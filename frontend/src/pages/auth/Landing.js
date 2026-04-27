import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Box, Button, Grid, Stack, Typography } from '@mui/material';
import ArrowForwardIosIcon from '@mui/icons-material/ArrowForwardIos';

function Landing() {
  const navigate = useNavigate();

  return (
    <Box
      sx={{
        minHeight: '100vh',
        width: '100%',
        background: 'linear-gradient(180deg, #0e4f79 0%, #1e7ea7 38%, #f3fbff 100%)',
        overflow: 'hidden',
      }}
    >
      <Box
        sx={{
          position: 'absolute',
          top: 24,
          right: 24,
          width: 220,
          height: 220,
          borderRadius: '40%',
          background: 'rgba(255,255,255,0.16)',
          filter: 'blur(24px)',
        }}
      />
      <Box
        sx={{
          position: 'absolute',
          bottom: 24,
          left: 24,
          width: 260,
          height: 260,
          borderRadius: '50%',
          background: 'rgba(255,255,255,0.12)',
          filter: 'blur(28px)',
        }}
      />

      <Grid container sx={{ minHeight: '100vh', px: { xs: 3, md: 8 }, py: { xs: 4, md: 6 } }} alignItems="center">
        <Grid item xs={12} md={6} sx={{ color: '#ffffff', zIndex: 1 }}>
          <Typography variant="overline" sx={{
            background: 'linear-gradient(90deg, #d8b4f8, #ff69b4)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            letterSpacing: 2,
            fontWeight: 700,
            mb: 3,
            display: 'inline-block',
          }}>
            AI NéphroCare
          </Typography>
          <Typography variant="h1" sx={{ fontWeight: 900, lineHeight: 1.02, mb: 3, maxWidth: 600, fontSize: { xs: '3rem', md: '4.2rem' } }}>
            Bienvenue dans votre espace santé
          </Typography>
          <Typography variant="h6" sx={{ color: '#e7f2fb', maxWidth: 580, mb: 4, lineHeight: 1.8 }}>
            Ouvrez votre compte sécurisé pour accéder à vos dossiers patients, vos analyses et vos outils de suivi médical.
          </Typography>

          <Button
            onClick={() => navigate('/login')}
            variant="contained"
            sx={{
              minWidth: 240,
              mt: 4,
              ml: { xs: 0, md: 2 },
              py: 1.95,
              px: 5,
              borderRadius: 3,
              background: 'linear-gradient(135deg, #1970a7 0%, #0b4f74 100%)',
              boxShadow: '0 20px 44px rgba(13, 45, 75, 0.18)',
              textTransform: 'none',
            }}
            endIcon={<ArrowForwardIosIcon />}
          >
            Commencer
          </Button>
        </Grid>

        <Grid item xs={12} md={6} sx={{ position: 'relative', zIndex: 1, mt: { xs: 6, md: 0 }, minHeight: { xs: 420, md: 620 }, overflow: 'visible' }}>
            <Box
              component="img"
              src="/kidney-landing.png"
              alt="Illustration néphrologique"
              sx={{
                position: 'absolute',
                top: '-10%',
                left: '-8%',
                width: '124%',
                height: '124%',
                objectFit: 'contain',
                objectPosition: 'top left',
                filter: 'contrast(1.1) saturate(1.1) brightness(0.94)',
                transform: 'translateY(0px) rotate(0deg)',
                animation: 'floatRotate 9s ease-in-out infinite',
                '@keyframes floatRotate': {
                  '0%, 100%': { transform: 'translateY(0px) rotate(0deg)' },
                  '25%': { transform: 'translateY(-10px) rotate(-1deg)' },
                  '50%': { transform: 'translateY(-20px) rotate(0.5deg)' },
                  '75%': { transform: 'translateY(-10px) rotate(-0.5deg)' },
                },
              }}
            />
        </Grid>
      </Grid>
    </Box>
  );
}

export default Landing;
