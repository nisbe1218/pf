import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Box } from '@mui/material';
import Dashboard from './pages/dashboard/Dashboard';
import Landing from './pages/auth/Landing';
import Login from './pages/auth/Login';
import Unauthorized from './pages/unauthorized/Unauthorized';
import PatientsManagement from './pages/patients/PatientsManagement';
import ModelAI from './pages/model-ai/ModelAI';
import ProtectedRoute from './components/common/ProtectedRoute';
import { AuthProvider } from './context/AuthContext';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Box
          sx={{ width: '100%', minHeight: '100vh', pt: 0, pb: 4, px: 0, mx: 0, minWidth: 0, overflowX: 'hidden' }}
        >
          <Routes>
            {/* Page d’accueil publique */}
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/unauthorized" element={<Unauthorized />} />

            {/* Routes Protégées (Tous les rôles connectés) */}
            <Route element={<ProtectedRoute />}>
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/modele-ai" element={<ModelAI />} />
            </Route>

            <Route element={<ProtectedRoute allowedRoles={['super_admin', 'chef_service']} />}>
              <Route path="/patients" element={<PatientsManagement />} />
            </Route>

            {/* Les autres rôles viendront ici (ex: routes admin, route patients) */}

            {/* Redirection par défaut */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Box>
      </Router>
    </AuthProvider>
  );
}

export default App;