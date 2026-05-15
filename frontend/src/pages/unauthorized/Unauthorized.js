import React from 'react';
import { Box, Button, Card, CardContent, Stack, Typography } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import { useLanguage } from '../../context/LanguageContext';

function Unauthorized() {
  const { t } = useLanguage();
  return (
    <Box sx={{ minHeight: '70vh', display: 'flex', alignItems: 'center', justifyContent: 'center', px: 2 }}>
      <Card sx={{ maxWidth: 560, width: '100%', overflow: 'hidden' }} elevation={0}>
        <CardContent sx={{ p: { xs: 3, md: 4 }, background: 'linear-gradient(160deg, rgba(22,90,114,0.08), rgba(255,255,255,1))' }}>
          <Stack spacing={2.25}>
            <Typography variant="overline" color="primary.main" fontWeight={800}>
              RBAC
            </Typography>
            <Typography variant="h4" fontWeight={900}>
              {t('unauthorizedTitle')}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {t('unauthorizedMessage')}
            </Typography>
            <Button component={RouterLink} to="/dashboard" variant="contained" sx={{ alignSelf: 'flex-start' }}>
              {t('unauthorizedBack')}
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}

export default Unauthorized;