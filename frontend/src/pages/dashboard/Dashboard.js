import React, { useContext, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Avatar,
  Chip,
  Divider,
  Grid,
  InputAdornment,
  MenuItem,
  Paper,
  Stack,
  SvgIcon,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  Typography,
} from '@mui/material';
import api from '../../services/api/axios';
import { AuthContext } from '../../context/AuthContext';
import CallOutlinedIcon from '@mui/icons-material/CallOutlined';
import AppSidebar from '../../components/common/AppSidebar';
import EditOutlinedIcon from '@mui/icons-material/EditOutlined';
import DeleteOutlineOutlinedIcon from '@mui/icons-material/DeleteOutlineOutlined';
import LogoutOutlinedIcon from '@mui/icons-material/LogoutOutlined';
import { useLocation, useNavigate } from 'react-router-dom';

const roleLabels = {
  super_admin: 'Super Administrateur',
  chef_service: 'Chef de Service',
  professeur: 'Professeur',
  resident: 'Résident',
};

const roleDescriptions = {
  super_admin: 'Gestion globale du système, supervision des accès et traçabilité complète.',
  chef_service: 'Supervision médicale, gestion des comptes du service et validation des données.',
  professeur: 'Analyse clinique, suivi des patients et exploitation des modèles prédictifs.',
  resident: 'Utilisation opérationnelle, consultation des dossiers et application des prédictions IA.',
};

const emptyForm = {
  id: null,
  email: '',
  nom: '',
  prenom: '',
  telephone: '',
  role_id: '',
  is_active: true,
  password: '',
};

const formatHashSnippet = (hash) => {
  if (!hash) {
    return '';
  }

  if (hash.length <= 34) {
    return hash;
  }

  return `${hash.slice(0, 18)}…${hash.slice(-10)}`;
};

function Dashboard() {
  const { user, refreshProfile, logout } = useContext(AuthContext);
  const navigate = useNavigate();
  const location = useLocation();
  const [roles, setRoles] = useState([]);
  const [users, setUsers] = useState([]);
  const [search, setSearch] = useState('');
  const [form, setForm] = useState(emptyForm);
  const [adminPassword, setAdminPassword] = useState('');
  const [revealDialogOpen, setRevealDialogOpen] = useState(false);
  const [revealTargetUser, setRevealTargetUser] = useState(null);
  const [revealDialogPassword, setRevealDialogPassword] = useState('');
  const [revealing, setRevealing] = useState(false);
  const [revealedHashes, setRevealedHashes] = useState({});
  const [loadingData, setLoadingData] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const isAdminScope = user?.role === 'super_admin' || user?.role === 'chef_service';
  const isDashboardActive = location.pathname.startsWith('/dashboard');
  const isPatientsActive = location.pathname.startsWith('/patients');
  const isModelAiActive = location.pathname.startsWith('/modele-ai');

  const stats = useMemo(() => {
    const managedUsers = users.filter((managedUser) => {
      if (user?.role === 'super_admin') {
        return true;
      }
      return managedUser.role?.nom === 'professeur' || managedUser.role?.nom === 'resident';
    });

    return {
      visibleUsers: managedUsers.length,
      activeUsers: managedUsers.filter((managedUser) => managedUser.is_active).length,
      inactiveUsers: managedUsers.filter((managedUser) => !managedUser.is_active).length,
      professorsCount: managedUsers.filter((managedUser) => managedUser.role?.nom === 'professeur').length,
      residentsCount: managedUsers.filter((managedUser) => managedUser.role?.nom === 'resident').length,
      rolesCount: roles.length,
    };
  }, [roles.length, user?.role, users]);

  const manageableUsers = useMemo(() => {
    const lower = search.trim().toLowerCase();
    return users.filter((managedUser) => {
      const allowed = user?.role === 'super_admin'
        || managedUser.role?.nom === 'professeur'
        || managedUser.role?.nom === 'resident';
      if (!allowed) {
        return false;
      }
      if (!lower) {
        return true;
      }
      return [
        managedUser.email,
        managedUser.nom,
        managedUser.prenom,
        managedUser.role?.label,
        managedUser.role?.nom,
      ].some((value) => value?.toLowerCase().includes(lower));
    });
  }, [user?.role, users, search]);

  const resolveRoleById = (roleId) => {
    return roles.find((role) => String(role.id) === String(roleId)) || null;
  };

  const loadManagementData = async () => {
    if (!isAdminScope) {
      return;
    }

    setLoadingData(true);
    setError('');
    try {
      const [rolesResponse, usersResponse] = await Promise.all([
        api.get('auth/roles/'),
        api.get('auth/utilisateurs/'),
      ]);
      setRoles(rolesResponse.data);
      setUsers(usersResponse.data);
    } catch (requestError) {
      setError('Impossible de charger les comptes et les rôles.');
    } finally {
      setLoadingData(false);
    }
  };

  useEffect(() => {
    loadManagementData();
  }, [isAdminScope]);

  const resetForm = () => {
    setForm(emptyForm);
    setError('');
    setSuccess('');
  };

  const openRevealDialog = (selectedUser) => {
    setRevealTargetUser(selectedUser);
    setRevealDialogPassword('');
    setRevealDialogOpen(true);
    setError('');
    setSuccess('');
  };

  const closeRevealDialog = () => {
    setRevealDialogOpen(false);
    setRevealTargetUser(null);
    setRevealDialogPassword('');
    setRevealing(false);
  };

  const revealPasswordHash = async () => {
    if (!revealTargetUser) {
      return;
    }

    if (!revealDialogPassword) {
      setError('Saisissez le mot de passe du compte connecté.');
      return;
    }

    setRevealing(true);
    setError('');
    setSuccess('');

    try {
      const response = await api.post('auth/confirm-password/', {
        password: revealDialogPassword,
      });

      if (!response.data?.confirmed) {
        setError('Confirmation refusée.');
        return;
      }

      setRevealedHashes((currentHashes) => ({
        ...currentHashes,
        [revealTargetUser.id]: revealTargetUser.password_hash,
      }));
      setSuccess('Mot de passe haché affiché.');
    } catch (requestError) {
      const apiMessage = requestError?.response?.data?.error
        || requestError?.response?.data?.detail
        || Object.values(requestError?.response?.data || {})[0];
      setError(apiMessage || 'Impossible d’afficher le mot de passe haché.');
    } finally {
      setRevealing(false);
    }
  };

  const beginEdit = (selectedUser) => {
    setForm({
      id: selectedUser.id,
      email: selectedUser.email,
      nom: selectedUser.nom,
      prenom: selectedUser.prenom,
      telephone: selectedUser.telephone || '',
      role_id: selectedUser.role?.id || '',
      is_active: selectedUser.is_active,
      password: '',
    });
    setError('');
    setSuccess('');
  };

  const handleChange = (event) => {
    const { name, value, type, checked } = event.target;
    setForm((current) => ({
      ...current,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleSaveUser = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');

    try {
      const payload = {
        email: form.email,
        nom: form.nom,
        prenom: form.prenom,
        telephone: form.telephone,
        role_id: form.role_id,
        is_active: form.is_active,
        confirmation_password: adminPassword,
      };

      const resolvedRole = resolveRoleById(form.role_id);

      if (form.id) {
        const response = await api.put(`auth/utilisateurs/${form.id}/`, payload);
        setUsers((currentUsers) => currentUsers.map((existingUser) => (
          existingUser.id === form.id
            ? { ...existingUser, ...response.data, role: resolvedRole || existingUser.role }
            : existingUser
        )));
        if (String(form.id) === String(user?.id)) {
          await refreshProfile();
        }
        setSuccess('Compte modifié avec succès.');
      } else {
        const response = await api.post('auth/utilisateurs/', {
          ...payload,
          password: form.password,
        });
        setUsers((currentUsers) => [{ ...response.data, role: resolvedRole }, ...currentUsers]);
        setSuccess('Compte créé avec succès.');
      }

      await loadManagementData();
      resetForm();
    } catch (requestError) {
      const apiMessage = requestError?.response?.data?.error
        || requestError?.response?.data?.detail
        || Object.values(requestError?.response?.data || {})[0];
      setError(apiMessage || 'Impossible d’enregistrer le compte. Vérifie les droits et la confirmation.');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteUser = async (selectedUser) => {
    const confirmed = window.confirm(`Supprimer le compte ${selectedUser.email} ?`);
    if (!confirmed) {
      return;
    }

    setSaving(true);
    setError('');
    setSuccess('');

    try {
      await api.delete(`auth/utilisateurs/${selectedUser.id}/`, {
        data: { confirmation_password: adminPassword },
      });
      setUsers((currentUsers) => currentUsers.filter((managedUser) => managedUser.id !== selectedUser.id));
      setSuccess('Compte supprimé avec succès.');
      await loadManagementData();
      resetForm();
    } catch (requestError) {
      const apiMessage = requestError?.response?.data?.error
        || requestError?.response?.data?.detail
        || Object.values(requestError?.response?.data || {})[0];
      setError(apiMessage || 'Suppression refusée ou confirmation invalide.');
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <Box
      sx={{
        flexGrow: 1,
        minHeight: '100vh',
        py: { xs: 2, md: 3 },
        px: { xs: 0, md: 1 },
        background: 'radial-gradient(circle at top left, rgba(102, 190, 219, 0.18), transparent 22%), radial-gradient(circle at bottom right, rgba(163, 221, 228, 0.14), transparent 18%), linear-gradient(180deg, #eaf7fb 0%, #f4fbff 100%)',
      }}
    >
      <Grid container spacing={2} alignItems="flex-start">
        <Grid item xs={12} md={3} lg={2}>
          <AppSidebar />
        </Grid>

        <Grid item xs={12} md={9} lg={10}>
      <Paper
        elevation={0}
        sx={{
          mb: 3,
          p: { xs: 2.5, md: 3.5 },
          borderRadius: 5,
          background: 'linear-gradient(135deg, #2C6975 0%, #68B2A0 45%, #CDE0C9 100%)',
          color: 'white',
          overflow: 'hidden',
          position: 'relative',
          boxShadow: '0 28px 70px rgba(15, 23, 42, 0.14)',
        }}
      >
        <Box
          sx={{
            position: 'absolute',
            inset: 'auto -80px -80px auto',
            width: 220,
            height: 220,
            borderRadius: '50%',
            background: 'rgba(255,255,255,0.08)',
            filter: 'blur(2px)',
          }}
        />
        <Stack spacing={1.25} sx={{ position: 'relative' }}>
          <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" spacing={2}>
            <Chip
              label={roleLabels[user?.role] || 'Utilisateur'}
              sx={{ alignSelf: 'flex-start', bgcolor: 'rgba(255,255,255,0.18)', color: 'white' }}
            />
            <Button
              onClick={handleLogout}
              variant="outlined"
              startIcon={<LogoutOutlinedIcon />}
              sx={{
                color: 'white',
                borderColor: 'rgba(255,255,255,0.35)',
                alignSelf: 'flex-start',
                '&:hover': {
                  borderColor: 'rgba(255,255,255,0.75)',
                  backgroundColor: 'rgba(255,255,255,0.08)',
                },
              }}
            >
              Déconnexion
            </Button>
          </Stack>
          <Typography variant="h4" fontWeight={900}>
            Tableau de bord RBAC
          </Typography>
          <Typography variant="body1" sx={{ maxWidth: 760, opacity: 0.92 }}>
            Gestion hiérarchisée des utilisateurs, confirmation des opérations sensibles et accès limité aux rôles autorisés.
          </Typography>
        </Stack>
      </Paper>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 3 }}>{success}</Alert>}

      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={4}>
          <Card elevation={0} sx={{ height: '100%', borderTop: '4px solid', borderTopColor: '#2C6975' }}>
            <CardContent sx={{ p: 2.5 }}>
              <Typography variant="overline" color="text.secondary">
                Comptes visibles
              </Typography>
              <Typography variant="h4" fontWeight={800} sx={{ mt: 0.5 }}>
                {stats.visibleUsers}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Selon votre périmètre d’accès.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <Card elevation={0} sx={{ height: '100%', borderTop: '4px solid', borderTopColor: '#68B2A0' }}>
            <CardContent sx={{ p: 2.5 }}>
              <Typography variant="overline" color="text.secondary">
                Actifs
              </Typography>
              <Typography variant="h4" fontWeight={800} sx={{ mt: 0.5 }}>
                {stats.activeUsers}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Comptes utilisables immédiatement.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <Card elevation={0} sx={{ height: '100%', borderTop: '4px solid', borderTopColor: '#CDE0C9' }}>
            <CardContent sx={{ p: 2.5 }}>
              <Typography variant="overline" color="text.secondary">
                Inactifs
              </Typography>
              <Typography variant="h4" fontWeight={800} sx={{ mt: 0.5 }}>
                {stats.inactiveUsers}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Comptes suspendus ou revus.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <Card elevation={0} sx={{ height: '100%', borderTop: '4px solid', borderTopColor: '#2C6975' }}>
            <CardContent sx={{ p: 2.5 }}>
              <Typography variant="overline" color="text.secondary">
                Professeurs
              </Typography>
              <Typography variant="h4" fontWeight={800} sx={{ mt: 0.5 }}>
                {stats.professorsCount}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Nombre de professeurs gérés.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <Card elevation={0} sx={{ height: '100%', borderTop: '4px solid', borderTopColor: '#68B2A0' }}>
            <CardContent sx={{ p: 2.5 }}>
              <Typography variant="overline" color="text.secondary">
                Résidents
              </Typography>
              <Typography variant="h4" fontWeight={800} sx={{ mt: 0.5 }}>
                {stats.residentsCount}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Nombre de résidents gérés.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={4}>
          <Card elevation={0} sx={{ height: '100%', borderTop: '4px solid', borderTopColor: '#E0ECDE' }}>
            <CardContent sx={{ p: 2.5 }}>
              <Typography variant="overline" color="text.secondary">
                Rôles chargés
              </Typography>
              <Typography variant="h4" fontWeight={800} sx={{ mt: 0.5 }}>
                {stats.rolesCount}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Profils disponibles dans le système.
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        <Grid item xs={12} xl={isAdminScope ? 4 : 12}>
          <Stack spacing={3}>
            <Card
              elevation={0}
              sx={{
                borderRadius: 5,
                overflow: 'hidden',
                border: '1px solid rgba(94, 115, 141, 0.12)',
                background: 'linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(239,246,249,0.96) 100%)',
                position: 'relative',
                boxShadow: '0 18px 52px rgba(15, 23, 42, 0.08)',
              }}
            >
              <Box
                sx={{
                  height: 10,
                  background: 'linear-gradient(90deg, #165a72 0%, #1f9d8a 55%, #d18f47 100%)',
                }}
              />
              <CardContent sx={{ p: 0 }}>
                <Box sx={{ p: 3 }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={2} sx={{ mb: 2.5 }}>
                    <Box>
                      <Typography variant="overline" color="primary.main" fontWeight={800}>
                        Session active
                      </Typography>
                      <Typography variant="h5" fontWeight={900} sx={{ mt: 0.5 }}>
                        Profil connecté
                      </Typography>
                    </Box>
                    <Chip
                      label={roleLabels[user?.role] || 'Utilisateur'}
                      sx={{ fontWeight: 800, bgcolor: 'rgba(44, 105, 117, 0.10)', color: '#2C6975' }}
                    />
                  </Stack>

                  <Box
                    sx={{
                      p: 2.25,
                      borderRadius: 4,
                      background: 'linear-gradient(135deg, rgba(44,105,117,0.10), rgba(104,178,160,0.08))',
                      border: '1px solid rgba(108, 178, 160, 0.18)',
                      mb: 2.5,
                    }}
                  >
                    <Stack direction="row" spacing={2} alignItems="center">
                      <Avatar
                        sx={{
                          width: 58,
                          height: 58,
                          bgcolor: '#2C6975',
                          fontWeight: 900,
                          boxShadow: '0 10px 24px rgba(44, 105, 117, 0.25)',
                        }}
                      >
                        {(user?.prenom?.[0] || '') + (user?.nom?.[0] || '')}
                      </Avatar>
                      <Box>
                        <Typography variant="caption" color="text.secondary">Nom complet</Typography>
                        <Typography variant="h6" fontWeight={900} sx={{ lineHeight: 1.15 }}>
                          {user?.prenom || '-'} {user?.nom || ''}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                          {roleDescriptions[user?.role] || 'Accès limité au périmètre autorisé.'}
                        </Typography>
                      </Box>
                    </Stack>
                  </Box>

                  <Stack spacing={1.5}>
                    <Stack direction="row" spacing={1.25} flexWrap="wrap" useFlexGap>
                      <Chip size="small" label={user?.email || '-'} variant="outlined" sx={{ borderRadius: 2 }} />
                      <Chip size="small" label={user?.telephone || 'Téléphone non renseigné'} variant="outlined" sx={{ borderRadius: 2 }} />
                    </Stack>
                    <Divider sx={{ my: 0.5 }} />
                    <Box>
                      <Typography variant="caption" color="text.secondary">Nom</Typography>
                      <Typography variant="body1" fontWeight={600}>{user?.nom || '-'}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">Prénom</Typography>
                      <Typography variant="body1" fontWeight={600}>{user?.prenom || '-'}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">Email</Typography>
                      <Typography variant="body1" fontWeight={600}>{user?.email || '-'}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">Téléphone</Typography>
                      <Typography variant="body1" fontWeight={600}>{user?.telephone || '-'}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">Rôle</Typography>
                      <Typography variant="body1" fontWeight={600}>{roleLabels[user?.role] || '-'}</Typography>
                    </Box>
                  </Stack>
                </Box>
              </CardContent>
            </Card>
          </Stack>
        </Grid>

        {isAdminScope && (
          <Grid item xs={12} xl={8}>
            <Card elevation={0} sx={{ borderRadius: 4, mb: 3, border: '1px solid rgba(94, 115, 141, 0.12)' }}>
              <CardContent sx={{ p: 3 }}>
                <Stack
                  direction={{ xs: 'column', md: 'row' }}
                  spacing={2}
                  justifyContent="space-between"
                  alignItems={{ xs: 'stretch', md: 'center' }}
                  sx={{ mb: 2 }}
                >
                  <Box>
                    <Typography variant="h6" fontWeight={800}>
                      Gestion des comptes
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Super administrateurs et chefs de service gèrent uniquement les Professeurs et Résidents.
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                      Pour enregistrer une modification, saisissez votre mot de passe de validation puis définissez le mot de passe du compte créé si nécessaire.
                    </Typography>
                  </Box>
                  <Button onClick={loadManagementData} variant="outlined" disabled={loadingData} sx={{ minWidth: 130 }}>
                    {loadingData ? 'Chargement...' : 'Rafraîchir'}
                  </Button>
                </Stack>

                <Box component="form" onSubmit={handleSaveUser} sx={{ display: 'grid', gap: 2.25 }}>
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={6}>
                      <TextField
                        label="Email"
                        name="email"
                        value={form.email}
                        onChange={handleChange}
                        required
                        fullWidth
                        size="small"
                      />
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <TextField
                        label="Téléphone"
                        name="telephone"
                        value={form.telephone}
                        onChange={handleChange}
                        fullWidth
                        size="small"
                        placeholder="+212 6 12 34 56 78"
                        inputMode="tel"
                        helperText="Numéro du contact principal du compte."
                        InputProps={{
                          startAdornment: (
                            <InputAdornment position="start">
                              <CallOutlinedIcon fontSize="small" />
                            </InputAdornment>
                          ),
                        }}
                      />
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <TextField
                        label="Nom"
                        name="nom"
                        value={form.nom}
                        onChange={handleChange}
                        required
                        fullWidth
                        size="small"
                      />
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <TextField
                        label="Prénom"
                        name="prenom"
                        value={form.prenom}
                        onChange={handleChange}
                        required
                        fullWidth
                        size="small"
                      />
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <TextField
                        select
                        label="Rôle"
                        name="role_id"
                        value={form.role_id}
                        onChange={handleChange}
                        required
                        fullWidth
                        size="small"
                      >
                        <MenuItem value="">Sélectionner</MenuItem>
                        {roles.map((role) => (
                          <MenuItem key={role.id} value={role.id}>
                            {role.label || role.nom}
                          </MenuItem>
                        ))}
                      </TextField>
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <TextField
                        select
                        label="Statut"
                        name="is_active"
                        value={form.is_active ? 'true' : 'false'}
                        onChange={(event) => setForm((current) => ({
                          ...current,
                          is_active: event.target.value === 'true',
                        }))}
                        fullWidth
                        size="small"
                      >
                        <MenuItem value="true">Actif</MenuItem>
                        <MenuItem value="false">Inactif</MenuItem>
                      </TextField>
                    </Grid>
                  </Grid>

                  <TextField
                    label="Mot de passe de validation"
                    type="password"
                    value={adminPassword}
                    onChange={(event) => setAdminPassword(event.target.value)}
                    fullWidth
                    required
                    size="small"
                    helperText="Mot de passe du compte connecté, obligatoire pour créer, modifier ou révoquer un compte."
                  />

                  {!form.id && (
                    <TextField
                      label="Mot de passe du nouveau compte"
                      type="password"
                      name="password"
                      value={form.password}
                      onChange={handleChange}
                      fullWidth
                      required
                      size="small"
                      helperText="Ce mot de passe sera utilisé par l’utilisateur créé."
                    />
                  )}

                  <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
                    <Button type="submit" variant="contained" disabled={saving} fullWidth>
                      {form.id ? 'Modifier' : 'Créer'}
                    </Button>
                    <Button type="button" variant="outlined" onClick={resetForm} fullWidth>
                      Réinitialiser
                    </Button>
                  </Stack>
                </Box>
              </CardContent>
            </Card>

            <Card elevation={0} sx={{ borderRadius: 4, border: '1px solid rgba(94, 115, 141, 0.12)' }}>
              <CardContent sx={{ p: 3 }}>
                <Stack direction={{ xs: 'column', sm: 'row' }} alignItems="center" justifyContent="space-between" spacing={2} sx={{ mb: 2 }}>
                  <Typography variant="h6" fontWeight={800}>
                    Comptes gérés
                  </Typography>
                  <TextField
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Rechercher un utilisateur..."
                    size="small"
                    sx={{ width: { xs: '100%', sm: 320 } }}
                  />
                </Stack>
                <Grid container spacing={2}>
                  {manageableUsers.length ? manageableUsers.map((managedUser) => (
                    <Grid item xs={12} sm={6} md={4} key={managedUser.id}>
                      <Card
                        elevation={0}
                        sx={{
                          borderRadius: 4,
                          bgcolor: 'rgba(255,255,255,0.96)',
                          border: '1px solid rgba(94, 115, 141, 0.12)',
                          minHeight: 240,
                          display: 'flex',
                          flexDirection: 'column',
                          justifyContent: 'space-between',
                        }}
                      >
                        <CardContent sx={{ p: 2.5 }}>
                          <Stack spacing={1.5}>
                            <Stack direction="row" spacing={2} alignItems="center">
                              <Avatar sx={{ bgcolor: 'primary.main', width: 48, height: 48, fontWeight: 700 }}>
                                {(managedUser.nom?.[0] || managedUser.prenom?.[0] || 'U').toUpperCase()}
                              </Avatar>
                              <Box>
                                <Typography variant="subtitle1" fontWeight={800}>
                                  {managedUser.nom || '-'} {managedUser.prenom || ''}
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                  {managedUser.email || '-'}
                                </Typography>
                              </Box>
                            </Stack>

                            <Stack direction="row" spacing={1} alignItems="center">
                              <Chip
                                label={managedUser.is_active ? 'Actif' : 'Inactif'}
                                color={managedUser.is_active ? 'success' : 'error'}
                                size="small"
                              />
                            </Stack>

                            <Stack spacing={0.75}>
                              <Typography variant="caption" color="text.secondary">Téléphone</Typography>
                              <Typography variant="body2">{managedUser.telephone || '-'}</Typography>
                            </Stack>

                            <Stack spacing={0.75}>
                              <Typography variant="caption" color="text.secondary">Rôle</Typography>
                              <Typography variant="body2">{managedUser.role?.label || managedUser.role?.nom || '-'}</Typography>
                            </Stack>

                            <Stack spacing={0.75}>
                              <Typography variant="caption" color="text.secondary">Mot de passe haché</Typography>
                              <Box
                                sx={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: 1,
                                  px: 1.25,
                                  py: 0.9,
                                  borderRadius: 2,
                                  backgroundColor: 'rgba(22, 90, 114, 0.08)',
                                  border: '1px solid rgba(22, 90, 114, 0.18)',
                                }}
                              >
                                <Typography
                                  variant="caption"
                                  component="code"
                                  sx={{
                                    fontFamily: '"JetBrains Mono", "Fira Code", monospace',
                                    wordBreak: 'break-all',
                                    flex: 1,
                                  }}
                                >
                                  {formatHashSnippet(managedUser.password_hash || 'HASH')}
                                </Typography>
                              </Box>
                            </Stack>
                          </Stack>
                        </CardContent>

                        <Box sx={{ p: 2.5, pt: 0 }}>
                          <Stack direction="row" justifyContent="flex-end" alignItems="center" spacing={1}>
                              <Button
                                size="small"
                                variant="outlined"
                                onClick={() => beginEdit(managedUser)}
                                aria-label="Éditer le compte"
                                sx={{ minWidth: 0, px: 1.1 }}
                              >
                                <EditOutlinedIcon fontSize="small" />
                              </Button>
                              <Button
                                size="small"
                                color="error"
                                variant="outlined"
                                onClick={() => handleDeleteUser(managedUser)}
                                aria-label="Révoquer le compte"
                                sx={{ minWidth: 0, px: 1.1 }}
                              >
                                <DeleteOutlineOutlinedIcon fontSize="small" />
                              </Button>
                          </Stack>
                        </Box>
                      </Card>
                    </Grid>
                  )) : (
                    <Grid item xs={12}>
                      <Typography align="center" color="text.secondary">
                        Aucun compte disponible.
                      </Typography>
                    </Grid>
                  )}
                </Grid>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>

        </Grid>
      </Grid>

    </Box>
  );
}

export default Dashboard;