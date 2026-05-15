import React, { useContext, useMemo, useState } from 'react';
import {
  Alert,
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Chip,
  Grid,
  MenuItem,
  Divider,
  Stack,
  TextField,
  Typography,
  Container,
  Paper,
} from '@mui/material';
import api from '../../services/api/axios';
import { AuthContext } from '../../context/AuthContext';
import AppSidebar from '../../components/common/AppSidebar';
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import LanguageOutlinedIcon from '@mui/icons-material/LanguageOutlined';
import { useLanguage } from '../../context/LanguageContext';

const PROFILE_THEME = {
  deepNavy: '#1e2d5a',
  medicalBlue: '#3d5a8a',
  softRose: '#9e3d6a',
  border: 'rgba(61,90,138,.12)',
};

const softCardSx = {
  elevation: 0,
  border: `1px solid ${PROFILE_THEME.border}`,
  background: 'linear-gradient(180deg, rgba(255,255,255,.98), rgba(247,250,255,.94))',
  borderRadius: 3,
};

const infoRowSx = {
  p: 1.5,
  borderRadius: 2,
  border: `1px solid ${PROFILE_THEME.border}`,
  bgcolor: 'rgba(255,255,255,.8)',
};

function Profile() {
  const { user } = useContext(AuthContext);
  const { language, setLanguage, t } = useLanguage();
  const [form, setForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  const userInitials = useMemo(() => {
    const first = (user?.prenom || '').trim();
    const last = (user?.nom || '').trim();
    const initials = `${first[0] || ''}${last[0] || ''}`.trim();
    return initials || 'U';
  }, [user?.nom, user?.prenom]);

  const auditItems = useMemo(() => ([
    t('auditActionCreateUser'),
    t('auditActionUpdateUser'),
    t('auditActionDeleteUser'),
    t('auditActionViewPassword'),
    t('auditActionChangePassword'),
  ]), [t]);

  const canViewAuditSummary = ['super_admin', 'chef_service'].includes(user?.role);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validations
    if (!form.currentPassword.trim()) {
      setMessage({ type: 'error', text: t('currentPasswordError') });
      return;
    }

    if (!form.newPassword.trim()) {
      setMessage({ type: 'error', text: t('newPasswordError') });
      return;
    }

    if (form.newPassword.length < 8) {
      setMessage({ type: 'error', text: t('passwordLengthError') });
      return;
    }

    if (form.newPassword !== form.confirmPassword) {
      setMessage({ type: 'error', text: t('passwordMismatchError') });
      return;
    }

    if (form.newPassword === form.currentPassword) {
      setMessage({ type: 'error', text: t('passwordSameError') });
      return;
    }

    setLoading(true);
    try {
      // Endpoint pour changer le mot de passe de l'utilisateur connecté
      await api.post('/auth/change-password/', {
        current_password: form.currentPassword,
        new_password: form.newPassword,
      });

      setMessage({ type: 'success', text: t('passwordSuccess') });
      setForm({
        currentPassword: '',
        newPassword: '',
        confirmPassword: '',
      });
    } catch (error) {
      const errorMsg = error.response?.data?.error || 
                       error.response?.data?.non_field_errors?.[0] ||
                       t('passwordGenericError');
      setMessage({ type: 'error', text: errorMsg });
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <AppSidebar />
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Paper
          elevation={0}
          sx={{
            p: { xs: 2.5, md: 3.5 },
            mb: 3,
            borderRadius: 5,
            color: 'white',
            overflow: 'hidden',
            background: `linear-gradient(135deg, ${PROFILE_THEME.deepNavy} 0%, ${PROFILE_THEME.medicalBlue} 52%, ${PROFILE_THEME.softRose} 100%)`,
            boxShadow: '0 24px 60px rgba(15, 23, 42, 0.12)',
          }}
        >
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2.5} alignItems={{ xs: 'flex-start', md: 'center' }}>
            <Avatar sx={{ width: 72, height: 72, bgcolor: 'rgba(255,255,255,.18)', color: 'white', fontWeight: 900, fontSize: 26 }}>
              {userInitials}
            </Avatar>
            <Box sx={{ flex: 1 }}>
              <Stack spacing={1}>
                <Chip
                  label={t('profileTitle')}
                  sx={{ alignSelf: 'flex-start', bgcolor: 'rgba(255,255,255,.16)', color: 'white', fontWeight: 800 }}
                />
                <Typography variant="h4" fontWeight={900} sx={{ letterSpacing: '-.04em' }}>
                  {user?.prenom || ''} {user?.nom || ''}
                </Typography>
                <Typography variant="body1" sx={{ maxWidth: 900, color: 'rgba(255,255,255,.92)' }}>
                  Gérez votre mot de passe, changez la langue de la plateforme et retrouvez les actions d’audit liées au compte.
                </Typography>
              </Stack>
            </Box>
            <Stack direction="row" spacing={1.25} flexWrap="wrap" sx={{ gap: 1.25 }}>
              <Chip label={user?.role || '-'} sx={{ bgcolor: 'rgba(255,255,255,.18)', color: 'white', fontWeight: 800 }} />
              <Chip label={t('languageBadge') + `: ${language === 'fr' ? t('french') : t('english')}`} sx={{ bgcolor: 'rgba(255,255,255,.18)', color: 'white', fontWeight: 800 }} />
            </Stack>
          </Stack>
        </Paper>

        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <Stack spacing={3}>
              <Card sx={softCardSx}>
                <CardContent sx={{ p: 3 }}>
                  <Stack spacing={2}>
                    <Typography variant="overline" fontWeight={900} sx={{ color: PROFILE_THEME.softRose, letterSpacing: 1.2 }}>
                      {t('profileTitleSmall')}
                    </Typography>
                    <Divider />
                    <Stack spacing={1.5}>
                      <Box sx={infoRowSx}>
                        <Typography variant="caption" color="text.secondary">Email</Typography>
                        <Typography variant="body1" fontWeight={700} sx={{ wordBreak: 'break-word' }}>{user?.email || '-'}</Typography>
                      </Box>
                      <Box sx={infoRowSx}>
                        <Typography variant="caption" color="text.secondary">{t('role')}</Typography>
                        <Typography variant="body1" fontWeight={700}>{user?.role || '-'}</Typography>
                      </Box>
                      <Box sx={infoRowSx}>
                        <Typography variant="caption" color="text.secondary">{t('telephone')}</Typography>
                        <Typography variant="body1" fontWeight={700}>{user?.telephone || '-'}</Typography>
                      </Box>
                    </Stack>
                  </Stack>
                </CardContent>
              </Card>

              <Card sx={softCardSx}>
                <CardContent sx={{ p: 3 }}>
                  <Stack spacing={2}>
                    <Stack direction="row" spacing={1.25} alignItems="center">
                      <LanguageOutlinedIcon sx={{ color: PROFILE_THEME.medicalBlue, fontSize: 22 }} />
                      <Typography variant="h6" fontWeight={900} sx={{ color: PROFILE_THEME.deepNavy }}>
                        {t('languageSectionTitle')}
                      </Typography>
                    </Stack>
                    <Typography variant="body2" color="text.secondary">
                      {t('languageSectionDescription')}
                    </Typography>
                    <TextField
                      select
                      label={t('languageLabel')}
                      value={language}
                      onChange={(e) => setLanguage(e.target.value)}
                      size="small"
                      fullWidth
                    >
                      <MenuItem value="fr">{t('french')}</MenuItem>
                      <MenuItem value="en">{t('english')}</MenuItem>
                    </TextField>
                  </Stack>
                </CardContent>
              </Card>

              {canViewAuditSummary ? (
                <Card sx={softCardSx}>
                  <CardContent sx={{ p: 3 }}>
                    <Stack spacing={2}>
                      <Stack direction="row" spacing={1.25} alignItems="center">
                        <Typography variant="h6" fontWeight={900} sx={{ color: PROFILE_THEME.deepNavy }}>
                          {t('auditCardTitle')}
                        </Typography>
                      </Stack>
                      <Typography variant="body2" color="text.secondary">
                        {t('auditCardDescription')}
                      </Typography>
                      <Chip
                        label={t('auditViewerHint')}
                        sx={{ alignSelf: 'flex-start', bgcolor: 'rgba(61,90,138,.10)', color: PROFILE_THEME.medicalBlue, fontWeight: 800 }}
                      />
                      <Stack spacing={1}>
                        {auditItems.map((item) => (
                          <Box key={item} sx={{ ...infoRowSx, display: 'flex', alignItems: 'center', gap: 1.25 }}>
                            <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: PROFILE_THEME.softRose, flexShrink: 0 }} />
                            <Typography variant="body2" fontWeight={700}>{item}</Typography>
                          </Box>
                        ))}
                      </Stack>
                    </Stack>
                  </CardContent>
                </Card>
              ) : (
                <Card sx={softCardSx}>
                  <CardContent sx={{ p: 3 }}>
                    <Stack spacing={1.5}>
                      <Typography variant="h6" fontWeight={900} sx={{ color: PROFILE_THEME.deepNavy }}>
                        {t('auditCardTitle')}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {t('auditCardDescription')}
                      </Typography>
                      <Chip
                        label={t('auditViewerHint')}
                        sx={{ alignSelf: 'flex-start', bgcolor: 'rgba(61,90,138,.10)', color: PROFILE_THEME.medicalBlue, fontWeight: 800 }}
                      />
                    </Stack>
                  </CardContent>
                </Card>
              )}
            </Stack>
          </Grid>

          <Grid item xs={12} md={8}>
            <Card sx={softCardSx}>
              <CardContent sx={{ p: { xs: 2.5, md: 3.5 } }}>
                <Stack spacing={3}>
                  <Stack direction="row" spacing={1.5} alignItems="center">
                    <LockOutlinedIcon sx={{ color: PROFILE_THEME.softRose, fontSize: 24 }} />
                    <Box>
                      <Typography variant="h6" fontWeight={900} sx={{ color: PROFILE_THEME.deepNavy }}>
                        {t('changePasswordTitle')}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Mettez à jour votre accès en toute sécurité avec confirmation du mot de passe actuel.
                      </Typography>
                    </Box>
                  </Stack>

                  {message.text && (
                    <Alert severity={message.type} onClose={() => setMessage({ type: '', text: '' })}>
                      {message.text}
                    </Alert>
                  )}

                  <Box component="form" onSubmit={handleSubmit}>
                    <Stack spacing={2}>
                      <TextField
                        label={t('currentPassword')}
                        type="password"
                        name="currentPassword"
                        value={form.currentPassword}
                        onChange={handleChange}
                        fullWidth
                        size="small"
                        disabled={loading}
                        helperText={t('currentPasswordHelper')}
                      />

                      <TextField
                        label={t('newPassword')}
                        type="password"
                        name="newPassword"
                        value={form.newPassword}
                        onChange={handleChange}
                        fullWidth
                        size="small"
                        disabled={loading}
                        helperText={t('newPasswordHelper')}
                      />

                      <TextField
                        label={t('confirmPassword')}
                        type="password"
                        name="confirmPassword"
                        value={form.confirmPassword}
                        onChange={handleChange}
                        fullWidth
                        size="small"
                        disabled={loading}
                        helperText={t('confirmPasswordHelper')}
                      />

                      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
                        <Button
                          type="submit"
                          variant="contained"
                          disabled={loading}
                          fullWidth
                          sx={{
                            minHeight: 46,
                            borderRadius: 999,
                            background: `linear-gradient(135deg, ${PROFILE_THEME.deepNavy} 0%, ${PROFILE_THEME.medicalBlue} 48%, ${PROFILE_THEME.softRose} 100%)`,
                            textTransform: 'none',
                            fontWeight: 800,
                            boxShadow: '0 16px 30px rgba(26,107,138,.22)',
                          }}
                        >
                          {loading ? <CircularProgress size={20} sx={{ mr: 1, color: 'white' }} /> : null}
                          {loading ? '...' : t('submitPassword')}
                        </Button>
                        <Button
                          type="button"
                          variant="outlined"
                          onClick={() => {
                            setForm({ currentPassword: '', newPassword: '', confirmPassword: '' });
                            setMessage({ type: '', text: '' });
                          }}
                          disabled={loading}
                          fullWidth
                          sx={{
                            minHeight: 46,
                            borderRadius: 999,
                            textTransform: 'none',
                            fontWeight: 800,
                          }}
                        >
                          {t('cancel')}
                        </Button>
                      </Stack>
                    </Stack>
                  </Box>
                </Stack>
              </CardContent>
            </Card>

            <Card sx={{ ...softCardSx, mt: 3 }}>
              <CardContent sx={{ p: { xs: 2.5, md: 3 } }}>
                <Stack spacing={1.5}>
                  <Typography variant="subtitle1" fontWeight={900} sx={{ color: PROFILE_THEME.deepNavy }}>
                    Résumé du profil
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Le profil centralise la gestion du compte, le changement de mot de passe et la langue de l’interface.
                  </Typography>
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Container>
    </>
  );
}

export default Profile;
