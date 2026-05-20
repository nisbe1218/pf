import React, { useEffect, useRef, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
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

export default function Preprocessing() {
  const [file, setFile] = useState(null);
  const [fileError, setFileError] = useState('');
  const [loading, setLoading] = useState(false);
  const [session, setSession] = useState(null);
  const [report, setReport] = useState(null);
  const [status, setStatus] = useState(null);  // 'pending', 'completed', 'error'
  const [statusMessage, setStatusMessage] = useState('');
  const pollIntervalRef = useRef(null);
  const [ollamaStatus, setOllamaStatus] = useState({
    checking: true,
    connected: false,
    message: 'Vérification de la connexion Ollama...',
    base_url: null,
    configured_model: null,
    errors: [],
  });
  const [datasetProfile, setDatasetProfile] = useState(null);
  const [originalPreviewRows, setOriginalPreviewRows] = useState([]);
  const [correctedPreviewRows, setCorrectedPreviewRows] = useState([]);
  const [pipelineInfo, setPipelineInfo] = useState(null);
  const [routeInfo, setRouteInfo] = useState(null);

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
        const resp = await api.get(`patients/preprocess/${session}/status/`);
        const data = resp.data || {};
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
    }, 2000);  // Poll every 2 seconds

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
      const resp = await api.post('patients/preprocess/analyze/', form);
      const data = resp.data || {};
      
      // Backend returns 202 ACCEPTED with preprocess_id
      const sessionId = data.preprocess_id || data.id || null;
      if (sessionId) {
        setSession(sessionId);
        setStatus('pending');
        setStatusMessage(data.message || 'Analyse en cours...');
        setPipelineInfo(null);
        setRouteInfo(null);
        // Polling will start automatically via useEffect
      } else {
        setStatus('error');
        setStatusMessage('ID de session non reçu');
        setLoading(false);
      }
    } catch (err) {
      console.error(err);
      setStatus('error');
      setStatusMessage(err?.response?.data?.error || 'Erreur lors de l\'analyse');
      setLoading(false);
    }
  };

  const checkOllamaStatus = async () => {
    setOllamaStatus((prev) => ({ ...prev, checking: true }));
    try {
      const resp = await api.get('patients/preprocess/health/');
      const data = resp.data || {};
      setOllamaStatus({
        checking: false,
        connected: Boolean(data.connected),
        message: data.message || 'Ollama connecté.',
        base_url: data.base_url || null,
        configured_model: data.configured_model || null,
        errors: Array.isArray(data.errors) ? data.errors : [],
      });
    } catch (err) {
      const data = err?.response?.data || {};
      setOllamaStatus({
        checking: false,
        connected: false,
        message: data.message || 'Ollama indisponible.',
        base_url: data.base_url || null,
        configured_model: data.configured_model || null,
        errors: Array.isArray(data.errors) ? data.errors : [],
      });
    }
  };

  useEffect(() => {
    checkOllamaStatus();
  }, []);

  const ollamaChipColor = ollamaStatus.checking
    ? 'warning'
    : ollamaStatus.connected
      ? 'success'
      : 'error';
  const ollamaChipLabel = ollamaStatus.checking
    ? 'Ollama: vérification...'
    : ollamaStatus.connected
      ? 'Ollama: connecté'
      : 'Ollama: indisponible';

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
      const resp = await api.get(`patients/preprocess/${session}/export/`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([resp.data]));
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

  const handleIntegrate = async () => {
    if (!session) return;
    if (!window.confirm('Intégrer les lignes corrigées dans la plateforme ?')) return;
    setLoading(true);
    try {
      await api.post(`patients/preprocess/${session}/integrate/`, {});
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
        <Typography variant="h6">Prétraitement </Typography>
        <Stack direction="row" spacing={1} sx={{ mt: 1, alignItems: 'center', flexWrap: 'wrap' }}>
          <Chip color={ollamaChipColor} label={ollamaChipLabel} />
          <Button variant="text" size="small" onClick={checkOllamaStatus} disabled={loading || ollamaStatus.checking}>
            Actualiser l'état Ollama
          </Button>
        </Stack>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          {ollamaStatus.message}
          {ollamaStatus.base_url ? ` URL: ${ollamaStatus.base_url}` : ''}
          {ollamaStatus.configured_model ? ` • Modèle: ${ollamaStatus.configured_model}` : ''}
        </Typography>
        {!ollamaStatus.checking && !ollamaStatus.connected && ollamaStatus.errors.length > 0 && (
          <Alert severity="warning" sx={{ mt: 1 }}>
            {ollamaStatus.errors[0]}
          </Alert>
        )}
        <Box sx={{ mt: 2, display: 'flex', gap: 2, alignItems: 'center' }}>
          <input type="file" accept=".csv,.xlsx" onChange={handleFileChange} />
          <Button variant="contained" onClick={handleAnalyze} disabled={!file || loading}>Analyser</Button>
          <Button variant="outlined" onClick={handleExport} disabled={!session || loading}>Exporter corrigé</Button>
          <Button color="secondary" variant="contained" onClick={handleIntegrate} disabled={!session || loading}>Intégrer</Button>
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
            <Typography variant="body2" sx={{ mt: 0.5 }}>{report.llm_analysis?.summary || 'Aucun résumé renvoyé par le modèle.'}</Typography>
            <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: 'wrap' }}>
              {(report.llm_analysis?.limitations || []).map((item, index) => (
                <Chip key={`${item}-${index}`} label={item} size="small" variant="outlined" />
              ))}
            </Stack>
          </Box>
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

        {originalPreviewRows && originalPreviewRows.length > 0 && (
          <Box sx={{ mt: 3 }}>
            <Typography variant="subtitle1">Aperçu brut extrait</Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  {Object.keys(originalPreviewRows[0]).map((k) => (
                    <TableCell key={k}>{k}</TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {originalPreviewRows.map((row, idx) => (
                  <TableRow key={idx}>
                    {Object.keys(row).map((k) => (
                      <TableCell key={k}>{String(row[k] ?? '')}</TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        )}

        {correctedPreviewRows && correctedPreviewRows.length > 0 && (
          <Box sx={{ mt: 3 }}>
            <Typography variant="subtitle1">Version corrigée proposée</Typography>
            <Alert severity="info" sx={{ mt: 1, mb: 2 }}>
              Cette version correspond au plan de correction proposé par le modèle local avant validation finale.
            </Alert>
            <Table size="small">
              <TableHead>
                <TableRow>
                  {Object.keys(correctedPreviewRows[0]).map((k) => (
                    <TableCell key={k}>{k}</TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {correctedPreviewRows.map((row, idx) => (
                  <TableRow key={idx}>
                    {Object.keys(row).map((k) => (
                      <TableCell key={k}>{String(row[k] ?? '')}</TableCell>
                    ))}
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
