import { createTheme } from '@mui/material/styles';

const NephroTheme = createTheme({
  palette: {
    primary: {
      main: '#165a72',
      light: '#4d8ea6',
      dark: '#0f3f51',
    },
    secondary: {
      main: '#1f2937',
      light: '#4b5563',
    },
    error: {
      main: '#d64545',
      light: '#ffe3e4',
    },
    warning: {
      main: '#d18f47',
      light: '#fff1df',
    },
    success: {
      main: '#1f9d8a',
      light: '#dcf7f2',
    },
    info: {
      main: '#2b6cb0',
      light: '#e8f2ff',
    },
    background: {
      default: '#f3f7fa',
      paper: '#ffffff',
    },
    text: {
      primary: '#18222f',
      secondary: '#5b6877',
    },
  },
  typography: {
    fontFamily: '"Inter", "Segoe UI", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: { fontWeight: 800, color: '#18222f', letterSpacing: '-0.02em' },
    h2: { fontWeight: 700, color: '#18222f', letterSpacing: '-0.015em' },
    h3: { fontWeight: 700, color: '#165a72', letterSpacing: '-0.01em' },
    h4: { fontWeight: 800, color: '#18222f', letterSpacing: '-0.01em' },
    h5: { fontWeight: 700, color: '#18222f' },
    h6: { fontWeight: 700, color: '#18222f' },
    button: { textTransform: 'none', fontWeight: 600 },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          background: 'linear-gradient(180deg, #f3f7fa 0%, #eef4f8 100%)',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 22,
          boxShadow: '0 14px 45px rgba(15, 23, 42, 0.08)',
          border: '1px solid rgba(94, 115, 141, 0.08)',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          padding: '11px 22px',
          boxShadow: 'none',
        },
        containedPrimary: {
          backgroundImage: 'linear-gradient(135deg, #165a72 0%, #1f7a8c 100%)',
        },
      },
    },
    MuiTextField: {
      defaultProps: {
        variant: 'outlined',
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          borderRadius: 14,
          backgroundColor: '#ffffff',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
      },
    },
  },
});

export default NephroTheme;
