import React from 'react';
import { Box, Button, Card, CardContent, Stack, Typography } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';

function Unauthorized() {
  return (
    <Box sx={{ minHeight: '70vh', display: 'flex', alignItems: 'center', justifyContent: 'center', px: 2 }}>
      <Card sx={{ maxWidth: 560, width: '100%', overflow: 'hidden' }} elevation={0}>
        <CardContent sx={{ p: { xs: 3, md: 4 }, background: 'linear-gradient(160deg, rgba(22,90,114,0.08), rgba(255,255,255,1))' }}>
          <Stack spacing={2.25}>
            <Typography variant="overline" color="primary.main" fontWeight={800}>
              RBAC
            </Typography>
            <Typography variant="h4" fontWeight={900}>
              Accès non autorisé
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Votre rôle ne dispose pas des permissions nécessaires pour afficher cette page.
            </Typography>
            <Button component={RouterLink} to="/dashboard" variant="contained" sx={{ alignSelf: 'flex-start' }}>
              Retour au tableau de bord
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}

export default Unauthorized;