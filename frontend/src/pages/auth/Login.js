import React, { useState, useContext } from 'react';
import {
  Alert,
  Box,
  Button,
  Divider,
  Grid,
  InputAdornment,
  TextField,
  Typography,
} from '@mui/material';
import EmailOutlinedIcon from '@mui/icons-material/EmailOutlined';
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import ArrowForwardIosIcon from '@mui/icons-material/ArrowForwardIos';
import { useNavigate, Navigate } from 'react-router-dom';
import { AuthContext } from '../../context/AuthContext';

function Connexion() {
  const [email, setEmail] = useState('admin@hopital.com');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login: connexion, user: utilisateur } = useContext(AuthContext);
  const navigate = useNavigate();

  if (utilisateur) {
    return <Navigate to="/dashboard" replace />;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await connexion(email.trim(), password);
      navigate('/dashboard');
    } catch (err) {
      setError('Identifiants incorrects. Veuillez réessayer.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ minHeight: '100vh', background: '#ffffff' }}>
      <Grid container sx={{ minHeight: '100vh', background: '#ffffff' }}>
        <Grid
          item
          xs={12}
          md={6}
          sx={{
            position: 'relative',
            overflow: 'hidden',
            background: 'linear-gradient(180deg, #0e4f79 0%, #0d3d65 58%, #0a2d51 100%)',
            clipPath: { xs: 'none', md: 'polygon(0 0, 100% 0, 82% 100%, 0 100%)' },
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            px: { xs: 4, md: 8 },
            py: { xs: 8, md: 10 },
            zIndex: 1,
          }}
        >
          <Box sx={{ position: 'absolute', inset: 0, background: 'radial-gradient(circle at 20% 20%, rgba(255,255,255,0.08), transparent 18%), radial-gradient(circle at 82% 10%, rgba(255,255,255,0.06), transparent 15%)', pointerEvents: 'none' }} />
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              backgroundImage: 'url(/login-kidney.png)',
              backgroundRepeat: 'no-repeat',
              backgroundSize: '70% auto',
              backgroundPosition: 'center 30%',
              opacity: 0.95,
              pointerEvents: 'none',
            }}
          />
          <Box sx={{ position: 'relative', zIndex: 1, maxWidth: 520, color: '#fff' }}>
            <Typography variant="h2" sx={{ fontWeight: 900, mb: 3, fontSize: { xs: '2.8rem', md: '4rem' }, lineHeight: 0.95, color: '#f5bbff' }}>
              AI NéphroCare
            </Typography>
            <Typography variant="body1" sx={{ color: 'rgba(255,255,255,0.88)', maxWidth: 480, mb: 4, lineHeight: 1.85 }}>
              Une plateforme intelligente dédiée à la néphrologie, pensée pour vos patients et vos équipes.
            </Typography>
          </Box>
        </Grid>

        <Grid
          item
          xs={12}
          md={6}
          sx={{
            position: 'relative',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            px: { xs: 4, md: 8 },
            py: { xs: 8, md: 10 },
            background: '#ffffff',
            overflow: 'hidden',
            width: { md: 'calc(100% + 80px)' },
            ml: { md: '-80px' },
            '&:before': {
              content: '""',
              position: 'absolute',
              top: 0,
              left: 0,
              width: 120,
              height: '100%',
              background: '#ffffff',
              transform: 'skewX(-12deg)',
              transformOrigin: 'top left',
              zIndex: 0,
            },
          }}
        >
          <Box
            sx={{
              position: 'relative',
              zIndex: 1,
              width: '100%',
              maxWidth: 520,
              background: '#ffffff',
              borderRadius: 4,
              boxShadow: '0 34px 80px rgba(15, 23, 42, 0.12)',
              border: '1px solid rgba(15, 23, 42, 0.06)',
              p: { xs: 4, md: 6 },
              overflow: 'hidden',
            }}
          >
            <Box sx={{ position: 'absolute', inset: 0, background: 'radial-gradient(circle at top left, rgba(124, 58, 237, 0.12), transparent 24%), radial-gradient(circle at bottom right, rgba(59, 130, 246, 0.08), transparent 20%)', pointerEvents: 'none' }} />
            <Box sx={{ position: 'relative', zIndex: 1 }}>
              <Typography
                variant="h5"
                sx={{
                  fontWeight: 700,
                  mb: 1,
                  color: '#0f2641',
                  textAlign: 'center', // Center align the text
                }}
              >
                Connexion
              </Typography>
              <Typography variant="body2" sx={{ color: '#64748b', mb: 5 }}>
                Connectez-vous pour continuer vers l’espace patient sécurisé.
              </Typography>

              {error && <Alert severity="error" sx={{ mb: 3, borderRadius: 3 }}>{error}</Alert>}

              <Box component="form" onSubmit={handleSubmit} noValidate sx={{ display: 'grid', gap: 2.5 }}>
                <TextField
                  required
                  fullWidth
                  label="Email"
                  placeholder="admin@hopital.com"
                  name="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <EmailOutlinedIcon sx={{ color: '#64748b' }} />
                      </InputAdornment>
                    ),
                  }}
                  sx={{ '& .MuiOutlinedInput-root': { borderRadius: '24px', background: '#f7f9ff' } }}
                />
                <TextField
                  required
                  fullWidth
                  label="Mot de passe"
                  placeholder="••••••••••••••"
                  type="password"
                  name="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <LockOutlinedIcon sx={{ color: '#64748b' }} />
                      </InputAdornment>
                    ),
                  }}
                  sx={{ '& .MuiOutlinedInput-root': { borderRadius: '24px', background: '#f7f9ff' } }}
                />

                <Box
                  component="button"
                  onClick={handleSubmit}
                  sx={{
                    background: 'none',
                    color: '#003366', // Dark blue color
                    fontWeight: 'bold',
                    fontSize: '1rem',
                    border: 'none',
                    cursor: 'pointer',
                    textTransform: 'none',
                    textDecoration: 'underline',
                    display: 'flex',
                    justifyContent: 'flex-end', // Align text to the right
                    alignItems: 'center',
                    gap: '4px',
                    '&:hover': {
                      textDecoration: 'none',
                      color: '#001a33', // Darker blue on hover
                    },
                  }}
                >
                  Connexion <ArrowForwardIosIcon sx={{ fontSize: '1rem' }} />
                </Box>
              </Box>

              <Box
                sx={{
                  position: 'absolute',
                  inset: 0,
                  zIndex: 0,
                  overflow: 'hidden',
                  pointerEvents: 'none',
                }}
              >
                <Box
                  sx={{
                    position: 'fixed', // Ensure it is fixed to the interface
                    top: 0,
                    right: 0,
                    width: '50%', // Adjust width to match the triangle area
                    height: '100%',
                    zIndex: -1, // Place it behind all content
                    overflow: 'hidden',
                    pointerEvents: 'none',
                    clipPath: 'polygon(50% 0, 100% 0, 100% 100%)', // Right triangle shape next to the blue area
                  }}
                >
                  {[...Array(100)].map((_, index) => (
                    <Box
                      key={index}
                      sx={{
                        position: 'absolute',
                        width: `${Math.random() * 10 + 5}px`,
                        height: `${Math.random() * 10 + 5}px`,
                        backgroundColor: 'rgba(59, 130, 246, 0.3)',
                        borderRadius: '50%',
                        animation: `float ${Math.random() * 5 + 5}s ease-in-out infinite`,
                        top: `${Math.random() * 100}%`,
                        left: `${Math.random() * 100}%`,
                      }}
                    />
                  ))}
                  <style>
                    {`
                      @keyframes float {
                        0% {
                          transform: translateY(0);
                        }
                        50% {
                          transform: translateY(-20px);
                        }
                        100% {
                          transform: translateY(0);
                        }
                      }
                    `}
                  </style>
                </Box>
              </Box>
            </Box>
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
}

export default Connexion;
