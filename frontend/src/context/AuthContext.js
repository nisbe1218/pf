import React, { createContext, useState, useEffect } from 'react';
import api from '../services/api/axios';
import { jwtDecode } from 'jwt-decode';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const normalizeUser = (payload) => ({
    id: payload.id,
    email: payload.email,
    nom: payload.nom,
    prenom: payload.prenom,
    telephone: payload.telephone,
    role: payload.role?.nom || payload.role,
  });

  useEffect(() => {
    const verifyToken = () => {
      const token = localStorage.getItem('access_token');
      if (token) {
        try {
          const decoded = jwtDecode(token);
          // Vérifier l'expiration du token
          if (decoded.exp * 1000 < Date.now()) {
            logout();
          } else {
            setUser(normalizeUser(decoded));
          }
        } catch (error) {
          logout();
        }
      }
      setLoading(false);
    };

    verifyToken();
  }, []);

  const login = async (email, password) => {
    try {
      const response = await api.post('auth/login/', { email, password });
      const { access, refresh } = response.data;
      
      localStorage.setItem('access_token', access);
      localStorage.setItem('refresh_token', refresh);
      
      const decoded = jwtDecode(access);
      setUser(normalizeUser(decoded));
      return true;
    } catch (error) {
      console.error("Login failed", error);
      throw error;
    }
  };

  const refreshProfile = async () => {
    const response = await api.get('auth/profil/');
    setUser(normalizeUser(response.data));
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, refreshProfile }}>
      {children}
    </AuthContext.Provider>
  );
};