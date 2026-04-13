import React, { useEffect, useState } from 'react';
import {
  Avatar,
  Badge,
  Box,
  Button,
  Card,
  CardContent,
  Divider,
  IconButton,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Popover,
  Stack,
  SvgIcon,
  Tooltip,
  Typography,
} from '@mui/material';
import HomeIcon from '@mui/icons-material/Home';
import DataObjectOutlinedIcon from '@mui/icons-material/DataObjectOutlined';
import PsychologyAltOutlinedIcon from '@mui/icons-material/PsychologyAltOutlined';
import NotificationsActiveOutlinedIcon from '@mui/icons-material/NotificationsActiveOutlined';
import { useLocation, useNavigate } from 'react-router-dom';

function AppSidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const isDashboardActive = location.pathname.startsWith('/dashboard');
  const isPatientsActive = location.pathname.startsWith('/patients');
  const isModelAiActive = location.pathname.startsWith('/modele-ai');
  const [pendingPatientImportStatus, setPendingPatientImportStatus] = useState(null);
  const [notificationAnchorEl, setNotificationAnchorEl] = useState(null);

  const buttonStyles = {
    justifyContent: 'space-between',
    textTransform: 'none',
    fontWeight: 800,
    borderRadius: 18,
    minHeight: 54,
    py: 0.9,
    px: 2,
    borderColor: 'rgba(108, 178, 160, 0.28)',
    transition: 'transform 180ms ease, box-shadow 180ms ease, background-color 180ms ease',
    '&:hover': {
      transform: 'translateY(-1px)',
      boxShadow: '0 14px 26px rgba(44, 105, 117, 0.16)',
      background: 'rgba(226,237,244,0.94)',
    },
  };

  useEffect(() => {
    const updateStatus = () => {
      try {
        const saved = localStorage.getItem('patients_insert_validation_status');
        const status = saved ? JSON.parse(saved) : null;
        setPendingPatientImportStatus(status?.status === 'pending' ? status : null);
      } catch {
        setPendingPatientImportStatus(null);
      }
    };

    updateStatus();

    window.addEventListener('patientsInsertValidationUpdated', updateStatus);
    window.addEventListener('storage', updateStatus);
    return () => {
      window.removeEventListener('patientsInsertValidationUpdated', updateStatus);
      window.removeEventListener('storage', updateStatus);
    };
  }, []);

  const handleNotificationClick = (event) => {
    setNotificationAnchorEl(event.currentTarget);
  };

  const handleNotificationClose = () => {
    setNotificationAnchorEl(null);
  };

  const handleMarkNotificationsRead = () => {
    setNotificationAnchorEl(null);
  };

  return (
    <Card
      elevation={0}
      sx={{
        borderRadius: 5,
        border: 'none',
        background: 'transparent',
        boxShadow: 'none',
        overflow: 'visible',
        position: { md: 'sticky' },
        top: { md: 16 },
      }}
    >
      <Box
        sx={{
          borderRadius: '32px',
          overflow: 'hidden',
          boxShadow: '0 24px 60px rgba(44, 105, 117, 0.08)',
          background: 'linear-gradient(180deg, #2C6975 0%, #68B2A0 100%)',
        }}
      >
        <Box
          sx={{
            p: 3,
            background: 'linear-gradient(135deg, #2C6975 0%, #68B2A0 100%)',
            color: 'white',
            borderTopLeftRadius: '32px',
            borderTopRightRadius: '32px',
          }}
        >
          <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 2 }}>
            <SvgIcon
              viewBox="0 0 64 64"
              sx={{ width: 46, height: 46, borderRadius: 3, bgcolor: 'rgba(255,255,255,0.18)', p: 1.25 }}
            >
              <circle cx="32" cy="32" r="30" fill="rgba(255,255,255,0.08)" stroke="white" strokeOpacity="0.25" strokeWidth="2" />
              <path d="M17 20c-4 5-4 12-1 17 3 5 9 7 13 4 4-3 5-8 4-13-1-5-4-9-10-10-4-1-6 0-6 2z" fill="#4aa4d6" />
              <path d="M47 20c4 5 4 12 1 17-3 5-9 7-13 4-4-3-5-8-4-13 1-5 4-9 10-10 4-1 6 0 6 2z" fill="#f0755a" />
              <path d="M24 25c-2 2-3 6-2 9" stroke="rgba(255,255,255,0.85)" strokeWidth="2" strokeLinecap="round" fill="none" />
              <path d="M40 25c2 2 3 6 2 9" stroke="rgba(255,255,255,0.85)" strokeWidth="2" strokeLinecap="round" fill="none" />
              <path d="M31 28c1 2 1 4 0 6" stroke="rgba(255,255,255,0.75)" strokeWidth="2" strokeLinecap="round" fill="none" />
            </SvgIcon>
            <Box sx={{ flexGrow: 1 }}>
              <Typography variant="caption" sx={{ opacity: 0.8, letterSpacing: 1.2 }}>
                NEPHRO AI
              </Typography>
            </Box>
            <Tooltip title={pendingPatientImportStatus ? "Nouvelle notification d'insertion en attente" : "Notifications"}>
              <IconButton
                onClick={handleNotificationClick}
                sx={{ color: 'white', border: '1px solid rgba(255,255,255,0.3)' }}
              >
                <Badge badgeContent={pendingPatientImportStatus ? 1 : 0} color="error" invisible={!pendingPatientImportStatus}>
                  <NotificationsActiveOutlinedIcon sx={{ width: 24, height: 24 }} />
                </Badge>
              </IconButton>
            </Tooltip>
          </Stack>
        </Box>

        <CardContent
          sx={{
            p: 2.5,
            background: 'rgba(255,255,255,0.96)',
            borderBottomLeftRadius: '32px',
            borderBottomRightRadius: '32px',
          }}
        >
          <Stack spacing={1.25}>
            <Button
              fullWidth
              variant={isDashboardActive ? 'contained' : 'outlined'}
              startIcon={<HomeIcon />}
              onClick={() => navigate('/dashboard')}
              sx={{
                ...buttonStyles,
                color: isDashboardActive ? 'white' : '#2C6975',
                background: isDashboardActive ? 'linear-gradient(115deg, #2C6975 0%, #68B2A0 100%)' : 'rgba(255,255,255,0.94)',
                boxShadow: isDashboardActive ? '0 12px 28px rgba(44, 105, 117, 0.16)' : '0 6px 18px rgba(44, 105, 117, 0.08)',
                '&:hover': {
                  transform: 'translateY(-1px)',
                  boxShadow: '0 14px 26px rgba(44, 105, 117, 0.16)',
                  background: isDashboardActive ? 'linear-gradient(115deg, #265863 0%, #5fa997 100%)' : 'rgba(226,237,244,0.94)',
                },
              }}
            >
              Tableau de bord
            </Button>
            <Button
              fullWidth
              variant={isPatientsActive ? 'contained' : 'outlined'}
              startIcon={<DataObjectOutlinedIcon />}
              onClick={() => navigate('/patients')}
              sx={{
                ...buttonStyles,
                color: isPatientsActive ? 'white' : '#2C6975',
                background: isPatientsActive ? 'linear-gradient(115deg, #2C6975 0%, #68B2A0 100%)' : 'rgba(255,255,255,0.94)',
                boxShadow: isPatientsActive ? '0 12px 28px rgba(44, 105, 117, 0.16)' : '0 6px 18px rgba(44, 105, 117, 0.08)',
                '&:hover': {
                  transform: 'translateY(-1px)',
                  boxShadow: '0 14px 26px rgba(44, 105, 117, 0.16)',
                  background: isPatientsActive ? 'linear-gradient(115deg, #265863 0%, #5fa997 100%)' : 'rgba(226,237,244,0.94)',
                },
              }}
            >
              Data patient
            </Button>
            <Button
              fullWidth
              variant={isModelAiActive ? 'contained' : 'outlined'}
              startIcon={<PsychologyAltOutlinedIcon />}
              onClick={() => navigate('/modele-ai')}
              sx={{
                ...buttonStyles,
                color: isModelAiActive ? 'white' : '#2C6975',
                background: isModelAiActive ? 'linear-gradient(115deg, #2C6975 0%, #68B2A0 100%)' : 'rgba(255,255,255,0.94)',
                boxShadow: isModelAiActive ? '0 12px 28px rgba(44, 105, 117, 0.16)' : '0 6px 18px rgba(44, 105, 117, 0.08)',
                '&:hover': {
                  transform: 'translateY(-1px)',
                  boxShadow: '0 14px 26px rgba(44, 105, 117, 0.16)',
                  background: isModelAiActive ? 'linear-gradient(115deg, #265863 0%, #5fa997 100%)' : 'rgba(226,237,244,0.94)',
                },
              }}
            >
              Modele AI
            </Button>
          </Stack>
        </CardContent>
      </Box>
      <Popover
        open={Boolean(notificationAnchorEl)}
        anchorEl={notificationAnchorEl}
        onClose={handleNotificationClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
        PaperProps={{ sx: { width: 340, borderRadius: 3, boxShadow: '0 24px 60px rgba(0,0,0,0.14)' } }}
      >
        <Box sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2, borderBottom: '1px solid rgba(0,0,0,0.08)' }}>
          <Box>
            <Typography variant="h6" fontWeight={700}>
              Notification
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {pendingPatientImportStatus ? '1 nouvelle alerte' : 'Aucune notification'}
            </Typography>
          </Box>
          {pendingPatientImportStatus && (
            <Button size="small" onClick={handleMarkNotificationsRead}>
              Marquer comme lu
            </Button>
          )}
        </Box>
        <Box sx={{ p: 2 }}>
          {pendingPatientImportStatus ? (
            <Box sx={{ display: 'flex', gap: 2, p: 2, borderRadius: 3, bgcolor: 'background.paper', boxShadow: '0 12px 24px rgba(15, 23, 42, 0.06)' }}>
              <Avatar sx={{ bgcolor: '#2C6975', width: 48, height: 48 }}>
                <NotificationsActiveOutlinedIcon />
              </Avatar>
              <Box sx={{ flex: 1 }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                  <Typography variant="subtitle2" fontWeight={700}>
                    Importation patient en attente
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {pendingPatientImportStatus.timestamp ? new Date(pendingPatientImportStatus.timestamp).toLocaleTimeString('fr-FR') : 'à l’instant'}
                  </Typography>
                </Stack>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  Les données importées doivent être validées pour apparaître sur toute la plateforme.
                </Typography>
                <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                  <Box sx={{ px: 1.2, py: 0.5, borderRadius: 2, bgcolor: 'rgba(255, 159, 67, 0.12)', color: '#D97706', fontSize: 12, fontWeight: 700 }}>
                    En attente
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    {pendingPatientImportStatus.requestedBy || 'Utilisateur'}
                  </Typography>
                </Stack>
              </Box>
            </Box>
          ) : (
            <Box sx={{ p: 2, textAlign: 'center' }}>
              <Typography variant="body2" color="text.secondary">
                Aucune notification à afficher.
              </Typography>
            </Box>
          )}
        </Box>
      </Popover>
    </Card>
  );
}

export default AppSidebar;
