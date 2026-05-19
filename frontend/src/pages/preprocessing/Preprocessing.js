import React, { useEffect, useRef, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  CircularProgress,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  List,
  ListItem,
  Grid,
  Chip,
  Alert,
  Stack,
} from '@mui/material';
import api from '../../services/api/axios';

const formatCellValue = (value) => {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string') return value;
  return String(value);
};

function DataValidationScreen({
  summary,
  originalRows,
  correctedRows,
  onApproveOriginal,
  onApproveCorrected,
  loading,
}) {
  const qualityScore = Number.isFinite(summary?.quality_score) ? summary.quality_score : null;
  const gaugeValue = qualityScore === null ? 0 : Math.max(0, Math.min(100, qualityScore));
  const gaugeColor = gaugeValue < 50 ? '#c62828' : gaugeValue < 80 ? '#ef6c00' : '#2e7d32';
  const rowCount = Math.min(20, Math.max(originalRows.length, correctedRows.length));
  const columns = Array.from(
    new Set([
      ...Object.keys(originalRows[0] || {}),
      ...Object.keys(correctedRows[0] || {}),
    ])
  );

  return (
    <Box sx={{ mt: 3 }}>
      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems="center" justifyContent="space-between">
          <Stack direction="row" spacing={2} alignItems="center">
            <Box sx={{ position: 'relative', display: 'inline-flex' }}>
              <CircularProgress variant="determinate" value={gaugeValue} size={72} thickness={5} sx={{ color: gaugeColor }} />
              <Box sx={{
                top: 0,
                left: 0,
                bottom: 0,
                right: 0,
                position: 'absolute',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>{qualityScore ?? '-'}</Typography>
              </Box>
            </Box>
            <Box>
              <Typography variant="subtitle2" color="text.secondary">Score de qualite</Typography>
              <Typography variant="body2">
                {summary?.confidence_label ? `${summary.confidence_label} (${summary.confidence_pct ?? '-'}%)` : 'Evaluation LLM'}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {summary?.rows ?? '-'} lignes • {summary?.columns ?? '-'} colonnes
              </Typography>
            </Box>
          </Stack>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ width: { xs: '100%', sm: 'auto' } }}>
            <Button
              variant="outlined"
              color="warning"
              onClick={onApproveOriginal}
              disabled={loading || !originalRows.length}
            >
              Rejeter les corrections et importer les donnees originales
            </Button>
            <Button
              variant="contained"
              color="success"
              onClick={onApproveCorrected}
              disabled={loading || !correctedRows.length}
            >
              Valider et integrer la version corrigee
            </Button>
          </Stack>
        </Stack>
      </Paper>

      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="subtitle1">Donnees originales</Typography>
            <Table size="small" sx={{ mt: 1 }}>
              <TableHead>
                <TableRow>
                  <TableCell>#</TableCell>
                  {columns.map((key) => (
                    <TableCell key={`orig-head-${key}`}>{key}</TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {Array.from({ length: rowCount }).map((_, rowIndex) => {
                  const originalRow = originalRows[rowIndex] || {};
                  const correctedRow = correctedRows[rowIndex] || {};
                  return (
                    <TableRow key={`orig-${rowIndex}`}>
                      <TableCell>{rowIndex + 1}</TableCell>
                      {columns.map((key) => {
                        const originalValue = formatCellValue(originalRow[key]);
                        const correctedValue = formatCellValue(correctedRow[key]);
                        const changed = originalValue !== correctedValue;
                        return (
                          <TableCell
                            key={`orig-${rowIndex}-${key}`}
                            sx={{
                              bgcolor: changed ? '#f8d7da' : 'transparent',
                              textDecoration: changed ? 'line-through' : 'none',
                            }}
                          >
                            {originalValue}
                          </TableCell>
                        );
                      })}
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="subtitle1">Donnees corrigees</Typography>
            <Table size="small" sx={{ mt: 1 }}>
              <TableHead>
                <TableRow>
                  <TableCell>#</TableCell>
                  {columns.map((key) => (
                    <TableCell key={`corr-head-${key}`}>{key}</TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {Array.from({ length: rowCount }).map((_, rowIndex) => {
                  const originalRow = originalRows[rowIndex] || {};
                  const correctedRow = correctedRows[rowIndex] || {};
                  return (
                    <TableRow key={`corr-${rowIndex}`}>
                      <TableCell>{rowIndex + 1}</TableCell>
                      {columns.map((key) => {
                        const originalValue = formatCellValue(originalRow[key]);
                        const correctedValue = formatCellValue(correctedRow[key]);
                        const changed = originalValue !== correctedValue;
                        return (
                          <TableCell
                            key={`corr-${rowIndex}-${key}`}
                            sx={{ bgcolor: changed ? '#d4edda' : 'transparent' }}
                          >
                            {correctedValue}
                          </TableCell>
                        );
                      })}
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}

export default function Preprocessing() {
  const [file, setFile] = useState(null);
  const [fileError, setFileError] = useState('');
  const [loading, setLoading] = useState(false);
  const [session, setSession] = useState(null);
  const [report, setReport] = useState(null);
  const [status, setStatus] = useState(null);
  const [statusMessage, setStatusMessage] = useState('');
  const [showRawJson, setShowRawJson] = useState(false);  // NOUVEAU
  const pollIntervalRef = useRef(null);
  const [llmStatus, setLlmStatus] = useState({
    checking: true,
    connected: false,
    message: 'Vérification de la connexion LLM...',
    base_url: null,
    configured_model: null,
    errors: [],
  });
  const [datasetProfile, setDatasetProfile] = useState(null);
  const [originalPreviewRows, setOriginalPreviewRows] = useState([]);
  const [correctedPreviewRows, setCorrectedPreviewRows] = useState([]);
  const [pipelineInfo, setPipelineInfo] = useState(null);
  const [routeInfo, setRouteInfo] = useState(null);

  const parseMaybeJson = (value) => {
    if (typeof value !== 'string') return null;
    const text = value.trim();
    if (!text.startsWith('{') && !text.startsWith('[')) return null;
    try {
      return JSON.parse(text);
    } catch (_error) {
      return null;
    }
  };

  const rawLlmAnalysis = report?.llm_analysis;
  const parsedLlmAnalysis = parseMaybeJson(rawLlmAnalysis);
  const llmAnalysisObject = typeof rawLlmAnalysis === 'object' && rawLlmAnalysis !== null ? rawLlmAnalysis : parsedLlmAnalysis || null;
  const llmSummaryText = (() => {
    if (llmAnalysisObject?.summary && typeof llmAnalysisObject.summary === 'string') {
      return llmAnalysisObject.summary;
    }
    if (typeof rawLlmAnalysis === 'string' && rawLlmAnalysis.trim()) {
      return rawLlmAnalysis.trim();
    }
    return 'Aucun résumé lisible renvoyé par le moteur d’analyse.';
  })();
  const routeReason = routeInfo?.reason || report?.route?.reason || '';
  const routeMode = routeInfo?.mode || report?.route?.mode || '';
  const routeLabel = routeInfo?.label || report?.route?.label || '';
  const routeFallbackUsed = Boolean(routeInfo?.fallback_used || report?.audit_log?.[0]?.fallback_used);

  const isAllowedFileType = (selectedFile) => {
    if (!selectedFile) return false;
    const fileName = String(selectedFile.name || '').toLowerCase();
    return fileName.endsWith('.csv') || fileName.endsWith('.xlsx');
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files && e.target.files[0];
    setReport(null);
    setSession(null);
    setStatus(null);
    setStatusMessage('');
    setShowRawJson(false);  // Réinitialiser
    setDatasetProfile(null);
    setOriginalPreviewRows([]);
    setCorrectedPreviewRows([]);
    setPipelineInfo(null);
    setRouteInfo(null);

    if (!selectedFile) {
      setFile(null);
      setFileError('');
      return;
    }

    if (!isAllowedFileType(selectedFile)) {
      setFile(null);
      setFileError('Format invalide. Choisissez un fichier .csv ou .xlsx.');
      return;
    }

    setFile(selectedFile);
    setFileError('');
  };

  // Poll for job status when session ID is set and status is pending
  useEffect(() => {
  if (!session || status !== 'pending') {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    return;
  }

  const interval = setInterval(async () => {
    try {
      const response = await fetch(`/patients/preprocess/${session}/status/`);
      const data = await response.json();
      const jobStatus = data.status || 'pending';
      setStatusMessage(data.progress_message || data.message || 'Traitement en cours...');

      if (jobStatus === 'completed') {
        setStatus('completed');
        setReport(data.report || null);
        setDatasetProfile(data.dataset_profile || data.report?.dataset_profile || null);
        setOriginalPreviewRows(data.original_preview_rows || []);
        setCorrectedPreviewRows(data.corrected_preview_rows || data.preview_rows || []);
        setPipelineInfo(data.report?.pipeline || null);
        setRouteInfo(data.report?.route || data.report?.llm_analysis?.route || null);
        clearInterval(interval);
        pollIntervalRef.current = null;
        setLoading(false);
      } else if (jobStatus === 'error') {
        setStatus('error');
        setStatusMessage(data.error || 'Erreur inconnue');
        clearInterval(interval);
        pollIntervalRef.current = null;
        setLoading(false);
      }
    } catch (err) {
      console.error('Erreur lors du polling:', err);
      setStatusMessage('Erreur lors de la vérification du statut');
    }
  }, 2000);

  pollIntervalRef.current = interval;
  return () => {
    clearInterval(interval);
    if (pollIntervalRef.current === interval) {
      pollIntervalRef.current = null;
    }
  };
}, [session, status]);

  const handleAnalyze = async () => {
  if (!file) return;
  setLoading(true);
  setStatus('pending');
  setStatusMessage('Initialisation du traitement...');
  try {
    const form = new FormData();
    form.append('file', file);
    
    // Utiliser fetch au lieu de api.post (évite l'envoi du token)
    const response = await fetch('/patients/preprocess/analyze/', {
      method: 'POST',
      body: form,
    });
    
    const data = await response.json();
    
    const sessionId = data.preprocess_id || data.id || null;
    if (sessionId) {
      setSession(sessionId);
      setStatus('pending');
      setStatusMessage(data.message || 'Analyse en cours...');
      setPipelineInfo(null);
      setRouteInfo(null);
    } else {
      setStatus('error');
      setStatusMessage('ID de session non reçu');
      setLoading(false);
    }
  } catch (err) {
    console.error(err);
    setStatus('error');
    setStatusMessage(err.message || 'Erreur lors de l\'analyse');
    setLoading(false);
  }
};

  const checkLlmStatus = async () => {
  setLlmStatus((prev) => ({ ...prev, checking: true }));
  try {
    const response = await fetch('/patients/preprocess/health/');
    const data = await response.json();
    
    setLlmStatus({
      checking: false,
      connected: true,
      message: 'LLM connecté (Ollama - Qwen 2.5 7B)',
      base_url: 'http://localhost:11434',
      configured_model: data.model || 'qwen2.5:7b',
      errors: [],
    });
  } catch (err) {
    setLlmStatus({
      checking: false,
      connected: false,
      message: 'Backend indisponible: ' + err.message,
      base_url: null,
      configured_model: null,
      errors: [err.message],
    });
  }
};

  const llmChipColor = llmStatus.checking
    ? 'warning'
    : llmStatus.connected
      ? 'success'
      : 'error';
  const llmChipLabel = llmStatus.checking
    ? 'LLM: vérification...'
    : llmStatus.connected
      ? 'LLM: connecté'
      : 'LLM: indisponible';

  const pipelineStages = [
    { key: 'upload', label: 'Upload & lecture' },
    { key: 'profile', label: 'Profilage Pandas' },
    { key: 'chunking', label: 'Chunking intelligent' },
    { key: 'retrieval', label: 'Retrieval contextuel' },
    { key: 'llm1', label: 'LLM diagnostic' },
    { key: 'llm2', label: 'Plan de correction' },
    { key: 'merge', label: 'Fusion & rapport' },
  ];

  const currentStageLabel = (() => {
    const text = String(statusMessage || '').toLowerCase();
    if (text.includes('lecture')) return 'upload';
    if (text.includes('profilage')) return 'profile';
    if (text.includes('chunk')) return 'chunking';
    if (text.includes('retrieval') || text.includes('contexte')) return 'retrieval';
    if (text.includes('passe 1')) return 'llm1';
    if (text.includes('passe 2')) return 'llm2';
    if (text.includes('fusion') || text.includes('rapport') || text.includes('correction')) return 'merge';
    return null;
  })();

  const handleExport = async () => {
  if (!session) return;
  try {
    const response = await fetch(`/patients/preprocess/${session}/export/`);
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.setAttribute('download', `preprocess_${session}.xlsx`);
    document.body.appendChild(a);
    a.click();
    a.remove();
  } catch (err) {
    console.error(err);
    alert('Erreur export');
  }
};

const handleIntegrateChoice = async (source) => {
  if (!session) return;
  const label = source === 'original' ? 'les données originales' : 'la version corrigée';
  if (!window.confirm(`Intégrer ${label} dans la plateforme ?`)) return;
  setLoading(true);
  try {
    await fetch(`/patients/preprocess/${session}/integrate/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source }),
    });
    alert('Import intégré. Rafraîchissez la page patients si nécessaire.');
  } catch (err) {
    console.error(err);
    alert('Erreur integration');
  } finally {
    setLoading(false);
  }
};
  return (
    <Box sx={{ p: 2 }}>
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6">Prétraitement</Typography>
        <Stack direction="row" spacing={1} sx={{ mt: 1, alignItems: 'center', flexWrap: 'wrap' }}>
          <Chip color={llmChipColor} label={llmChipLabel} />
          <Button variant="text" size="small" onClick={checkLlmStatus} disabled={loading || llmStatus.checking}>
            Actualiser l'état LLM
          </Button>
        </Stack>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          {llmStatus.message}
          {llmStatus.base_url ? ` URL: ${llmStatus.base_url}` : ''}
          {llmStatus.configured_model ? ` • Modèle: ${llmStatus.configured_model}` : ''}
        </Typography>
        {!llmStatus.checking && !llmStatus.connected && llmStatus.errors.length > 0 && (
          <Alert severity="warning" sx={{ mt: 1 }}>
            {llmStatus.errors[0]}
          </Alert>
        )}
        <Box sx={{ mt: 2, display: 'flex', gap: 2, alignItems: 'center' }}>
          <input type="file" accept=".csv,.xlsx" onChange={handleFileChange} />
          <Button variant="contained" onClick={handleAnalyze} disabled={!file || loading}>Analyser</Button>
          <Button variant="outlined" onClick={handleExport} disabled={!session || loading}>Exporter corrigé</Button>
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Formats acceptés: CSV ou XLSX, avec XLSX recommandé dans la plupart des cas.
        </Typography>

        {fileError && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {fileError}
          </Alert>
        )}

        {loading && status === 'pending' && (
          <Box sx={{ mt: 2 }}>
            <Alert severity="info" sx={{ mb: 2 }}>
              <Stack spacing={1}>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  Analyse en cours...
                </Typography>
                <Typography variant="body2">{statusMessage}</Typography>
                <LinearProgress />
              </Stack>
            </Alert>
          </Box>
        )}

        {(loading || report?.pipeline || currentStageLabel) && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle1">Pipeline d’analyse</Typography>
            <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: 'wrap' }}>
              {pipelineStages.map((stage) => {
                const isDone = ['profile', 'chunking', 'retrieval', 'llm1', 'llm2', 'merge'].indexOf(stage.key) <
                  ['profile', 'chunking', 'retrieval', 'llm1', 'llm2', 'merge'].indexOf(currentStageLabel);
                const isActive = currentStageLabel === stage.key;
                return (
                  <Chip
                    key={stage.key}
                    label={stage.label}
                    color={isActive ? 'primary' : isDone ? 'success' : 'default'}
                    variant={isActive || isDone ? 'filled' : 'outlined'}
                    size="small"
                  />
                );
              })}
            </Stack>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              {pipelineInfo?.stage ? `Étape finale: ${pipelineInfo.stage}` : statusMessage}
            </Typography>
            {pipelineInfo?.chunks_count ? (
              <Typography variant="body2" color="text.secondary">
                Chunks analysés: {pipelineInfo.chunks_count}
                {pipelineInfo?.retrieved_chunks_count ? ` • Chunks récupérés: ${pipelineInfo.retrieved_chunks_count}` : ''}
              </Typography>
            ) : null}
            {routeInfo?.mode ? (
              <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: 'wrap' }}>
                <Chip size="small" label={`Route: ${routeInfo.mode}`} color="secondary" variant="outlined" />
                {routeInfo.label ? <Chip size="small" label={routeInfo.label} variant="outlined" /> : null}
                {routeInfo.primary_model ? <Chip size="small" label={`Modèle: ${routeInfo.primary_model}`} variant="outlined" /> : null}
              </Stack>
            ) : null}
          </Box>
        )}

        {status === 'error' && (
          <Alert severity="error" sx={{ mt: 2 }}>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              Erreur d'analyse
            </Typography>
            <Typography variant="body2">{statusMessage}</Typography>
          </Alert>
        )}

        {loading && status !== 'pending' && <LinearProgress sx={{ mt: 2 }} />}

        {report?.summary && (
          <Grid container spacing={2} sx={{ mt: 2 }}>
            <Grid item xs={12}>
              <Alert severity="success">
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  ✓ Analyse terminée avec succès
                </Typography>
              </Alert>
            </Grid>
            <Grid item xs={12} md={3}>
              <Paper variant="outlined" sx={{ p: 2, height: '100%' }}>
                <Typography variant="overline" color="text.secondary">Score qualité</Typography>
                <Typography variant="h4">{report.summary.quality_score ?? '-'}</Typography>
                <Typography variant="body2" color="text.secondary">Évaluation LLM du dataset importé</Typography>
              </Paper>
            </Grid>
            <Grid item xs={12} md={3}>
              <Paper variant="outlined" sx={{ p: 2, height: '100%' }}>
                <Typography variant="overline" color="text.secondary">Lignes</Typography>
                <Typography variant="h4">{report.summary.rows ?? '-'}</Typography>
                <Typography variant="body2" color="text.secondary">{report.summary.corrected_rows ?? report.summary.rows ?? '-'} après corrections proposées</Typography>
              </Paper>
            </Grid>
            <Grid item xs={12} md={3}>
              <Paper variant="outlined" sx={{ p: 2, height: '100%' }}>
                <Typography variant="overline" color="text.secondary">Colonnes</Typography>
                <Typography variant="h4">{report.summary.columns ?? '-'}</Typography>
                <Typography variant="body2" color="text.secondary">Structure détectée par Pandas</Typography>
              </Paper>
            </Grid>
            <Grid item xs={12} md={3}>
              <Paper variant="outlined" sx={{ p: 2, height: '100%' }}>
                <Typography variant="overline" color="text.secondary">Corrections</Typography>
                <Typography variant="h4">{report.summary.applied_corrections_count ?? 0}</Typography>
                <Typography variant="body2" color="text.secondary">Règles exécutées sur la proposition corrigée</Typography>
              </Paper>
            </Grid>
          </Grid>
        )}

        {report?.summary && (
          <Box sx={{ mt: 3 }}>
            <Typography variant="subtitle1">Résumé du rapport</Typography>
            <Typography variant="body2" sx={{ mt: 0.5 }}>{llmSummaryText}</Typography>

            {(routeMode || routeLabel || routeReason) && (
              <Paper variant="outlined" sx={{ p: 2, mt: 2, bgcolor: '#fafbff' }}>
                <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
                  {routeMode ? <Chip size="small" label={`Route: ${routeMode}`} color={routeMode === 'rag_llm' ? 'success' : 'warning'} /> : null}
                  {routeLabel ? <Chip size="small" label={routeLabel} variant="outlined" /> : null}
                  {routeFallbackUsed ? <Chip size="small" label="Fallback utilisé" color="warning" variant="outlined" /> : null}
                  {pipelineInfo?.version ? <Chip size="small" label={`Pipeline: ${pipelineInfo.version}`} variant="outlined" /> : null}
                </Stack>
                {routeReason ? (
                  <Typography variant="body2" sx={{ mt: 1 }} color="text.secondary">
                    {routeReason}
                  </Typography>
                ) : null}
              </Paper>
            )}

            {llmAnalysisObject?.limitations?.length ? (
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>Limites détectées</Typography>
                <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
                  {llmAnalysisObject.limitations.map((item, index) => (
                    <Chip key={`${item}-${index}`} label={item} size="small" variant="outlined" />
                  ))}
                </Stack>
              </Box>
            ) : null}
            
            {/* Bouton pour afficher le JSON complet */}
            {rawLlmAnalysis && (
              <Button 
                size="small" 
                variant="outlined" 
                onClick={() => setShowRawJson(!showRawJson)}
                sx={{ mt: 1, mb: 1 }}
              >
                {showRawJson ? '📄 Masquer la réponse JSON' : '📋 Afficher la réponse JSON complète'}
              </Button>
            )}
            
            {/* Affichage du JSON complet */}
            {showRawJson && rawLlmAnalysis && (
              <Paper 
                variant="outlined" 
                sx={{ 
                  p: 2, 
                  maxHeight: 500, 
                  overflow: 'auto',
                  bgcolor: '#1e1e1e',
                  color: '#d4d4d4',
                  fontFamily: 'Consolas, monospace',
                  fontSize: '0.75rem',
                  mt: 1
                }}
              >
                <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                  {typeof rawLlmAnalysis === 'string'
                    ? rawLlmAnalysis
                    : JSON.stringify(rawLlmAnalysis, null, 2)}
                </pre>
              </Paper>
            )}
          </Box>
        )}

        {(originalPreviewRows.length > 0 || correctedPreviewRows.length > 0) && (
          <DataValidationScreen
            summary={report?.summary}
            originalRows={originalPreviewRows}
            correctedRows={correctedPreviewRows}
            onApproveOriginal={() => handleIntegrateChoice('original')}
            onApproveCorrected={() => handleIntegrateChoice('corrected')}
            loading={loading}
          />
        )}

        {Array.isArray(report?.issues) && report.issues.length > 0 && (
          <Box sx={{ mt: 3 }}>
            <Typography variant="subtitle1">Problèmes détectés</Typography>
            <List dense>
              {report.issues.map((issue, index) => (
                <ListItem key={index} sx={{ display: 'block' }}>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {`${issue.severity || 'info'} • ${issue.category || 'general'}${issue.column ? ` • ${issue.column}` : ''}`}
                  </Typography>
                  <Typography variant="body2">{issue.explanation || issue.message || ''}</Typography>
                  {Array.isArray(issue.rows) && issue.rows.length > 0 && (
                    <Typography variant="caption" color="text.secondary">Lignes: {issue.rows.join(', ')}</Typography>
                  )}
                </ListItem>
              ))}
            </List>
          </Box>
        )}

        {Array.isArray(report?.recommendations) && report.recommendations.length > 0 && (
          <Box sx={{ mt: 3 }}>
            <Typography variant="subtitle1">Recommandations</Typography>
            <List dense>
              {report.recommendations.map((item, index) => (
                <ListItem key={index}>{item}</ListItem>
              ))}
            </List>
          </Box>
        )}

        {datasetProfile?.columns_profile && datasetProfile.columns_profile.length > 0 && (
          <Box sx={{ mt: 3 }}>
            <Typography variant="subtitle1">Profil de structure extrait par Pandas</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              {datasetProfile.rows ?? '-'} lignes • {datasetProfile.columns ?? '-'} colonnes
            </Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Colonne</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Manquants</TableCell>
                  <TableCell>Exemples</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {datasetProfile.columns_profile.map((column) => (
                  <TableRow key={column.column}>
                    <TableCell>{column.column}</TableCell>
                    <TableCell>{column.dtype}</TableCell>
                    <TableCell>{column.missing_pct}%</TableCell>
                    <TableCell>{Array.isArray(column.sample_values) ? column.sample_values.join(' | ') : ''}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        )}

      </Paper>
    </Box>
  );
}