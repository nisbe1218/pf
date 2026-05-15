import React, { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useLocation, useNavigate } from 'react-router-dom';
import { useContext } from 'react';
import { AuthContext } from '../../context/AuthContext';
import { useLanguage } from '../../context/LanguageContext';

// Palette professionnelle médicale avec touche rose subtile
const COLORS = {
  // Bleu nuit profond - sérieux et confiance (couleur primaire médicale)
  deepNavy: '#0A2B3E',       // Bleu nuit profond
  medicalBlue: '#1A6B8A',    // Bleu médical élégant
  oceanTeal: '#2C8C9E',      // Teal océan pour accents
  
  // Touche rose - plus foncée pour meilleure visibilité au survol
  softRose: '#D47A8E',       // Rose plus soutenu pour les accents
  dustyRose: '#C46B82',      // Rose poussiéreux élégant (plus foncé)
  blushPink: '#F0D3DF',      // Rose très clair pour fonds
  roseGlow: '#D47A8E40',     // Rose pour lueurs/ombrés (plus opaque)
  roseHover: '#C46B8230',    // Rose foncé transparent pour hover
  roseDark: '#B85C72',       // Rose plus foncé pour contrastes
  
  // Bleus clairs et apaisants
  iceBlue: '#D4EAF2',        // Bleu glacier très clair
  softMint: '#E0F2F1',       // Menthe très douce
  paleAqua: '#E8F4F8',       // Aqua pâle
  
  // Neutres professionnels
  white: '#FFFFFF',
  offWhite: '#F5F9FC',
  lightGray: '#EFF3F6',
  mediumGray: '#DCE3E9',
  textDark: '#1A2F3C',
  textMuted: '#6B8A9C',
  borderLight: '#E2ECF0',
  
  // Accents
  sageGreen: '#7E9A8E',      // Vert sauge pour succès
  success: '#4A8B7C',        // Vert médical
  warning: '#E8A29E',        // Alerte douce
};

// Icône Rein / Néphrologie - Version réaliste avec deux reins
const IconKidney = (size = 28) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    xmlns="http://www.w3.org/2000/svg">
    <path d="M7 6C5 6 3.5 8 3.5 11C3.5 14 4.5 16 6 17.5C7 18.5 7.5 20 7.5 21" 
      stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round"/>
    <path d="M7 6C9 6 10.5 8 10.5 11C10.5 14 9.5 16 8 17.5C7 18.5 6.5 20 6.5 21" 
      stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round"/>
    <path d="M17 6C19 6 20.5 8 20.5 11C20.5 14 19.5 16 18 17.5C17 18.5 16.5 20 16.5 21" 
      stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round"/>
    <path d="M17 6C15 6 13.5 8 13.5 11C13.5 14 14.5 16 16 17.5C17 18.5 17.5 20 17.5 21" 
      stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round"/>
    <path d="M10.5 12H13.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
    <path d="M12 10.5V13.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
    <path d="M7 21C7 22 9 22 12 22C15 22 17 22 17 21" 
      stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
    <circle cx="7" cy="12" r="1" stroke="currentColor" strokeWidth="0.8" fill="currentColor" fillOpacity="0.15"/>
    <circle cx="17" cy="12" r="1" stroke="currentColor" strokeWidth="0.8" fill="currentColor" fillOpacity="0.15"/>
  </svg>
);

// Version détaillée pour desktop
const IconKidneyDetailed = (size = 32) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    xmlns="http://www.w3.org/2000/svg">
    <path d="M6.5 5.5C4 5.5 3 8 3 11C3 14.5 4.5 17 6 18.5C7 19.5 7.5 21 7.5 22" 
      stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round"/>
    <path d="M8.5 5.5C11 5.5 12 8 12 11C12 14.5 10.5 17 9 18.5C8 19.5 7.5 21 7.5 22" 
      stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round"/>
    <path d="M17.5 5.5C20 5.5 21 8 21 11C21 14.5 19.5 17 18 18.5C17 19.5 16.5 21 16.5 22" 
      stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round"/>
    <path d="M15.5 5.5C13 5.5 12 8 12 11C12 14.5 13.5 17 15 18.5C16 19.5 16.5 21 16.5 22" 
      stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round"/>
    <path d="M9.5 11.5L14.5 11.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
    <path d="M12 9V14" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
    <path d="M7 8.5L8.5 10" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeOpacity="0.6"/>
    <path d="M17 8.5L15.5 10" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeOpacity="0.6"/>
    <path d="M7.5 22C7.5 23 9.5 23 12 23C14.5 23 16.5 23 16.5 22" 
      stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
    <path d="M9 22.5C9 23.5 10.5 24 12 24C13.5 24 15 23.5 15 22.5" 
      stroke="currentColor" strokeWidth="1.2" fill="none" strokeLinecap="round" fillOpacity="0.1"/>
    <circle cx="5.5" cy="12" r="1.2" stroke="currentColor" strokeWidth="0.8" fill="currentColor" fillOpacity="0.12"/>
    <circle cx="18.5" cy="12" r="1.2" stroke="currentColor" strokeWidth="0.8" fill="currentColor" fillOpacity="0.12"/>
  </svg>
);

// Version simplifiée pour mobile
const IconKidneySimple = (size = 24) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    xmlns="http://www.w3.org/2000/svg">
    <path d="M7 6C5.5 6 4.5 8 4.5 10.5C4.5 13.5 5.5 15.5 6.5 16.5C7.5 17.5 7.5 19 7.5 20" 
      stroke="currentColor" strokeWidth="1.8" fill="none" strokeLinecap="round"/>
    <path d="M9 6C10.5 6 11.5 8 11.5 10.5C11.5 13.5 10.5 15.5 9.5 16.5C8.5 17.5 8.5 19 8.5 20" 
      stroke="currentColor" strokeWidth="1.8" fill="none" strokeLinecap="round"/>
    <path d="M17 6C18.5 6 19.5 8 19.5 10.5C19.5 13.5 18.5 15.5 17.5 16.5C16.5 17.5 16.5 19 16.5 20" 
      stroke="currentColor" strokeWidth="1.8" fill="none" strokeLinecap="round"/>
    <path d="M15 6C13.5 6 12.5 8 12.5 10.5C12.5 13.5 13.5 15.5 14.5 16.5C15.5 17.5 15.5 19 15.5 20" 
      stroke="currentColor" strokeWidth="1.8" fill="none" strokeLinecap="round"/>
    <path d="M11 11H13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    <path d="M12 10V13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    <path d="M8 20C8 21 10 21.5 12 21.5C14 21.5 16 21 16 20" 
      stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
  </svg>
);

// Icônes de navigation
const IconDashboard = (size = 20) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="7" height="7" rx="1.5"/>
    <rect x="14" y="3" width="7" height="7" rx="1.5"/>
    <rect x="3" y="14" width="7" height="7" rx="1.5"/>
    <rect x="14" y="14" width="7" height="7" rx="1.5"/>
  </svg>
);

const IconPatients = (size = 20) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
  </svg>
);

const IconAI = (size = 20) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3"/>
    <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/>
  </svg>
);

const IconMonitor = (size = 20) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 5h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z"/>
    <path d="M8 20h8"/>
    <path d="M12 17v3"/>
    <path d="M7 12h2l1.2-3 2.1 6 1.6-3H17"/>
  </svg>
);

const IconBell = (size = 20) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
    <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
  </svg>
);

const IconLogout = (size = 18) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
    <polyline points="16 17 21 12 16 7"/>
    <line x1="21" y1="12" x2="9" y2="12"/>
  </svg>
);

const IconProfile = (size = 18) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
    <circle cx="12" cy="7" r="4"/>
  </svg>
);

const IconMenu = (size = 22) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
    <line x1="3" y1="6" x2="21" y2="6"/>
    <line x1="3" y1="12" x2="21" y2="12"/>
    <line x1="3" y1="18" x2="21" y2="18"/>
  </svg>
);

const IconClose = (size = 20) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
    <line x1="18" y1="6" x2="6" y2="18"/>
    <line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);

// NavItem avec bouton rond, animations, tooltip et touche rose plus visible
function NavItem({ icon, label, active, onClick, badge }) {
  const [hovered, setHovered] = useState(false);
  const [ripple, setRipple] = useState(false);
  const btnRef = useRef(null);
  const [tipPos, setTipPos] = useState(null);

  useEffect(() => {
    if (hovered && btnRef.current) {
      try {
        const r = btnRef.current.getBoundingClientRect();
        setTipPos(r);
      } catch (e) {
        setTipPos(null);
      }
    } else {
      setTipPos(null);
    }
  }, [hovered]);

  const handleClick = (e) => {
    setRipple(true);
    setTimeout(() => setRipple(false), 400);
    onClick(e);
  };

  // Dégradé actif avec touche rose
  const bgColor = active 
    ? `linear-gradient(135deg, ${COLORS.medicalBlue} 0%, ${COLORS.deepNavy} 100%)`
    : hovered 
      ? COLORS.roseHover  // Rose plus foncé et plus visible
      : 'transparent';
  
  const iconColor = active || hovered ? COLORS.white : COLORS.textMuted;
  
  // Bordure au survol plus visible
  const hoverBorder = hovered && !active ? `2px solid ${COLORS.dustyRose}60` : '2px solid transparent';

  return (
    <div style={{ position: 'relative', margin: '4px 0' }}>
      {/* Animation ripple avec touche rose plus visible */}
      {ripple && (
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          width: 60,
          height: 60,
          marginLeft: -30,
          marginTop: -30,
          borderRadius: '50%',
          background: `radial-gradient(circle, ${COLORS.softRose}80 0%, transparent 70%)`,
          animation: 'ripple 0.4s ease-out',
          pointerEvents: 'none',
          zIndex: 10,
        }} />
      )}
      
      {/* Indicateur actif - point lumineux rose plus soutenu */}
      {active && (
        <div style={{
          position: 'absolute',
          right: -4,
          top: '50%',
          transform: 'translateY(-50%)',
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: COLORS.softRose,
          boxShadow: `0 0 12px ${COLORS.softRose}`,
          animation: 'pulse 2s infinite',
        }} />
      )}

      <button
        ref={btnRef}
        onClick={handleClick}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        title={label}
        style={{
          width: 48,
          height: 48,
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'pointer',
          zIndex: 20,
          background: bgColor,
          border: active ? `2px solid ${COLORS.softRose}` : hoverBorder,
          color: iconColor,
          transition: 'all 0.3s cubic-bezier(0.34, 1.2, 0.64, 1)',
          transform: hovered ? 'scale(1.08)' : 'scale(1)',
          boxShadow: active 
            ? `0 4px 16px ${COLORS.softRose}50, 0 0 0 1px ${COLORS.softRose}30`
            : hovered 
              ? `0 4px 14px ${COLORS.dustyRose}40` 
              : 'none',
        }}
      >
        {badge ? (
          <div style={{ position: 'relative', display: 'flex' }}>
            {icon}
            <div style={{
              position: 'absolute', top: -4, right: -4,
              width: 10, height: 10,
              background: COLORS.warning,
              borderRadius: '50%',
              border: `2px solid ${COLORS.white}`,
              animation: 'pulse 1.5s infinite',
            }} />
          </div>
        ) : icon}
      </button>
      
      {/* Tooltip amélioré en fixed pour éviter d'être coupé */}
      {/* tip position handled in useEffect */}

      {hovered && !active && window.innerWidth > 768 && tipPos && (typeof document !== 'undefined') && createPortal(
        <div style={{
          position: 'fixed',
          left: tipPos.right + 14,
          top: tipPos.top + (tipPos.height / 2) - 20,
          transform: 'translateY(-50%)',
          background: `linear-gradient(135deg, ${COLORS.deepNavy} 0%, ${COLORS.medicalBlue} 100%)`,
          color: COLORS.white,
          padding: '6px 14px',
          borderRadius: 20,
          fontSize: 12,
          fontWeight: 500,
          letterSpacing: '0.3px',
          whiteSpace: 'nowrap',
          zIndex: 99999,
          boxShadow: `0 12px 36px rgba(10,43,62,0.32)`,
          pointerEvents: 'none',
          animation: 'fadeIn 0.12s ease',
        }}>
          {label}
          <div style={{
            position: 'absolute',
            left: -6,
            top: '50%',
            transform: 'translateY(-50%) rotate(45deg)',
            width: 10,
            height: 10,
            background: COLORS.medicalBlue,
            borderRadius: 2,
            borderLeft: `1px solid ${COLORS.softRose}30`,
            borderBottom: `1px solid ${COLORS.softRose}30`,
            zIndex: 99999,
          }} />
        </div>,
        document.body
      )}
    </div>
  );
}

// Popover Notifications - CORRIGÉ pour un meilleur affichage
function NotifPopover({ anchor, onClose, pending, onValidate, onView }) {
  if (!anchor) return null;

  const popoverLeft = anchor.right + 12;
  const popoverTop = anchor.top + (anchor.height / 2) - 24;
  const viewportHeight = typeof window !== 'undefined' ? window.innerHeight : 900;
  const estimatedPopoverHeight = pending ? 360 : 250;
  const safeTop = Math.max(8, Math.min(popoverTop, viewportHeight - estimatedPopoverHeight - 8));

  // Formatage facile du timestamp
  const formatTs = (iso) => {
    try { return new Date(iso).toLocaleString('fr-FR'); } catch { return iso; }
  };

  const content = (
    <>
      <div
        onClick={onClose}
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 2500,
          background: 'rgba(10,43,62,0.10)',
          backdropFilter: 'blur(2px)',
        }}
      />
      <div
        style={{
          position: 'fixed',
          top: safeTop,
          left: popoverLeft,
          width: 340,
          background: 'linear-gradient(180deg, rgba(255,255,255,0.98), rgba(245,249,252,0.96))',
          borderRadius: 15,
          border: `1px solid rgba(26,107,138,0.22)`,
          boxShadow: '0 24px 56px rgba(10,43,62,0.24)',
          zIndex: 2501,
          padding: 0,
          overflow: 'hidden',
          animation: 'fadeIn 0.18s ease, slideDown 0.18s ease',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 14px', background: `linear-gradient(135deg, ${COLORS.deepNavy}, ${COLORS.medicalBlue})` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 36, height: 36, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(255,255,255,0.06)', borderRadius: 10 }}>
              {IconBell(18)}
            </div>
            <div>
              <div style={{ color: COLORS.white, fontWeight: 700, fontSize: 14 }}>Notifications</div>
              <div style={{ color: 'rgba(255,255,255,0.85)', fontSize: 12 }}>{pending ? 'Import en attente' : 'A jour'}</div>
            </div>
          </div>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: COLORS.white, cursor: 'pointer', padding: 6 }} title="Fermer">
            {IconClose(16)}
          </button>
        </div>

        {/* Body */}
        <div style={{ maxHeight: 260, overflowY: 'auto', padding: 14, background: 'linear-gradient(180deg, rgba(245,249,252,0.95), rgba(255,255,255,0.96))' }}>
          {pending ? (
            <div style={{ display: 'grid', gap: 8 }}>
              <div style={{ padding: 12, borderRadius: 10, background: 'linear-gradient(180deg, rgba(232,162,158,0.06), rgba(255,255,255,0.0))', border: `1px solid ${COLORS.warning}40` }}>
                <div style={{ fontWeight: 700, color: COLORS.warning, marginBottom: 6 }}>Import en attente</div>
                <div style={{ fontSize: 13, color: COLORS.textMuted }}>Demandé par <strong>{pending.requestedBy || '—'}</strong></div>
                {pending.timestamp && <div style={{ fontSize: 12, color: COLORS.textMuted }}>{formatTs(pending.timestamp)}</div>}
              </div>

              <div style={{ display: 'flex', gap: 8 }}>
                <button style={{ flex: 1, padding: '10px 12px', borderRadius: 10, border: 'none', background: `linear-gradient(135deg, ${COLORS.medicalBlue}, ${COLORS.deepNavy})`, color: COLORS.white, fontWeight: 700, cursor: 'pointer' }} onClick={() => { onView && onView(); onClose(); }}>Voir</button>
                <button style={{ flex: 1, padding: '10px 12px', borderRadius: 10, border: `1px solid ${COLORS.softRose}40`, background: COLORS.white, color: COLORS.textDark, fontWeight: 700, cursor: 'pointer' }} onClick={() => { onValidate && onValidate(); onClose(); }}>Valider</button>
              </div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '18px 6px' }}>
              <div style={{ width: 56, height: 56, borderRadius: 12, background: COLORS.blushPink, margin: '0 auto 12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <span style={{ fontSize: 20, color: COLORS.softRose }}>✓</span>
              </div>
              <div style={{ fontSize: 13, color: COLORS.textMuted }}>Aucune nouvelle notification</div>
            </div>
          )}
        </div>

        {/* small pointer */}
        <div style={{ position: 'absolute', left: -8, top: 26, width: 16, height: 16, transform: 'rotate(45deg)', background: COLORS.deepNavy, borderRadius: 2 }} />
      </div>
    </>
  );

  return typeof document !== 'undefined' ? createPortal(content, document.body) : content;
}

// AppSidebar principale
function AppSidebar({ onValidateInsertion, onViewImport }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout } = useContext(AuthContext);
  const { t } = useLanguage();
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const isDashboard = useMemo(() => location.pathname.startsWith('/dashboard'), [location.pathname]);
  const isPatients = useMemo(() => location.pathname.startsWith('/patients'), [location.pathname]);
  const isModelAi = useMemo(() => location.pathname.startsWith('/modele-ai'), [location.pathname]);
  const isMonitor = useMemo(() => location.pathname.startsWith('/monitor'), [location.pathname]);

  const [pending, setPending] = useState(null);
  const [notifAnchor, setNotifAnchor] = useState(null);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const update = () => {
      try {
        const raw = localStorage.getItem('patients_insert_validation_status');
        const s = raw ? JSON.parse(raw) : null;
        setPending(s?.status === 'pending' ? s : null);
      } catch {
        setPending(null);
      }
    };
    update();
    window.addEventListener('patientsInsertValidationUpdated', update);
    window.addEventListener('storage', update);
    return () => {
      window.removeEventListener('patientsInsertValidationUpdated', update);
      window.removeEventListener('storage', update);
    };
  }, []);

  const handleNotifClick = useCallback((e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setNotifAnchor(rect);
  }, []);

  const handleNav = useCallback((path) => {
    navigate(path);
    setMobileOpen(false);
  }, [navigate]);

  const navItems = useMemo(() => [
    { icon: IconDashboard(22), label: t('dashboard'), active: isDashboard, path: '/dashboard' },
    { icon: IconPatients(22), label: t('patients'), active: isPatients, path: '/patients' },
    { icon: IconAI(22), label: t('aiAnalysis'), active: isModelAi, path: '/modele-ai' },
    { icon: IconMonitor(22), label: t('monitor'), active: isMonitor, path: '/monitor' },
  ], [isDashboard, isPatients, isModelAi, isMonitor, t]);

  // Sidebar Desktop avec touche rose
  const DesktopSidebar = (
    <nav style={{
      position: 'fixed', left: 0, top: 0,
      height: '100vh', width: 88,
      background: `linear-gradient(180deg, ${COLORS.white} 0%, ${COLORS.blushPink}15 100%)`,
      borderRight: `1px solid ${COLORS.softRose}25`,
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', padding: '28px 0',
      zIndex: 1200,
      boxShadow: `2px 0 20px rgba(10, 43, 62, 0.04), 0 0 20px ${COLORS.softRose}15`,
    }}>
      {/* Logo Rein - bouton rond avec lueur rose */}
      <div
        onClick={() => handleNav('/dashboard')}
        style={{
          width: 56,
          height: 56,
          borderRadius: '50%',
          background: `linear-gradient(135deg, ${COLORS.deepNavy} 0%, ${COLORS.medicalBlue} 65%, ${COLORS.softRose} 100%)`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'pointer',
          marginBottom: 36,
          boxShadow: `0 4px 20px ${COLORS.softRose}50, 0 0 0 2px ${COLORS.softRose}25`,
          transition: 'all 0.3s cubic-bezier(0.34, 1.2, 0.64, 1)',
          animation: 'float 3s ease-in-out infinite',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'scale(1.08)';
          e.currentTarget.style.boxShadow = `0 8px 28px ${COLORS.softRose}70, 0 0 0 3px ${COLORS.softRose}40`;
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'scale(1)';
          e.currentTarget.style.boxShadow = `0 4px 20px ${COLORS.softRose}50, 0 0 0 2px ${COLORS.softRose}25`;
        }}
      >
        <div style={{ color: COLORS.white }}>
          {IconKidneyDetailed(32)}
        </div>
      </div>

      {/* Navigation principale */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, flex: 1 }}>
        {navItems.map(item => (
          <NavItem
            key={item.path}
            icon={item.icon}
            label={item.label}
            active={item.active}
            onClick={() => handleNav(item.path)}
          />
        ))}
      </div>

      {/* Actions en bas */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 'auto' }}>
        <NavItem
          icon={IconBell(20)}
          label={t('notifications')}
          active={false}
          badge={!!pending}
          onClick={handleNotifClick}
        />

        <div style={{
          width: 32,
          height: 1,
          background: `linear-gradient(90deg, transparent, ${COLORS.softRose}, transparent)`,
          margin: '8px auto',
        }} />

        <button
          onClick={() => navigate('/profil')}
          title={t('profile')}
          style={{
            width: 48,
            height: 48,
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            background: 'transparent',
            border: '2px solid transparent',
            color: COLORS.medicalBlue,
            transition: 'all 0.3s cubic-bezier(0.34, 1.2, 0.64, 1)',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = `${COLORS.medicalBlue}25`;
            e.currentTarget.style.transform = 'scale(1.08)';
            e.currentTarget.style.border = `2px solid ${COLORS.medicalBlue}50`;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'transparent';
            e.currentTarget.style.transform = 'scale(1)';
            e.currentTarget.style.border = '2px solid transparent';
          }}
        >
          {IconProfile(18)}
        </button>

        <button
          onClick={() => { logout(); navigate('/login'); }}
          title={t('logout')}
          style={{
            width: 48,
            height: 48,
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            background: 'transparent',
            border: '2px solid transparent',
            color: COLORS.warning,
            transition: 'all 0.3s cubic-bezier(0.34, 1.2, 0.64, 1)',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = `${COLORS.softRose}25`;
            e.currentTarget.style.transform = 'scale(1.08)';
            e.currentTarget.style.border = `2px solid ${COLORS.softRose}50`;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'transparent';
            e.currentTarget.style.transform = 'scale(1)';
            e.currentTarget.style.border = '2px solid transparent';
          }}
        >
          {IconLogout(18)}
        </button>
      </div>
    </nav>
  );

  // Mobile Drawer avec touche rose
  const MobileDrawer = mobileOpen && (
    <>
      <div
        onClick={() => setMobileOpen(false)}
        style={{
          position: 'fixed', inset: 0, background: `${COLORS.deepNavy}50`,
          backdropFilter: 'blur(4px)',
          zIndex: 1299,
          animation: 'fadeIn 0.2s ease',
        }}
      />
      <div style={{
        position: 'fixed', left: 0, top: 0,
        height: '100%', width: 280,
        background: `linear-gradient(135deg, ${COLORS.white} 0%, ${COLORS.blushPink} 100%)`,
        boxShadow: `4px 0 32px ${COLORS.deepNavy}20, -4px 0 0 ${COLORS.softRose}25`,
        zIndex: 1300,
        display: 'flex',
        flexDirection: 'column',
        animation: 'slideIn 0.3s ease',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '20px 20px',
          background: `linear-gradient(135deg, ${COLORS.deepNavy} 0%, ${COLORS.medicalBlue} 70%, ${COLORS.softRose} 100%)`,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }} onClick={() => handleNav('/dashboard')}>
            <div style={{
              width: 44,
              height: 44,
              borderRadius: '50%',
              background: `linear-gradient(135deg, ${COLORS.white}, ${COLORS.blushPink})`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              {IconKidneySimple(24)}
            </div>
            <span style={{
              fontWeight: 700,
              fontSize: 16,
              color: COLORS.white,
              letterSpacing: '-0.2px',
            }}>
              {t('appName')}
            </span>
          </div>
          <button
            onClick={() => setMobileOpen(false)}
            style={{
              width: 36,
              height: 36,
              borderRadius: '50%',
              border: 'none',
              background: `${COLORS.white}20`,
              cursor: 'pointer',
              color: COLORS.white,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s ease',
            }}
            onMouseEnter={e => e.currentTarget.style.background = `${COLORS.softRose}60`}
            onMouseLeave={e => e.currentTarget.style.background = `${COLORS.white}20`}
          >
            {IconClose(18)}
          </button>
        </div>

        <div style={{ padding: '20px 16px', flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
          {navItems.map(item => (
            <button
              key={item.path}
              onClick={() => handleNav(item.path)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 14,
                padding: '12px 18px',
                borderRadius: 40,
                cursor: 'pointer',
                background: item.active ? `linear-gradient(135deg, ${COLORS.deepNavy}, ${COLORS.medicalBlue} 70%, ${COLORS.softRose})` : 'transparent',
                border: item.active ? `1px solid ${COLORS.softRose}50` : '1px solid transparent',
                color: item.active ? COLORS.white : COLORS.textMuted,
                fontWeight: item.active ? 600 : 500,
                fontSize: 14,
                width: '100%',
                textAlign: 'left',
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={(e) => {
                if (!item.active) {
                  e.currentTarget.style.background = `${COLORS.softRose}20`;
                  e.currentTarget.style.border = `1px solid ${COLORS.softRose}30`;
                }
              }}
              onMouseLeave={(e) => {
                if (!item.active) {
                  e.currentTarget.style.background = 'transparent';
                  e.currentTarget.style.border = '1px solid transparent';
                }
              }}
            >
              <div style={{ color: item.active ? COLORS.white : COLORS.textMuted }}>
                {item.icon}
              </div>
              <span>{item.label}</span>
            </button>
          ))}
        </div>

        <div style={{ padding: '16px', borderTop: `1px solid ${COLORS.softRose}30` }}>
          <button
            onClick={() => { navigate('/profil'); setMobileOpen(false); }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 14,
              padding: '12px 18px',
              borderRadius: 40,
              cursor: 'pointer',
              color: COLORS.medicalBlue,
              fontSize: 14,
              fontWeight: 500,
              border: 'none',
              background: 'transparent',
              width: '100%',
              transition: 'all 0.2s ease',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = `${COLORS.medicalBlue}20`;
              e.currentTarget.style.border = `1px solid ${COLORS.medicalBlue}30`;
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.border = 'none';
            }}
          >
            {IconProfile(18)}
            <span>{t('profile')}</span>
          </button>

          <button
            onClick={() => { logout(); navigate('/login'); }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 14,
              padding: '12px 18px',
              borderRadius: 40,
              cursor: 'pointer',
              color: COLORS.warning,
              fontSize: 14,
              fontWeight: 500,
              border: 'none',
              background: 'transparent',
              width: '100%',
              transition: 'all 0.2s ease',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = `${COLORS.softRose}20`;
              e.currentTarget.style.border = `1px solid ${COLORS.softRose}30`;
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.border = 'none';
            }}
          >
            {IconLogout(18)}
            <span>{t('logout')}</span>
          </button>
        </div>
      </div>
    </>
  );

  // Styles d'animations globaux
  const animationStyles = `
    @keyframes ripple {
      0% { transform: scale(0); opacity: 0.6; }
      100% { transform: scale(2); opacity: 0; }
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.5; transform: scale(1.2); }
    }
    @keyframes float {
      0%, 100% { transform: translateY(0); }
      50% { transform: translateY(-3px); }
    }
    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }
    @keyframes slideDown {
      from { opacity: 0; transform: translateY(-10px); }
      to { opacity: 1; transform: translateY(0); }
    }
    @keyframes slideIn {
      from { transform: translateX(-100%); }
      to { transform: translateX(0); }
    }
  `;

  return (
    <>
      <style>{animationStyles}</style>
      <div style={{ display: isMobile ? 'none' : 'block' }}>
        {DesktopSidebar}
      </div>

      {isMobile && (
        <button
          onClick={() => setMobileOpen(true)}
          style={{
            position: 'fixed', top: 16, left: 16, zIndex: 1100,
            width: 48, height: 48, borderRadius: '50%',
            background: `linear-gradient(135deg, ${COLORS.deepNavy}, ${COLORS.medicalBlue} 70%, ${COLORS.softRose})`,
            border: `1px solid ${COLORS.softRose}50`,
            boxShadow: `0 4px 16px ${COLORS.softRose}40`,
            cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: COLORS.white,
            transition: 'all 0.3s ease',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.transform = 'scale(1.05)';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.transform = 'scale(1)';
          }}
        >
          {IconMenu(22)}
        </button>
      )}

      {MobileDrawer}

      <NotifPopover
        anchor={notifAnchor}
        onClose={() => setNotifAnchor(null)}
        pending={pending}
        onValidate={onValidateInsertion}
        onView={onViewImport}
      />
    </>
  );
}

export default AppSidebar;