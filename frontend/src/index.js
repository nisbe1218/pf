import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { ThemeProvider } from '@mui/material/styles';
import NephroTheme from './theme';
import CssBaseline from '@mui/material/CssBaseline';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <ThemeProvider theme={NephroTheme}>
      {/* CssBaseline va harmoniser le CSS de base du body, reset margin, etc. */}
      <CssBaseline />
      <App />
    </ThemeProvider>
  </React.StrictMode>
);