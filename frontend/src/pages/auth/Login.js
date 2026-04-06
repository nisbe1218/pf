import React, { useState, useContext } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Container,
  Divider,
  Grid,
  InputAdornment,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import HealthAndSafetyIcon from '@mui/icons-material/HealthAndSafety';
import ShieldOutlinedIcon from '@mui/icons-material/ShieldOutlined';
import QueryStatsOutlinedIcon from '@mui/icons-material/QueryStatsOutlined';
import LocalHospitalOutlinedIcon from '@mui/icons-material/LocalHospitalOutlined';
import { useNavigate, Navigate } from 'react-router-dom';
import { AuthContext } from '../../context/AuthContext';

function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, user } = useContext(AuthContext);
  const navigate = useNavigate();

  // Si déjà connecté, on redirige
  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await login(email, password);
      // Redirection après succès
      navigate('/dashboard');
    } catch (err) {
      setError('Identifiants incorrects. Veuillez réessayer.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        py: { xs: 3, md: 6 },
        background: 'radial-gradient(circle at top left, rgba(78, 197, 182, 0.18), transparent 28%), radial-gradient(circle at bottom right, rgba(22, 90, 114, 0.14), transparent 26%), linear-gradient(180deg, #f4f8fb 0%, #edf4f8 100%)',
      }}
    >
      <Container component="main" maxWidth="lg">
      <Box
        sx={{
          borderRadius: 5,
          overflow: 'hidden',
          background: 'rgba(255,255,255,0.72)',
          backdropFilter: 'blur(14px)',
          boxShadow: '0 30px 80px rgba(15, 23, 42, 0.12)',
          border: '1px solid rgba(148, 163, 184, 0.14)',
        }}
      >
        <Grid container>
          <Grid
            item
            xs={12}
            md={5}
            sx={{
              position: 'relative',
              color: 'white',
              background: 'linear-gradient(160deg, #0f3f51 0%, #165a72 48%, #2b8aa3 100%)',
              p: { xs: 3, md: 5 },
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <Box
              sx={{
                position: 'absolute',
                inset: 'auto -60px -80px auto',
                width: 240,
                height: 240,
                borderRadius: '50%',
                background: 'rgba(255,255,255,0.08)',
              }}
            />
            <Stack spacing={3} sx={{ position: 'relative', zIndex: 1 }}>
              <Box>
                <HealthAndSafetyIcon sx={{ fontSize: 58, mb: 1, color: '#e9fbff' }} />
                <Typography variant="h4" fontWeight={900} sx={{ color: 'white' }}>
                  Néphro-IA
                </Typography>
                <Typography variant="body1" sx={{ mt: 1, opacity: 0.9, maxWidth: 360 }}>
                  Plateforme clinique de suivi, d’analyse et de prédiction des risques rénaux.
                </Typography>
              </Box>

              <Stack spacing={1.5}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                  <ShieldOutlinedIcon />
                  <Typography variant="body2">Accès sécurisé par authentification</Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                  <QueryStatsOutlinedIcon />
                  <Typography variant="body2">Tableaux de bord orientés décision</Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                  <LocalHospitalOutlinedIcon />
                  <Typography variant="body2">Design professionnel, sobre et médical</Typography>
                </Box>
              </Stack>
            </Stack>
          </Grid>

          <Grid item xs={12} md={7} sx={{ p: { xs: 3, md: 6 } }}>
            <Card elevation={0} sx={{ background: 'transparent' }}>
              <CardContent sx={{ p: 0, '&:last-child': { pb: 0 } }}>
                <Box sx={{ maxWidth: 420, mx: 'auto' }}>
                  <Box sx={{ mb: 3 }}>
                    <Typography component="h1" variant="h4" fontWeight={900} color="text.primary">
                      Connexion
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      Accédez à votre espace selon votre rôle.
                    </Typography>
                  </Box>

                  {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

                  <Box component="form" onSubmit={handleSubmit} noValidate>
                    <Stack spacing={2}>
                      <TextField
                        required
                        fullWidth
                        id="email"
                        label="Adresse email"
                        name="email"
                        autoComplete="email"
                        autoFocus
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        InputProps={{
                          startAdornment: <InputAdornment position="start">@</InputAdornment>,
                        }}
                      />
                      <TextField
                        required
                        fullWidth
                        name="password"
                        label="Mot de passe"
                        type="password"
                        id="password"
                        autoComplete="current-password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                      />
                      <Button
                        type="submit"
                        fullWidth
                        variant="contained"
                        sx={{ py: 1.6, fontSize: '1rem' }}
                        disabled={loading}
                      >
                        {loading ? 'Connexion en cours...' : 'Se connecter'}
                      </Button>
                    </Stack>
                  </Box>

                  <Divider sx={{ my: 3 }} />

                  <Typography variant="caption" color="text.secondary">
                    Interface optimisée pour une lecture rapide et un usage clinique quotidien.
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Box>
      </Container>
    </Box>
  );
}

export default Login;