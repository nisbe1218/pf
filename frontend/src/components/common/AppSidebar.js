import React, { useEffect, useState } from 'react';
import {
  Avatar,
  Badge,
  Box,
  IconButton,
  Stack,
  SvgIcon,
  Popover,
  Typography,
  Button,
} from '@mui/material';
import HomeIcon from '@mui/icons-material/Home';
import DataObjectOutlinedIcon from '@mui/icons-material/DataObjectOutlined';
import PsychologyAltOutlinedIcon from '@mui/icons-material/PsychologyAltOutlined';
import NotificationsActiveOutlinedIcon from '@mui/icons-material/NotificationsActiveOutlined';
import LogoutIcon from '@mui/icons-material/Logout';
import { useLocation, useNavigate } from 'react-router-dom';
import { useContext } from 'react';
import { AuthContext } from '../../context/AuthContext';

function AppSidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout } = useContext(AuthContext);
  const isDashboardActive = location.pathname.startsWith('/dashboard');
  const isPatientsActive = location.pathname.startsWith('/patients');
  const isModelAiActive = location.pathname.startsWith('/modele-ai');

  const [pendingPatientImportStatus, setPendingPatientImportStatus] = useState(null);
  const [notificationAnchorEl, setNotificationAnchorEl] = useState(null);

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

  const iconBtn = (active) => ({
    width: 42,
    height: 42,
    borderRadius: '50%',
    background: active ? '#1a1a1a' : 'rgba(255,255,255,0.08)',
    color: active ? 'white' : 'rgba(255,255,255,0.55)',
    transition: 'background 180ms ease, color 180ms ease, transform 150ms ease',
    '&:hover': {
      background: active ? '#111' : 'rgba(255,255,255,0.18)',
      color: 'white',
      transform: 'scale(1.08)',
    },
  });

  return (
    <>
      <Box
        sx={{
          position: { md: 'fixed' },
          top: { md: '50%' },
          left: { md: 16 },
          transform: { md: 'translateY(-50%)' },
          zIndex: 1200,
          display: 'flex',
          flexDirection: { xs: 'row', md: 'column' },
          alignItems: 'center',
          gap: 1.2,
          px: 1.2,
          py: 1.8,
          borderRadius: '40px',
          background: 'linear-gradient(180deg, #2C6975 0%, #3d8a78 100%)',
          boxShadow: '0 8px 32px rgba(44,105,117,0.28)',
        }}
      >
        {/* Logo */}
        <SvgIcon
          viewBox="0 0 64 64"
          sx={{
            width: 34,
            height: 34,
            borderRadius: '50%',
            bgcolor: 'rgba(255,255,255,0.15)',
            p: 0.7,
            mb: { md: 0.5 },
          }}
        >
          <circle cx="32" cy="32" r="30" fill="rgba(255,255,255,0.08)" stroke="white" strokeOpacity="0.25" strokeWidth="2" />
          <path d="M17 20c-4 5-4 12-1 17 3 5 9 7 13 4 4-3 5-8 4-13-1-5-4-9-10-10-4-1-6 0-6 2z" fill="#4aa4d6" />
          <path d="M47 20c4 5 4 12 1 17-3 5-9 7-13 4-4-3-5-8-4-13 1-5 4-9 10-10 4-1 6 0 6 2z" fill="#f0755a" />
          <path d="M24 25c-2 2-3 6-2 9" stroke="rgba(255,255,255,0.85)" strokeWidth="2" strokeLinecap="round" fill="none" />
          <path d="M40 25c2 2 3 6 2 9" stroke="rgba(255,255,255,0.85)" strokeWidth="2" strokeLinecap="round" fill="none" />
        </SvgIcon>

        {/* Séparateur */}
        <Box sx={{ width: { xs: 1, md: 28 }, height: { xs: 28, md: 1 }, bgcolor: 'rgba(255,255,255,0.18)', borderRadius: 1 }} />

        {/* Dashboard */}
        <IconButton onClick={() => navigate('/dashboard')} sx={iconBtn(isDashboardActive)}>
          <HomeIcon sx={{ fontSize: 20 }} />
        </IconButton>

        {/* Patients */}
        <IconButton onClick={() => navigate('/patients')} sx={iconBtn(isPatientsActive)}>
          <DataObjectOutlinedIcon sx={{ fontSize: 20 }} />
        </IconButton>

        {/* Modèle AI */}
        <IconButton onClick={() => navigate('/modele-ai')} sx={iconBtn(isModelAiActive)}>
          <PsychologyAltOutlinedIcon sx={{ fontSize: 20 }} />
        </IconButton>

        {/* Séparateur */}
        <Box sx={{ width: { xs: 1, md: 28 }, height: { xs: 28, md: 1 }, bgcolor: 'rgba(255,255,255,0.18)', borderRadius: 1 }} />

        {/* Notifications */}
        <IconButton
          onClick={(e) => setNotificationAnchorEl(e.currentTarget)}
          sx={iconBtn(false)}
        >
          <Badge
            badgeContent={pendingPatientImportStatus ? 1 : 0}
            color="error"
            invisible={!pendingPatientImportStatus}
            sx={{ '& .MuiBadge-badge': { fontSize: 9, minWidth: 14, height: 14 } }}
          >
            <NotificationsActiveOutlinedIcon sx={{ fontSize: 20 }} />
          </Badge>
        </IconButton>

        {/* Séparateur */}
        <Box sx={{ width: { xs: 1, md: 28 }, height: { xs: 28, md: 1 }, bgcolor: 'rgba(255,255,255,0.18)', borderRadius: 1 }} />

        {/* Déconnexion */}
        <IconButton
          onClick={() => { logout(); navigate('/login'); }}
          sx={{
            width: 42,
            height: 42,
            borderRadius: '50%',
            background: 'rgba(255,255,255,0.08)',
            color: 'rgba(255,180,180,0.8)',
            transition: 'background 180ms ease, color 180ms ease, transform 150ms ease',
            '&:hover': {
              background: 'rgba(220,60,60,0.22)',
              color: '#ff8a80',
              transform: 'scale(1.08)',
            },
          }}
        >
          <LogoutIcon sx={{ fontSize: 20 }} />
        </IconButton>
      </Box>

      {/* Popover notifications */}
      <Popover
        open={Boolean(notificationAnchorEl)}
        anchorEl={notificationAnchorEl}
        onClose={() => setNotificationAnchorEl(null)}
        anchorOrigin={{ vertical: 'center', horizontal: 'right' }}
        transformOrigin={{ vertical: 'center', horizontal: 'left' }}
        PaperProps={{ sx: { width: 340, borderRadius: 3, boxShadow: '0 24px 60px rgba(0,0,0,0.14)', ml: 1 } }}
      >
        <Box sx={{ p: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid rgba(0,0,0,0.08)' }}>
          <Box>
            <Typography variant="h6" fontWeight={700}>Notification</Typography>
            <Typography variant="caption" color="text.secondary">
              {pendingPatientImportStatus ? '1 nouvelle alerte' : 'Aucune notification'}
            </Typography>
          </Box>
          {pendingPatientImportStatus && (
            <Button size="small" onClick={() => setNotificationAnchorEl(null)}>
              Marquer comme lu
            </Button>
          )}
        </Box>
        <Box sx={{ p: 2 }}>
          {pendingPatientImportStatus ? (
            <Box sx={{ display: 'flex', gap: 2, p: 2, borderRadius: 3, bgcolor: 'background.paper', boxShadow: '0 12px 24px rgba(15,23,42,0.06)' }}>
              <Avatar sx={{ bgcolor: '#2C6975', width: 48, height: 48 }}>
                <NotificationsActiveOutlinedIcon />
              </Avatar>
              <Box sx={{ flex: 1 }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                  <Typography variant="subtitle2" fontWeight={700}>Importation patient en attente</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {pendingPatientImportStatus.timestamp
                      ? new Date(pendingPatientImportStatus.timestamp).toLocaleTimeString('fr-FR')
                      : 'à l\'instant'}
                  </Typography>
                </Stack>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  Les données importées doivent être validées pour apparaître sur toute la plateforme.
                </Typography>
                <Stack direction="row" spacing={1} alignItems="center">
                  <Box sx={{ px: 1.2, py: 0.5, borderRadius: 2, bgcolor: 'rgba(255,159,67,0.12)', color: '#D97706', fontSize: 12, fontWeight: 700 }}>
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
              <Typography variant="body2" color="text.secondary">Aucune notification à afficher.</Typography>
            </Box>
          )}
        </Box>
      </Popover>
    </>
  );
}

export default AppSidebar;