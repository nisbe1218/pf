import React, { useContext, useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  InputAdornment,
  LinearProgress,
  Slider,
  Paper,
  MenuItem,
  Stack,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import AddCircleOutlineOutlinedIcon from '@mui/icons-material/AddCircleOutlineOutlined';
import DeleteOutlineOutlinedIcon from '@mui/icons-material/DeleteOutlineOutlined';
import EditOutlinedIcon from '@mui/icons-material/EditOutlined';
import SearchOutlinedIcon from '@mui/icons-material/SearchOutlined';
import UploadFileOutlinedIcon from '@mui/icons-material/UploadFileOutlined';
import ClearOutlinedIcon from '@mui/icons-material/ClearOutlined';
import FileDownloadOutlinedIcon from '@mui/icons-material/FileDownloadOutlined';
import DataObjectOutlinedIcon from '@mui/icons-material/DataObjectOutlined';
import PsychologyAltOutlinedIcon from '@mui/icons-material/PsychologyAltOutlined';
import ArrowBackOutlinedIcon from '@mui/icons-material/ArrowBackOutlined';
import { useLocation, useNavigate } from 'react-router-dom';
import { Bar, Bubble, Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Tooltip,
  Legend,
} from 'chart.js';
import api from '../../services/api/axios';
import { AuthContext } from '../../context/AuthContext';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Tooltip, Legend);

const emptyForm = {
  id: null,
  nom: '',
  prenom: '',
  age: '',
  sexe: '',
  maladie: '',
  date_naissance: '',
};

const emptyFilters = {
  search: '',
  id_patient: '',
  sexe: '',
  age_min: '',
  age_max: '',
  date_naissance: '',
  statut_inclusion: '',
  infection: '',
  hemorrhage: '',
  avf_created: '',
};

const sexLabels = {
  M: 'Homme',
  F: 'Femme',
  O: 'Inconnu',
};

const normalizeSexDisplay = (rawValue) => {
  if (rawValue === null || rawValue === undefined || rawValue === '') {
    return rawValue;
  }

  const normalized = String(rawValue).trim().toLowerCase();
  if (['1', 'm', 'male', 'masculin', 'homme', 'man'].includes(normalized)) {
    return 'Homme';
  }
  if (['0', 'f', 'female', 'feminin', 'femme', 'woman'].includes(normalized)) {
    return 'Femme';
  }
  if (['i', 'intersex', 'intersexe'].includes(normalized)) {
    return 'Intersexe';
  }
  if (['9', 'o', 'other', 'autre', 'unknown', 'inconnu', 'na', 'n/a', 'none', 'null'].includes(normalized)) {
    return 'Inconnu';
  }

  return rawValue;
};

const BOOLEAN_TRUE_VALUES = ['1', 'true', 'yes', 'oui', 'y'];
const BOOLEAN_FALSE_VALUES = ['0', 'false', 'no', 'non', 'n'];

const toBooleanDisplay = (rawValue) => {
  if (rawValue === null || rawValue === undefined || rawValue === '') {
    return rawValue;
  }

  const normalized = String(rawValue).trim().toLowerCase();
  if (BOOLEAN_TRUE_VALUES.includes(normalized)) {
    return 'Oui';
  }
  if (BOOLEAN_FALSE_VALUES.includes(normalized)) {
    return 'Non';
  }

  return rawValue;
};

const isNoResponseValue = (value) => {
  if (value === null || value === undefined || value === '') {
    return true;
  }

  const normalized = String(value).trim().toLowerCase();
  return normalized === '' || normalized === 'x' || normalized === '-';
};

const isPositiveClinicalValue = (value) => {
  if (isNoResponseValue(value)) {
    return false;
  }

  const normalized = String(value).trim().toLowerCase();
  if (BOOLEAN_FALSE_VALUES.includes(normalized)) {
    return false;
  }
  if (['absent', 'negative', 'negatif', 'no'].includes(normalized)) {
    return false;
  }
  return true;
};


const toMonthKey = (rawDate) => {
  const parsed = new Date(String(rawDate || ''));
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }
  const year = parsed.getFullYear();
  const month = String(parsed.getMonth() + 1).padStart(2, '0');
  return `${year}-${month}`;
};

const monthKeyToLabel = (monthKey) => {
  const [year, month] = String(monthKey).split('-');
  return `${month}/${year}`;
};

const PATIENT_FIELD_MAP = {
  nom: 'nom',
  prenom: 'prenom',
  age: 'age',
  sexe: 'sexe',
  maladie: 'maladie',
  telephone: 'telephone',
  adresse: 'adresse',
  date_naissance: 'date_naissance',
  date_admission: 'date_admission',
  id_patient: 'id_patient',
  id_enregistrement_source: 'id_enregistrement_source',
  id_site: 'id_site',
  statut_inclusion: 'statut_inclusion',
  statut_consentement: 'statut_consentement',
  date_evaluation_initiale: 'date_evaluation_initiale',
  utilisateur_saisie: 'utilisateur_saisie',
  derniere_mise_a_jour: 'derniere_mise_a_jour',
};

const FIXED_BASE_COLUMNS = [
  { key: 'id_patient', label: 'id_patient' },
  { key: 'nom', label: 'nom' },
  { key: 'prenom', label: 'prenom' },
  { key: 'age', label: 'age' },
];

const SECTION_FIELD_MAP = {
  demographie_: 'demographie_data',
  irc_: 'irc_data',
  comorbidite_: 'comorbidite_data',
  presentation_: 'presentation_data',
  biologie_: 'biologie_data',
  imagerie_: 'imagerie_data',
  dialyse_: 'dialyse_data',
  qualite_: 'qualite_data',
  complication_: 'complication_data',
  traitement_: 'traitement_data',
  devenir_: 'devenir_data',
};

const SIMILAR_SCHEMA_FALLBACK_MAP = {
  demographie_sexe: 'sexe',
  demographie_date_naissance: 'date_naissance',
  irc_etiologie_principale: 'maladie',
};

const EXTRA_DATA_FALLBACK_KEYS = {
  demographie_sexe: ['sex', 'gender', 'sexe'],
  demographie_date_naissance: ['date_of_birth', 'birth_date', 'naissance'],
  irc_etiologie_principale: ['ckd_etiology', 'diagnostic'],
  id_patient: ['patient_id'],
  age: ['age_years'],
};

const EXPLICIT_BIRTH_DATE_KEYS = [
  'date_of_birth',
  'birth_date',
  'dob',
  'birthdate',
  'date_birth',
  'naissance',
  'demographie_date_naissance',
  'date_naissance',
];

const safeStringify = (value) => {
  if (value === null || value === undefined || value === '') {
    return '';
  }

  if (typeof value === 'string') {
    return value;
  }

  return JSON.stringify(value);
};

const escapeCsvCell = (value) => {
  return String(value)
    .replaceAll('"', '""');
};

const extractApiMessage = (requestError, fallbackMessage) => {
  const status = requestError?.response?.status;
  const data = requestError?.response?.data;

  if (typeof data === 'string') {
    if (status === 404) {
      return 'Endpoint patients introuvable. Redémarrez le backend Django.';
    }
    if (status === 401 || status === 403) {
      return 'Accès refusé à l’API patients pour ce compte.';
    }
    return fallbackMessage;
  }

  const message = data?.error
    || data?.detail
    || (data ? Object.values(data)[0] : null);

  return message || fallbackMessage;
};

const shouldDisplayBirthYearOnly = (patient, rawValue) => {
  if (!rawValue || !patient) {
    return false;
  }

  const date = new Date(String(rawValue));
  if (Number.isNaN(date.getTime())) {
    return false;
  }

  const age = Number(patient?.age);
  if (!Number.isFinite(age) || age < 0) {
    return false;
  }

  const hasExplicitBirthDate = EXPLICIT_BIRTH_DATE_KEYS.some((key) => {
    const value = patient?.extra_data?.[key];
    return value !== undefined && value !== null && String(value).trim() !== '';
  });
  if (hasExplicitBirthDate) {
    return false;
  }

  const today = new Date();
  const expectedYear = today.getFullYear() - Math.trunc(age);
  const sameMonthDay = date.getMonth() === today.getMonth() && date.getDate() === today.getDate();
  return sameMonthDay && date.getFullYear() === expectedYear;
};

const formatBirthDateDisplay = (patient, schemaKey, rawValue) => {
  if (!['date_naissance', 'demographie_date_naissance'].includes(schemaKey)) {
    return rawValue;
  }

  if (!rawValue) {
    return rawValue;
  }

  if (shouldDisplayBirthYearOnly(patient, rawValue)) {
    return String(rawValue).slice(0, 4);
  }

  return rawValue;
};

function PatientsManagement() {
  const INITIAL_DYNAMIC_COLUMNS_LIMIT = 20;
  const INITIAL_ROWS_LIMIT = 100;
  const { user } = useContext(AuthContext);
  const navigate = useNavigate();
  const location = useLocation();
  const fileInputRef = useRef(null);
  const [patients, setPatients] = useState([]);
  const [schemaTemplate, setSchemaTemplate] = useState(null);
  const [schemaAnswers, setSchemaAnswers] = useState({});
  const [form, setForm] = useState(emptyForm);
  const [filters, setFilters] = useState(emptyFilters);
  const [extraDataValues, setExtraDataValues] = useState({});
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [showAllDynamicColumns, setShowAllDynamicColumns] = useState(false);
  const [showAllRows, setShowAllRows] = useState(false);
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [selectedPatientIds, setSelectedPatientIds] = useState([]);
  const [deletingSelection, setDeletingSelection] = useState(false);
  const [mainSection, setMainSection] = useState('data_patient');
  const [activeTab, setActiveTab] = useState('gestion');
  const [analysisView, setAnalysisView] = useState('synthese');
  const [profile3dAngle, setProfile3dAngle] = useState(35);

  useEffect(() => {
    if (location.pathname.startsWith('/modele-ai')) {
      setMainSection('modele_ai');
      return;
    }
    setMainSection('data_patient');
  }, [location.pathname]);

  useEffect(() => {
    const validIdSet = new Set(patients.map((patient) => patient.id));
    setSelectedPatientIds((current) => current.filter((id) => validIdSet.has(id)));
  }, [patients]);

  const schemaFieldKeySet = useMemo(() => {
    return new Set((schemaTemplate?.fields || []).map((field) => field.key));
  }, [schemaTemplate]);

  const extraColumns = useMemo(() => {
    const keys = new Set();
    patients.forEach((patient) => {
      Object.keys(patient.extra_data || {}).forEach((key) => keys.add(key));
    });
    return Array.from(keys).filter((key) => !schemaFieldKeySet.has(key));
  }, [patients, schemaFieldKeySet]);

  const visibleExtraColumns = useMemo(() => {
    if (showAllDynamicColumns) {
      return extraColumns;
    }
    return extraColumns.slice(0, INITIAL_DYNAMIC_COLUMNS_LIMIT);
  }, [extraColumns, showAllDynamicColumns]);

  const formDynamicExtraColumns = useMemo(() => {
    const keys = new Set(extraColumns);
    Object.keys(extraDataValues || {}).forEach((key) => {
      if (!schemaFieldKeySet.has(key)) {
        keys.add(key);
      }
    });
    return Array.from(keys).sort((a, b) => a.localeCompare(b));
  }, [extraColumns, extraDataValues, schemaFieldKeySet]);

  const visiblePatients = useMemo(() => {
    if (showAllRows) {
      return patients;
    }
    return patients.slice(0, INITIAL_ROWS_LIMIT);
  }, [patients, showAllRows]);

  const selectedVisibleCount = useMemo(() => {
    const visibleIdSet = new Set(visiblePatients.map((patient) => patient.id));
    return selectedPatientIds.filter((id) => visibleIdSet.has(id)).length;
  }, [selectedPatientIds, visiblePatients]);

  const allVisibleSelected = visiblePatients.length > 0 && selectedVisibleCount === visiblePatients.length;

  const selectedPatientsCountLabel = selectedPatientIds.length > 1
    ? `${selectedPatientIds.length} lignes selectionnees`
    : selectedPatientIds.length === 1
      ? '1 ligne selectionnee'
      : 'Aucune ligne selectionnee';

  const tableSchemaFields = useMemo(() => {
    const fields = schemaTemplate?.fields || [];
    return [...fields].sort((a, b) => (a.order || 0) - (b.order || 0));
  }, [schemaTemplate]);

  const fixedBaseColumns = useMemo(() => {
    return FIXED_BASE_COLUMNS;
  }, []);

  const tableDisplaySchemaFields = useMemo(() => {
    const fixedKeys = new Set(FIXED_BASE_COLUMNS.map((column) => column.key));
    return tableSchemaFields.filter((field) => !fixedKeys.has(field.key));
  }, [tableSchemaFields]);

  const getSectionFieldBySchemaKey = (schemaKey) => {
    const sectionPrefix = Object.keys(SECTION_FIELD_MAP).find((prefix) => schemaKey.startsWith(prefix));
    if (!sectionPrefix) {
      return null;
    }
    return SECTION_FIELD_MAP[sectionPrefix];
  };

  const schemaBooleanFieldKeys = useMemo(() => {
    const keys = new Set();
    tableSchemaFields.forEach((field) => {
      const choices = (field.choices || []).map((choice) => String(choice).trim().toLowerCase());
      const hasOuiNonChoices = choices.length > 0 && choices.every((choice) => ['oui', 'non'].includes(choice));
      if (field.field_type === 'boolean' || hasOuiNonChoices) {
        keys.add(field.key);
      }
    });
    return keys;
  }, [tableSchemaFields]);

  const extraBinaryColumnKeys = useMemo(() => {
    const keys = new Set();
    extraColumns.forEach((columnKey) => {
      let hasValue = false;
      let isBinaryOnly = true;

      for (const patient of patients) {
        const raw = patient?.extra_data?.[columnKey];
        if (raw === null || raw === undefined || raw === '') {
          continue;
        }
        hasValue = true;

        const normalized = String(raw).trim().toLowerCase();
        if (!BOOLEAN_TRUE_VALUES.includes(normalized) && !BOOLEAN_FALSE_VALUES.includes(normalized)) {
          isBinaryOnly = false;
          break;
        }
      }

      if (hasValue && isBinaryOnly) {
        keys.add(columnKey);
      }
    });
    return keys;
  }, [extraColumns, patients]);

  const formatSchemaValue = (schemaKey, value) => {
    if (schemaBooleanFieldKeys.has(schemaKey)) {
      return toBooleanDisplay(value);
    }
    return value;
  };

  const formatExtraValue = (columnKey, value) => {
    if (extraBinaryColumnKeys.has(columnKey)) {
      return toBooleanDisplay(value);
    }
    return value;
  };

  const resolveTableCellValue = (patient, schemaKey) => {
    const mappedField = PATIENT_FIELD_MAP[schemaKey];
    if (mappedField) {
      const raw = patient?.[mappedField];
      if (schemaKey === 'sexe' || schemaKey === 'demographie_sexe') {
        return normalizeSexDisplay(sexLabels[raw] || raw);
      }
      return formatBirthDateDisplay(patient, schemaKey, formatSchemaValue(schemaKey, raw));
    }

    const sectionPrefix = Object.keys(SECTION_FIELD_MAP).find((prefix) => schemaKey.startsWith(prefix));
    if (sectionPrefix) {
      const sectionField = SECTION_FIELD_MAP[sectionPrefix];
      const valueFromSection = patient?.[sectionField]?.[schemaKey];
      if (valueFromSection !== undefined && valueFromSection !== null && valueFromSection !== '') {
        if (schemaKey === 'demographie_sexe') {
          return normalizeSexDisplay(valueFromSection);
        }
        return formatBirthDateDisplay(patient, schemaKey, formatSchemaValue(schemaKey, valueFromSection));
      }
    }

    const fallbackField = SIMILAR_SCHEMA_FALLBACK_MAP[schemaKey];
    if (fallbackField) {
      const fallbackRaw = patient?.[fallbackField];
      if (fallbackRaw !== undefined && fallbackRaw !== null && fallbackRaw !== '') {
        if (fallbackField === 'sexe' || schemaKey === 'demographie_sexe') {
          return normalizeSexDisplay(sexLabels[fallbackRaw] || fallbackRaw);
        }
        return formatBirthDateDisplay(patient, schemaKey, formatSchemaValue(schemaKey, fallbackRaw));
      }
    }

    const extraFallbackKeys = EXTRA_DATA_FALLBACK_KEYS[schemaKey] || [];
    for (const candidateKey of extraFallbackKeys) {
      const candidateValue = patient?.extra_data?.[candidateKey];
      if (candidateValue !== undefined && candidateValue !== null && candidateValue !== '') {
        if (schemaKey === 'demographie_sexe' || schemaKey === 'sexe') {
          return normalizeSexDisplay(candidateValue);
        }
        return formatBirthDateDisplay(patient, schemaKey, formatSchemaValue(schemaKey, candidateValue));
      }
    }

    const raw = patient?.extra_data?.[schemaKey] ?? patient?.extra_data?.[schemaKey.replaceAll('_', ' ')] ?? null;
    return formatBirthDateDisplay(patient, schemaKey, formatSchemaValue(schemaKey, raw));
  };

  const analysisSummary = useMemo(() => {
    const totalPatients = patients.length;
    const ageValues = patients
      .map((patient) => Number(patient?.age))
      .filter((age) => Number.isFinite(age) && age >= 0);

    const averageAge = ageValues.length
      ? (ageValues.reduce((acc, age) => acc + age, 0) / ageValues.length).toFixed(1)
      : '-';

    const sexCountsMap = { Homme: 0, Femme: 0, Inconnu: 0 };
    patients.forEach((patient) => {
      const normalizedSex = normalizeSexDisplay(sexLabels[patient?.sexe] || patient?.sexe || 'Inconnu');
      if (normalizedSex === 'Homme') {
        sexCountsMap.Homme += 1;
      } else if (normalizedSex === 'Femme') {
        sexCountsMap.Femme += 1;
      } else {
        sexCountsMap.Inconnu += 1;
      }
    });

    const inclusionMap = {};
    patients.forEach((patient) => {
      const raw = resolveTableCellValue(patient, 'statut_inclusion');
      if (isNoResponseValue(raw)) {
        return;
      }
      const key = String(raw).trim();
      inclusionMap[key] = (inclusionMap[key] || 0) + 1;
    });

    const ageBandsMap = {
      '0-20': 0,
      '21-40': 0,
      '41-60': 0,
      '61-80': 0,
      '81+': 0,
    };

    ageValues.forEach((age) => {
      if (age <= 20) {
        ageBandsMap['0-20'] += 1;
      } else if (age <= 40) {
        ageBandsMap['21-40'] += 1;
      } else if (age <= 60) {
        ageBandsMap['41-60'] += 1;
      } else if (age <= 80) {
        ageBandsMap['61-80'] += 1;
      } else {
        ageBandsMap['81+'] += 1;
      }
    });

    const etiologyMap = {};
    patients.forEach((patient) => {
      const etiologyValue = resolveTableCellValue(patient, 'irc_etiologie_principale');
      if (isNoResponseValue(etiologyValue)) {
        return;
      }
      const key = String(etiologyValue).trim();
      etiologyMap[key] = (etiologyMap[key] || 0) + 1;
    });

    const monthlyInclusionMap = {};
    const monthlyComplicationMap = {};
    const etiologyInclusionMap = {};

    patients.forEach((patient) => {
      const monthKey = [
        patient?.date_evaluation_initiale,
        patient?.date_admission,
        patient?.derniere_mise_a_jour,
        patient?.date_naissance,
      ]
        .map((candidateDate) => toMonthKey(candidateDate))
        .find(Boolean);

      const inclusionValueRaw = resolveTableCellValue(patient, 'statut_inclusion');
      const inclusionLabel = isNoResponseValue(inclusionValueRaw) ? 'Non renseigne' : String(inclusionValueRaw).trim();

      const etiologyRaw = resolveTableCellValue(patient, 'irc_etiologie_principale');
      const etiologyLabel = isNoResponseValue(etiologyRaw) ? 'Non renseignee' : String(etiologyRaw).trim();

      if (!etiologyInclusionMap[etiologyLabel]) {
        etiologyInclusionMap[etiologyLabel] = {};
      }
      etiologyInclusionMap[etiologyLabel][inclusionLabel] = (etiologyInclusionMap[etiologyLabel][inclusionLabel] || 0) + 1;

      if (monthKey) {
        if (!isNoResponseValue(inclusionValueRaw)) {
          monthlyInclusionMap[monthKey] = (monthlyInclusionMap[monthKey] || 0) + 1;
        }

        if (!monthlyComplicationMap[monthKey]) {
          monthlyComplicationMap[monthKey] = {
            infection: 0,
            hemorrhage: 0,
            avf_created: 0,
          };
        }

        ['infection', 'hemorrhage', 'avf_created'].forEach((key) => {
          const value = resolveTableCellValue(patient, key);
          if (isPositiveClinicalValue(value)) {
            monthlyComplicationMap[monthKey][key] += 1;
          }
        });
      }
    });

    const comorbidityFieldMap = new Map();

    tableDisplaySchemaFields
      .filter((field) => field.key.startsWith('comorbidite_'))
      .forEach((field) => {
        comorbidityFieldMap.set(field.key, {
          key: field.key,
          label: field.label,
          getValue: (patient) => resolveTableCellValue(patient, field.key),
        });
      });

    patients.forEach((patient) => {
      Object.keys(patient?.comorbidite_data || {}).forEach((key) => {
        if (!comorbidityFieldMap.has(key)) {
          comorbidityFieldMap.set(key, {
            key,
            label: key,
            getValue: (p) => p?.comorbidite_data?.[key],
          });
        }
      });

      Object.keys(patient?.extra_data || {}).forEach((key) => {
        const normalized = String(key).toLowerCase();
        if ((normalized.startsWith('comorbidite_') || normalized.includes('comorbid')) && !comorbidityFieldMap.has(key)) {
          comorbidityFieldMap.set(key, {
            key,
            label: key,
            getValue: (p) => p?.extra_data?.[key],
          });
        }
      });
    });

    const comorbidityFields = Array.from(comorbidityFieldMap.values());
    const comorbidityMap = {};
    const comorbidityCombinationMap = {};
    const profile3dPoints = [];

    comorbidityFields.forEach((field) => {
      let count = 0;

      patients.forEach((patient) => {
        const rawValue = field.getValue(patient);
        if (isNoResponseValue(rawValue)) {
          return;
        }

        const normalized = String(rawValue).trim().toLowerCase();
        const isExplicitFalse = BOOLEAN_FALSE_VALUES.includes(normalized) || ['absent', 'negative', 'negatif'].includes(normalized);
        if (!isExplicitFalse) {
          count += 1;
        }
      });

      if (count > 0) {
        comorbidityMap[field.label] = count;
      }
    });

    patients.forEach((patient) => {
      const positives = comorbidityFields
        .filter((field) => isPositiveClinicalValue(field.getValue(patient)))
        .map((field) => field.label)
        .sort();

      const age = Number(patient?.age);
      if (Number.isFinite(age) && age >= 0) {
        const complicationCount = ['infection', 'hemorrhage', 'avf_created']
          .reduce((acc, key) => acc + (isPositiveClinicalValue(resolveTableCellValue(patient, key)) ? 1 : 0), 0);
        const sex = normalizeSexDisplay(sexLabels[patient?.sexe] || patient?.sexe || 'Inconnu');
        const inclusion = resolveTableCellValue(patient, 'statut_inclusion');

        profile3dPoints.push({
          age,
          comorbidityCount: positives.length,
          complicationCount,
          sex,
          inclusion: isNoResponseValue(inclusion) ? 'Non renseigne' : String(inclusion),
        });
      }

      if (positives.length < 2) {
        return;
      }

      const combinationLabel = positives.slice(0, 3).join(' + ');
      comorbidityCombinationMap[combinationLabel] = (comorbidityCombinationMap[combinationLabel] || 0) + 1;
    });

    const qualityColumns = [
      ...fixedBaseColumns.map((column) => ({ key: column.key, label: column.label, isExtra: false })),
      ...tableDisplaySchemaFields.map((field) => ({ key: field.key, label: field.label, isExtra: false })),
      ...visibleExtraColumns.map((columnKey) => ({ key: columnKey, label: columnKey, isExtra: true })),
    ];

    const fillRates = qualityColumns.map((column) => {
      const filled = patients.reduce((acc, patient) => {
        const rawValue = column.isExtra
          ? patient?.extra_data?.[column.key]
          : resolveTableCellValue(patient, column.key);
        return acc + (isNoResponseValue(rawValue) ? 0 : 1);
      }, 0);
      const rate = totalPatients ? Math.round((filled / totalPatients) * 100) : 0;
      return {
        label: column.label,
        filled,
        rate,
      };
    }).sort((a, b) => a.rate - b.rate);

    const averageCompleteness = fillRates.length
      ? Math.round(fillRates.reduce((acc, item) => acc + item.rate, 0) / fillRates.length)
      : 0;

    const monthlyInclusions = Object.entries(monthlyInclusionMap)
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([monthKey, count]) => ({ label: monthKeyToLabel(monthKey), count }));

    const monthlyComplications = Object.entries(monthlyComplicationMap)
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([monthKey, values]) => ({
        label: monthKeyToLabel(monthKey),
        infection: values.infection,
        hemorrhage: values.hemorrhage,
        avf_created: values.avf_created,
      }));

    const topEtiologyLabels = Object.entries(etiologyMap)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([label]) => label);

    const inclusionStatuses = Array.from(new Set(Object.values(etiologyInclusionMap)
      .flatMap((statusMap) => Object.keys(statusMap)))).slice(0, 5);

    const etiologyInclusionGrouped = {
      labels: topEtiologyLabels,
      datasets: inclusionStatuses.map((status) => ({
        status,
        values: topEtiologyLabels.map((etiology) => etiologyInclusionMap?.[etiology]?.[status] || 0),
      })),
    };

    const ageSexDistribution = Object.keys(ageBandsMap).map((band) => ({
      band,
      homme: 0,
      femme: 0,
      inconnu: 0,
    }));

    patients.forEach((patient) => {
      const age = Number(patient?.age);
      if (!Number.isFinite(age) || age < 0) {
        return;
      }

      const sex = normalizeSexDisplay(sexLabels[patient?.sexe] || patient?.sexe || 'Inconnu');
      const targetBand = age <= 20
        ? '0-20'
        : age <= 40
          ? '21-40'
          : age <= 60
            ? '41-60'
            : age <= 80
              ? '61-80'
              : '81+';

      const target = ageSexDistribution.find((item) => item.band === targetBand);
      if (!target) {
        return;
      }

      if (sex === 'Homme') {
        target.homme += 1;
      } else if (sex === 'Femme') {
        target.femme += 1;
      } else {
        target.inconnu += 1;
      }
    });

    return {
      totalPatients,
      averageAge,
      inclusionCount: Object.values(inclusionMap).reduce((acc, count) => acc + count, 0),
      averageCompleteness,
      sexCounts: Object.entries(sexCountsMap).map(([label, count]) => ({ label, count })),
      inclusionCounts: Object.entries(inclusionMap)
        .map(([label, count]) => ({ label, count }))
        .sort((a, b) => b.count - a.count),
      ageBands: Object.entries(ageBandsMap).map(([label, count]) => ({ label, count })),
      topEtiologies: Object.entries(etiologyMap)
        .map(([label, count]) => ({ label, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 6),
      topComorbidities: Object.entries(comorbidityMap)
        .map(([label, count]) => ({ label, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 8),
      monthlyInclusions,
      monthlyComplications,
      etiologyInclusionGrouped,
      ageSexDistribution,
      topComorbidityCombinations: Object.entries(comorbidityCombinationMap)
        .map(([label, count]) => ({ label, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 8),
      profile3dPoints: profile3dPoints.slice(0, 1200),
      weakestColumns: fillRates.slice(0, 10),
    };
  }, [fixedBaseColumns, patients, tableDisplaySchemaFields, visibleExtraColumns]); // eslint-disable-line react-hooks/exhaustive-deps

  const monthlyInclusionChartData = useMemo(() => ({
    labels: analysisSummary.monthlyInclusions.map((item) => item.label),
    datasets: [
      {
        label: 'Patients inclus',
        data: analysisSummary.monthlyInclusions.map((item) => item.count),
        borderColor: 'rgba(31, 122, 140, 1)',
        backgroundColor: 'rgba(31, 122, 140, 0.25)',
        tension: 0.25,
        fill: true,
      },
    ],
  }), [analysisSummary.monthlyInclusions]);

  const monthlyComplicationsChartData = useMemo(() => ({
    labels: analysisSummary.monthlyComplications.map((item) => item.label),
    datasets: [
      {
        label: 'Infection',
        data: analysisSummary.monthlyComplications.map((item) => item.infection),
        backgroundColor: 'rgba(231, 76, 60, 0.75)',
      },
      {
        label: 'Hemorrhage',
        data: analysisSummary.monthlyComplications.map((item) => item.hemorrhage),
        backgroundColor: 'rgba(241, 196, 15, 0.75)',
      },
      {
        label: 'AVF',
        data: analysisSummary.monthlyComplications.map((item) => item.avf_created),
        backgroundColor: 'rgba(52, 152, 219, 0.75)',
      },
    ],
  }), [analysisSummary.monthlyComplications]);

  const etiologyInclusionChartData = useMemo(() => ({
    labels: analysisSummary.etiologyInclusionGrouped.labels,
    datasets: analysisSummary.etiologyInclusionGrouped.datasets.map((dataset, index) => ({
      label: dataset.status,
      data: dataset.values,
      backgroundColor: [
        'rgba(31, 122, 140, 0.72)',
        'rgba(241, 196, 15, 0.72)',
        'rgba(231, 76, 60, 0.72)',
        'rgba(46, 204, 113, 0.72)',
        'rgba(155, 89, 182, 0.72)',
      ][index % 5],
    })),
  }), [analysisSummary.etiologyInclusionGrouped]);

  const ageSexHistogramData = useMemo(() => ({
    labels: analysisSummary.ageSexDistribution.map((item) => item.band),
    datasets: [
      {
        label: 'Homme',
        data: analysisSummary.ageSexDistribution.map((item) => item.homme),
        backgroundColor: 'rgba(52, 152, 219, 0.72)',
      },
      {
        label: 'Femme',
        data: analysisSummary.ageSexDistribution.map((item) => item.femme),
        backgroundColor: 'rgba(231, 76, 60, 0.72)',
      },
      {
        label: 'Inconnu',
        data: analysisSummary.ageSexDistribution.map((item) => item.inconnu),
        backgroundColor: 'rgba(127, 140, 141, 0.72)',
      },
    ],
  }), [analysisSummary.ageSexDistribution]);

  const comorbidityCombinationChartData = useMemo(() => ({
    labels: analysisSummary.topComorbidityCombinations.map((item) => item.label),
    datasets: [
      {
        label: 'Patients',
        data: analysisSummary.topComorbidityCombinations.map((item) => item.count),
        backgroundColor: 'rgba(142, 68, 173, 0.72)',
      },
    ],
  }), [analysisSummary.topComorbidityCombinations]);

  const defaultChartOptions = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          precision: 0,
        },
      },
    },
  }), []);

  const profileProjectedBubbleData = useMemo(() => {
    const points = analysisSummary.profile3dPoints || [];
    const colorBySex = {
      Homme: 'rgba(31, 119, 180, 0.75)',
      Femme: 'rgba(231, 76, 60, 0.75)',
      Inconnu: 'rgba(127, 140, 141, 0.75)',
    };

    if (!points.length) {
      return { datasets: [] };
    }

    const angleRad = (profile3dAngle * Math.PI) / 180;
    const ages = points.map((p) => p.age);
    const comorbs = points.map((p) => p.comorbidityCount);
    const meanAge = ages.reduce((acc, n) => acc + n, 0) / ages.length;
    const meanComorb = comorbs.reduce((acc, n) => acc + n, 0) / comorbs.length;

    const projected = points.map((p) => {
      const x = p.age - meanAge;
      const y = p.comorbidityCount - meanComorb;
      const z = p.complicationCount;

      const depth = (x * Math.sin(angleRad)) + (z * Math.cos(angleRad));
      const u = (x * Math.cos(angleRad)) - (z * Math.sin(angleRad));
      const v = y + (depth * 0.35);

      return {
        u,
        v,
        r: Math.max(4, 4 + (p.complicationCount * 2)),
        sex: p.sex,
      };
    });

    const minU = Math.min(...projected.map((p) => p.u));
    const minV = Math.min(...projected.map((p) => p.v));

    return {
      datasets: [
        {
          label: 'Patients (taille = complications, couleur = sexe)',
          data: projected.map((p) => ({
            x: p.u - minU + 1,
            y: p.v - minV + 1,
            r: p.r,
          })),
          backgroundColor: projected.map((p) => colorBySex[p.sex] || colorBySex.Inconnu),
        },
      ],
    };
  }, [analysisSummary.profile3dPoints, profile3dAngle]);

  const profileBubbleOptions = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: {
        title: {
          display: true,
          text: 'Age',
        },
        beginAtZero: true,
      },
      y: {
        title: {
          display: true,
          text: 'Nombre de comorbidites',
        },
        beginAtZero: true,
        ticks: {
          precision: 0,
        },
      },
    },
    plugins: {
      tooltip: {
        callbacks: {
          label: (context) => {
            const point = analysisSummary.profile3dPoints[context.dataIndex];
            if (!point) {
              return '';
            }
            return `Age: ${point.age}, Comorbidites: ${point.comorbidityCount}, Complications: ${point.complicationCount}, Sexe: ${point.sex}, Inclusion: ${point.inclusion}`;
          },
        },
      },
      legend: {
        display: false,
      },
    },
  }), [analysisSummary.profile3dPoints]);

  const analysisKpis = useMemo(() => {
    const total = analysisSummary.totalPatients || 0;
    const inclusionRate = total ? Math.round((analysisSummary.inclusionCount / total) * 100) : 0;

    const complicationsTotal = analysisSummary.monthlyComplications.reduce((acc, month) => {
      return acc + month.infection + month.hemorrhage + month.avf_created;
    }, 0);

    const topEtiology = analysisSummary.topEtiologies[0]?.label || '-';

    return {
      inclusionRate,
      complicationsTotal,
      topEtiology,
    };
  }, [analysisSummary]);

  const loadPatients = async (activeFilters = filters) => {
    setLoading(true);
    setError('');
    try {
      const response = await api.get('patients/', {
        params: {
          search: activeFilters.search || undefined,
          id_patient: activeFilters.id_patient || undefined,
          sexe: activeFilters.sexe || undefined,
          age_min: activeFilters.age_min || undefined,
          age_max: activeFilters.age_max || undefined,
          date_naissance: activeFilters.date_naissance || undefined,
          statut_inclusion: activeFilters.statut_inclusion || undefined,
          infection: activeFilters.infection || undefined,
          hemorrhage: activeFilters.hemorrhage || undefined,
          avf_created: activeFilters.avf_created || undefined,
        },
      });
      setPatients(response.data);
    } catch (requestError) {
      setError(extractApiMessage(requestError, 'Impossible de charger les données patients.'));
    } finally {
      setLoading(false);
    }
  };
  const loadSchema = async () => {
    try {
      const response = await api.get('patients/schema/');
      setSchemaTemplate(response.data?.template || null);
    } catch (requestError) {
      setSchemaTemplate(null);
    }
  };

  useEffect(() => {
    loadPatients();
    loadSchema();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const resetForm = () => {
    setForm(emptyForm);
    setExtraDataValues({});
    setIsEditDialogOpen(false);
    setSchemaAnswers({});
  };

  const beginEdit = (patient) => {
    setForm({
      id: patient.id,
      nom: patient.nom || '',
      prenom: patient.prenom || '',
      age: patient.age ?? '',
      sexe: patient.sexe || '',
      maladie: patient.maladie || '',
      date_naissance: patient.date_naissance || '',
    });
    setExtraDataValues(patient.extra_data && typeof patient.extra_data === 'object' ? patient.extra_data : {});
    setIsEditDialogOpen(true);

    const loadedAnswers = {};
    (schemaTemplate?.fields || []).forEach((field) => {
      if (PATIENT_FIELD_MAP[field.key]) {
        loadedAnswers[field.key] = patient[PATIENT_FIELD_MAP[field.key]] ?? '';
      } else {
        const sectionField = getSectionFieldBySchemaKey(field.key);
        if (sectionField) {
          loadedAnswers[field.key] = patient?.[sectionField]?.[field.key] ?? '';
        } else {
          loadedAnswers[field.key] = patient?.extra_data?.[field.key] ?? '';
        }
      }
    });
    setSchemaAnswers(loadedAnswers);

    setError('');
    setSuccess('');
  };

  const togglePatientSelection = (patientId) => {
    setSelectedPatientIds((current) => {
      if (current.includes(patientId)) {
        return current.filter((id) => id !== patientId);
      }
      return [...current, patientId];
    });
  };

  const toggleSelectAllVisible = (checked) => {
    const visibleIds = visiblePatients.map((patient) => patient.id);

    if (checked) {
      setSelectedPatientIds((current) => Array.from(new Set([...current, ...visibleIds])));
      return;
    }

    const visibleSet = new Set(visibleIds);
    setSelectedPatientIds((current) => current.filter((id) => !visibleSet.has(id)));
  };

  const handleEditSelected = () => {
    if (selectedPatientIds.length !== 1) {
      return;
    }

    const selectedPatient = patients.find((patient) => patient.id === selectedPatientIds[0]);
    if (!selectedPatient) {
      setError('La ligne selectionnee est introuvable. Rechargez la liste.');
      return;
    }

    beginEdit(selectedPatient);
  };

  useEffect(() => {
    if (!schemaTemplate?.fields?.length) {
      return;
    }

    setSchemaAnswers((current) => {
      const next = { ...current };
      schemaTemplate.fields.forEach((field) => {
        if (next[field.key] !== undefined) {
          return;
        }

        if (field.field_type === 'multiple_choice') {
          next[field.key] = [];
        } else if (field.field_type === 'auto') {
          next[field.key] = '';
        } else {
          next[field.key] = '';
        }
      });
      return next;
    });
  }, [schemaTemplate, form.id]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((current) => ({
      ...current,
      [name]: value,
    }));
  };

  const handleFilterChange = (event) => {
    const { name, value } = event.target;
    setFilters((current) => ({
      ...current,
      [name]: value,
    }));
  };

  const handleSchemaAnswerChange = (field, value) => {
    setSchemaAnswers((current) => ({
      ...current,
      [field.key]: value,
    }));
  };

  const handleExtraDataFieldChange = (columnKey, value) => {
    setExtraDataValues((current) => ({
      ...current,
      [columnKey]: value,
    }));
  };

  const handleSearch = async (event) => {
    event.preventDefault();
    await loadPatients(filters);
  };

  const handleSave = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');

    const parsedExtraData = Object.entries(extraDataValues || {}).reduce((acc, [key, value]) => {
      if (value !== undefined && value !== null) {
        acc[key] = value;
      }
      return acc;
    }, {});

    const payload = {
      nom: form.nom,
      prenom: form.prenom,
      age: form.age === '' ? null : Number(form.age),
      sexe: form.sexe,
      maladie: form.maladie,
      date_naissance: form.date_naissance || null,
      extra_data: parsedExtraData,
    };

    (schemaTemplate?.fields || []).forEach((field) => {
      const currentValue = schemaAnswers[field.key];
      let value = currentValue;

      if (field.field_type === 'multiple_choice') {
        value = Array.isArray(value) ? value : [];
      }

      if (PATIENT_FIELD_MAP[field.key]) {
        const modelField = PATIENT_FIELD_MAP[field.key];
        if (value !== '' && value !== null && value !== undefined) {
          payload[modelField] = value;
        }
      } else {
        const sectionField = getSectionFieldBySchemaKey(field.key);
        if (sectionField) {
          if (value !== '' && value !== null && value !== undefined && !(Array.isArray(value) && !value.length)) {
            if (!payload[sectionField] || typeof payload[sectionField] !== 'object') {
              payload[sectionField] = {};
            }
            payload[sectionField][field.key] = value;
          }
        } else if (value !== '' && value !== null && value !== undefined && !(Array.isArray(value) && !value.length)) {
          payload.extra_data[field.key] = value;
        }
      }
    });

    try {
      if (form.id) {
        await api.put(`patients/${form.id}/`, payload);
        setSuccess('Patient modifié avec succès.');
      } else {
        await api.post('patients/', payload);
        setSuccess('Patient ajouté avec succès.');
      }
      await loadPatients();
      resetForm();
    } catch (requestError) {
      setError(extractApiMessage(requestError, 'Impossible d’enregistrer le patient.'));
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteSelected = async () => {
    if (!selectedPatientIds.length) {
      return;
    }

    const selectedPatients = patients.filter((patient) => selectedPatientIds.includes(patient.id));
    const confirmed = window.confirm(
      selectedPatientIds.length === 1
        ? `Supprimer le patient ${selectedPatients[0]?.prenom || ''} ${selectedPatients[0]?.nom || ''} ?`
        : `Supprimer ${selectedPatientIds.length} patients selectionnes ?`,
    );
    if (!confirmed) {
      return;
    }

    setDeletingSelection(true);
    setError('');
    setSuccess('');
    try {
      const idsToDelete = [...selectedPatientIds];
      const deletionResults = await Promise.allSettled(
        idsToDelete.map((id) => api.delete(`patients/${id}/`)),
      );

      const deletedIds = idsToDelete.filter((_, index) => deletionResults[index].status === 'fulfilled');
      const failedCount = deletionResults.length - deletedIds.length;

      if (deletedIds.length) {
        const deletedIdSet = new Set(deletedIds);
        setPatients((currentPatients) => currentPatients.filter((item) => !deletedIdSet.has(item.id)));
        setSelectedPatientIds((current) => current.filter((id) => !deletedIdSet.has(id)));
      }

      if (deletedIds.length && failedCount === 0) {
        setSuccess(
          deletedIds.length === 1
            ? 'Patient supprime avec succes.'
            : `${deletedIds.length} patients supprimes avec succes.`,
        );
      } else if (deletedIds.length) {
        setSuccess(`${deletedIds.length} patients supprimes. ${failedCount} suppression(s) ont echoue.`);
      } else {
        setError('Aucune suppression n a pu etre effectuee.');
      }

      if (form.id && deletedIds.includes(form.id)) {
        resetForm();
      }
    } catch (requestError) {
      setError(extractApiMessage(requestError, 'Suppression impossible.'));
    } finally {
      setDeletingSelection(false);
    }
  };

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleExportExcel = () => {
    setError('');
    try {
      const headerRow = [
        ...fixedBaseColumns.map((column) => column.label),
        ...tableDisplaySchemaFields.map((field) => field.label),
        ...visibleExtraColumns,
      ];

      const rows = visiblePatients.map((patient) => [
        ...fixedBaseColumns.map((column) => renderValue(resolveTableCellValue(patient, column.key))),
        ...tableDisplaySchemaFields.map((field) => renderValue(resolveTableCellValue(patient, field.key))),
        ...visibleExtraColumns.map((columnKey) => renderValue(formatExtraValue(columnKey, patient?.extra_data?.[columnKey]))),
      ]);

      const csvContent = [headerRow, ...rows]
        .map((row) => row.map((cell) => `"${escapeCsvCell(cell)}"`).join(';'))
        .join('\n');

      const bom = '\uFEFF';
      const blob = new Blob([bom, csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `patients_tableau_${new Date().toISOString().slice(0, 19).replaceAll(':', '-')}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      setSuccess('Fichier Excel téléchargé avec succès.');
    } catch (requestError) {
      setError(extractApiMessage(requestError, 'Téléchargement Excel impossible.'));
    }
  };

  const handleFileSelect = async (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    setImporting(true);
    setError('');
    setSuccess('');

    try {
      const formData = new FormData();
      formData.append('file', file);
      const response = await api.post('patients/import/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const importedFields = response.data?.fields_created || 0;
      const patientsCreated = response.data?.patients_created || 0;
      const mode = response.data?.mode;

      if (mode === 'schema') {
        setSuccess(`${importedFields} colonne(s) de structure importée(s) depuis Excel.`);
      } else {
        setSuccess(`${patientsCreated} patient(s) importé(s) et ${importedFields} colonne(s) gérée(s).`);
      }

      if ((response.data?.errors || []).length) {
        setError(`Import partiel: ${response.data.errors.length} ligne(s) rejetée(s).`);
      }

      await loadSchema();
      await loadPatients();
    } catch (requestError) {
      setError(extractApiMessage(requestError, 'Import de la structure Excel impossible.'));
    } finally {
      setImporting(false);
      event.target.value = '';
    }
  };

  const renderValue = (value) => {
    if (value === null || value === undefined || value === '') {
      return '-';
    }

    if (typeof value === 'string') {
      const normalized = value.trim().toLowerCase();
      if (normalized === 'x' || normalized === '-') {
        return '-';
      }
    }

    if (typeof value === 'object') {
      return safeStringify(value);
    }

    return value;
  };

  const closeEditDialog = () => {
    resetForm();
  };

  const renderDynamicExtraFields = (title) => {
    if (!formDynamicExtraColumns.length) {
      return null;
    }

    return (
      <Box
        sx={{
          p: 1.5,
          borderRadius: 2,
          border: '1px solid rgba(94, 115, 141, 0.18)',
          backgroundColor: 'rgba(255,255,255,0.8)',
          maxHeight: 280,
          overflowY: 'auto',
          display: 'grid',
          gap: 1.25,
        }}
      >
        <Typography variant="subtitle2" fontWeight={800}>
          {title}
        </Typography>
        {formDynamicExtraColumns.map((columnKey) => (
          <TextField
            key={`dynamic-form-${columnKey}`}
            label={columnKey}
            value={extraDataValues[columnKey] ?? ''}
            onChange={(event) => handleExtraDataFieldChange(columnKey, event.target.value)}
            size="small"
            fullWidth
          />
        ))}
      </Box>
    );
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        py: 2,
        background: 'radial-gradient(circle at top left, rgba(77, 142, 166, 0.12), transparent 24%), linear-gradient(180deg, #f2f7fb 0%, #edf3f8 100%)',
      }}
    >
      <Grid container spacing={2} alignItems="flex-start">
        <Grid item xs={12} md={3} lg={2}>
          <Card
            elevation={0}
            sx={{
              borderRadius: 5,
              border: '1px solid rgba(15, 63, 81, 0.14)',
              background: 'linear-gradient(165deg, rgba(255,255,255,0.98) 0%, rgba(232,244,250,0.94) 100%)',
              boxShadow: '0 18px 42px rgba(15, 63, 81, 0.10)',
              overflow: 'hidden',
              position: { md: 'sticky' },
              top: { md: 16 },
            }}
          >
            <Box
              sx={{
                p: 2,
                background: 'linear-gradient(120deg, #0f3f51 0%, #1a6b84 100%)',
                color: 'white',
              }}
            >
              <Typography variant="caption" sx={{ opacity: 0.85, letterSpacing: 1.1 }}>
                CONTROL CENTER
              </Typography>
              <Typography variant="subtitle1" fontWeight={900}>
                Navigation intelligente
              </Typography>
            </Box>

            <CardContent sx={{ p: 2 }}>
              <Stack spacing={1.25}>
                <Button
                  fullWidth
                  variant="text"
                  startIcon={<ArrowBackOutlinedIcon />}
                  onClick={() => navigate('/dashboard')}
                  aria-label="Retourner au tableau de bord"
                  sx={{
                    justifyContent: 'center',
                    textTransform: 'none',
                    fontWeight: 700,
                    borderRadius: 2.5,
                    py: 0.85,
                    px: 1.5,
                    color: '#0f3f51',
                    minWidth: 0,
                    '& .MuiButton-startIcon': {
                      margin: 0,
                    },
                    '&:hover': {
                      backgroundColor: 'rgba(15,63,81,0.08)',
                    },
                  }}
                />
                <Button
                  fullWidth
                  variant={mainSection === 'data_patient' ? 'contained' : 'outlined'}
                  startIcon={<DataObjectOutlinedIcon />}
                  onClick={() => navigate('/patients')}
                  sx={{
                    justifyContent: 'flex-start',
                    textTransform: 'none',
                    fontWeight: 800,
                    borderRadius: 2.5,
                    py: 1,
                    px: 1.5,
                    borderColor: 'rgba(15, 63, 81, 0.22)',
                    color: mainSection === 'data_patient' ? 'white' : '#0f3f51',
                    background: mainSection === 'data_patient' ? 'linear-gradient(115deg, #0f3f51 0%, #1f7a8c 100%)' : 'rgba(255,255,255,0.8)',
                    boxShadow: mainSection === 'data_patient' ? '0 10px 26px rgba(15, 63, 81, 0.25)' : 'none',
                    transition: 'transform 160ms ease, box-shadow 160ms ease, background-color 160ms ease',
                    '&:hover': {
                      transform: 'translateY(-1px)',
                      boxShadow: '0 12px 24px rgba(15, 63, 81, 0.18)',
                      background: mainSection === 'data_patient' ? 'linear-gradient(115deg, #0f3f51 0%, #1f7a8c 100%)' : 'rgba(15,63,81,0.06)',
                    },
                  }}
                >
                  Data patient
                </Button>
                <Button
                  fullWidth
                  variant={mainSection === 'modele_ai' ? 'contained' : 'outlined'}
                  startIcon={<PsychologyAltOutlinedIcon />}
                  onClick={() => navigate('/modele-ai')}
                  sx={{
                    justifyContent: 'flex-start',
                    textTransform: 'none',
                    fontWeight: 800,
                    borderRadius: 2.5,
                    py: 1,
                    px: 1.5,
                    borderColor: 'rgba(15, 63, 81, 0.22)',
                    color: mainSection === 'modele_ai' ? 'white' : '#0f3f51',
                    background: mainSection === 'modele_ai' ? 'linear-gradient(115deg, #114b5f 0%, #16867a 100%)' : 'rgba(255,255,255,0.8)',
                    boxShadow: mainSection === 'modele_ai' ? '0 10px 26px rgba(17, 75, 95, 0.25)' : 'none',
                    transition: 'transform 160ms ease, box-shadow 160ms ease, background-color 160ms ease',
                    '&:hover': {
                      transform: 'translateY(-1px)',
                      boxShadow: '0 12px 24px rgba(17, 75, 95, 0.18)',
                      background: mainSection === 'modele_ai' ? 'linear-gradient(115deg, #114b5f 0%, #16867a 100%)' : 'rgba(17,75,95,0.08)',
                    },
                  }}
                >
                  Modele AI
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={9} lg={10}>
      <Stack spacing={3}>
        {mainSection === 'data_patient' ? (
          <>
        <Card elevation={0} sx={{ borderRadius: 4, border: '1px solid rgba(94, 115, 141, 0.12)' }}>
          <CardContent sx={{ p: 3 }}>
            <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={2}>
              <Box>
                <Typography variant="h5" fontWeight={900}>
                  Gestion des données patients
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  Saisie manuelle, import Excel, filtrage et validation pour le chef de service.
                </Typography>
              </Box>
              <Chip
                label={user?.role === 'chef_service' ? 'Chef de Service' : 'Administrateur'}
                color="primary"
                sx={{ alignSelf: 'flex-start' }}
              />
            </Stack>
            <Tabs
              value={activeTab}
              onChange={(_, newValue) => setActiveTab(newValue)}
              sx={{ mt: 2 }}
            >
              <Tab value="gestion" label="Gestion des donnees" />
              <Tab value="analyse" label="Analyse" />
            </Tabs>
          </CardContent>
        </Card>

        {error && <Alert severity="error">{error}</Alert>}
        {success && <Alert severity="success">{success}</Alert>}

        {activeTab === 'gestion' ? (
        <Grid container spacing={3}>
          <Grid item xs={12} lg={4}>
            <Card elevation={0} sx={{ borderRadius: 4, border: '1px solid rgba(94, 115, 141, 0.12)' }}>
              <CardContent sx={{ p: 3 }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                  <Typography variant="h6" fontWeight={800}>
                    {form.id ? 'Modifier un patient' : 'Ajouter un patient'}
                  </Typography>
                  {form.id && (
                    <Button size="small" variant="text" onClick={resetForm} startIcon={<ClearOutlinedIcon />}>
                      Annuler
                    </Button>
                  )}
                </Stack>

                <Box component="form" onSubmit={handleSave} sx={{ display: 'grid', gap: 2 }}>
                  <TextField label="Nom" name="nom" value={form.nom} onChange={handleChange} required fullWidth size="small" />
                  <TextField label="Prénom" name="prenom" value={form.prenom} onChange={handleChange} required fullWidth size="small" />
                  <TextField label="Âge" name="age" type="number" value={form.age} onChange={handleChange} fullWidth size="small" />
                  <TextField select label="Sexe" name="sexe" value={form.sexe} onChange={handleChange} fullWidth size="small">
                    <MenuItem value="">Sélectionner</MenuItem>
                    <MenuItem value="M">Homme</MenuItem>
                    <MenuItem value="F">Femme</MenuItem>
                    <MenuItem value="O">Autre</MenuItem>
                  </TextField>
                  <TextField label="Maladie" name="maladie" value={form.maladie} onChange={handleChange} fullWidth size="small" />
                  <TextField
                    label="Date de naissance"
                    name="date_naissance"
                    type="date"
                    value={form.date_naissance}
                    onChange={handleChange}
                    fullWidth
                    size="small"
                    InputLabelProps={{ shrink: true }}
                  />
                  {schemaTemplate?.fields?.length ? (
                    <Box
                      sx={{
                        p: 1.5,
                        borderRadius: 2,
                        border: '1px solid rgba(94, 115, 141, 0.18)',
                        backgroundColor: 'rgba(255,255,255,0.8)',
                        maxHeight: 320,
                        overflowY: 'auto',
                        display: 'grid',
                        gap: 1.25,
                      }}
                    >
                      <Typography variant="subtitle2" fontWeight={800}>
                        Reponses du modele interne
                      </Typography>
                      {tableSchemaFields.map((field) => {
                        const value = schemaAnswers[field.key];

                        if (field.field_type === 'auto') {
                          return (
                            <TextField
                              key={field.id}
                              label={field.label}
                              value={value || '(genere automatiquement)'}
                              size="small"
                              fullWidth
                              disabled
                            />
                          );
                        }

                        if (field.field_type === 'single_choice' || field.field_type === 'boolean') {
                          return (
                            <TextField
                              key={field.id}
                              select
                              label={field.label}
                              value={value || ''}
                              onChange={(event) => handleSchemaAnswerChange(field, event.target.value)}
                              size="small"
                              fullWidth
                            >
                              <MenuItem value="">Selectionner</MenuItem>
                              {(field.choices || []).map((choice) => (
                                <MenuItem key={`${field.id}-${choice}`} value={choice}>{choice}</MenuItem>
                              ))}
                            </TextField>
                          );
                        }

                        if (field.field_type === 'multiple_choice') {
                          return (
                            <TextField
                              key={field.id}
                              select
                              label={field.label}
                              value={Array.isArray(value) ? value : []}
                              onChange={(event) => handleSchemaAnswerChange(field, event.target.value)}
                              size="small"
                              fullWidth
                              SelectProps={{
                                multiple: true,
                                renderValue: (selected) => selected.join(', '),
                              }}
                            >
                              {(field.choices || []).map((choice) => (
                                <MenuItem key={`${field.id}-${choice}`} value={choice}>{choice}</MenuItem>
                              ))}
                            </TextField>
                          );
                        }

                        if (field.field_type === 'date') {
                          return (
                            <TextField
                              key={field.id}
                              label={field.label}
                              type="date"
                              value={value || ''}
                              onChange={(event) => handleSchemaAnswerChange(field, event.target.value)}
                              size="small"
                              fullWidth
                              InputLabelProps={{ shrink: true }}
                            />
                          );
                        }

                        if (field.field_type === 'integer') {
                          return (
                            <TextField
                              key={field.id}
                              label={field.label}
                              type="number"
                              value={value || ''}
                              onChange={(event) => handleSchemaAnswerChange(field, event.target.value)}
                              size="small"
                              fullWidth
                            />
                          );
                        }

                        return (
                          <TextField
                            key={field.id}
                            label={field.label}
                            value={value || ''}
                            onChange={(event) => handleSchemaAnswerChange(field, event.target.value)}
                            size="small"
                            fullWidth
                            multiline={field.field_type === 'text_long'}
                            minRows={field.field_type === 'text_long' ? 2 : undefined}
                          />
                        );
                      })}
                    </Box>
                  ) : null}

                  {renderDynamicExtraFields('Colonnes dynamiques detectees (modifiables)')}

                  <Stack direction="row" spacing={1.5}>
                    <Button type="submit" variant="contained" disabled={saving} startIcon={<AddCircleOutlineOutlinedIcon />} fullWidth>
                      {form.id ? 'Modifier' : 'Créer'}
                    </Button>
                    <Button type="button" variant="outlined" onClick={resetForm} fullWidth>
                      Réinitialiser
                    </Button>
                  </Stack>
                  <Button type="button" variant="outlined" startIcon={<FileDownloadOutlinedIcon />} onClick={handleExportExcel} fullWidth>
                    Télécharger les données (Excel)
                  </Button>
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} lg={8}>
            <Stack spacing={3}>
              <Card elevation={0} sx={{ borderRadius: 4, border: '1px solid rgba(94, 115, 141, 0.12)' }}>
                <CardContent sx={{ p: 3 }}>
                  <Box component="form" onSubmit={handleSearch}>
                    <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5}>
                      <TextField
                        label="Recherche rapide"
                        name="search"
                        value={filters.search}
                        onChange={handleFilterChange}
                        fullWidth
                        size="small"
                        InputProps={{
                          startAdornment: (
                            <InputAdornment position="start">
                              <SearchOutlinedIcon fontSize="small" />
                            </InputAdornment>
                          ),
                        }}
                      />
                      <TextField label="ID patient" name="id_patient" value={filters.id_patient} onChange={handleFilterChange} size="small" sx={{ minWidth: 180 }} />
                      <Button type="button" variant="contained" onClick={() => setShowAdvancedFilters((current) => !current)}>
                        {showAdvancedFilters ? 'Masquer filtres' : 'Filtrer'}
                      </Button>
                    </Stack>

                    {showAdvancedFilters && (
                      <Box sx={{ mt: 2, p: 2, borderRadius: 2, border: '1px solid rgba(94, 115, 141, 0.18)', backgroundColor: 'rgba(255,255,255,0.85)' }}>
                        <Typography variant="subtitle2" fontWeight={800} sx={{ mb: 1.5 }}>
                          Filtres disponibles
                        </Typography>
                        <Grid container spacing={1.5}>
                          <Grid item xs={12} sm={6} md={3}>
                            <TextField select label="Sexe" name="sexe" value={filters.sexe} onChange={handleFilterChange} size="small" fullWidth>
                              <MenuItem value="">Tous</MenuItem>
                              <MenuItem value="M">Homme</MenuItem>
                              <MenuItem value="F">Femme</MenuItem>
                              <MenuItem value="O">Inconnu/Autre</MenuItem>
                            </TextField>
                          </Grid>
                          <Grid item xs={12} sm={6} md={3}>
                            <TextField label="Âge min" name="age_min" type="number" value={filters.age_min} onChange={handleFilterChange} size="small" fullWidth />
                          </Grid>
                          <Grid item xs={12} sm={6} md={3}>
                            <TextField label="Âge max" name="age_max" type="number" value={filters.age_max} onChange={handleFilterChange} size="small" fullWidth />
                          </Grid>
                          <Grid item xs={12} sm={6} md={3}>
                            <TextField label="Statut inclusion" name="statut_inclusion" value={filters.statut_inclusion} onChange={handleFilterChange} size="small" fullWidth />
                          </Grid>
                          <Grid item xs={12} sm={6} md={3}>
                            <TextField
                              label="Date de naissance"
                              name="date_naissance"
                              type="date"
                              value={filters.date_naissance}
                              onChange={handleFilterChange}
                              size="small"
                              InputLabelProps={{ shrink: true }}
                              fullWidth
                            />
                          </Grid>
                          <Grid item xs={12} sm={6} md={2}>
                            <TextField select label="Infection" name="infection" value={filters.infection} onChange={handleFilterChange} size="small" fullWidth>
                              <MenuItem value="">Tous</MenuItem>
                              <MenuItem value="oui">Oui</MenuItem>
                              <MenuItem value="non">Non</MenuItem>
                            </TextField>
                          </Grid>
                          <Grid item xs={12} sm={6} md={2}>
                            <TextField select label="Hemorrhage" name="hemorrhage" value={filters.hemorrhage} onChange={handleFilterChange} size="small" fullWidth>
                              <MenuItem value="">Tous</MenuItem>
                              <MenuItem value="oui">Oui</MenuItem>
                              <MenuItem value="non">Non</MenuItem>
                            </TextField>
                          </Grid>
                          <Grid item xs={12} sm={6} md={2}>
                            <TextField select label="AVF created" name="avf_created" value={filters.avf_created} onChange={handleFilterChange} size="small" fullWidth>
                              <MenuItem value="">Tous</MenuItem>
                              <MenuItem value="oui">Oui</MenuItem>
                              <MenuItem value="non">Non</MenuItem>
                            </TextField>
                          </Grid>
                        </Grid>

                        <Stack direction="row" spacing={1.5} justifyContent="flex-end" sx={{ mt: 1.5 }}>
                          <Button type="submit" variant="contained">Appliquer</Button>
                          <Button
                            type="button"
                            variant="outlined"
                            onClick={() => {
                              setFilters(emptyFilters);
                              loadPatients(emptyFilters);
                            }}
                          >
                            Effacer
                          </Button>
                        </Stack>
                      </Box>
                    )}
                  </Box>

                </CardContent>
              </Card>

              <Card elevation={0} sx={{ borderRadius: 4, border: '1px solid rgba(94, 115, 141, 0.12)' }}>
                <CardContent sx={{ p: 3 }}>
                  <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={2} sx={{ mb: 2 }}>
                    <Box>
                      <Typography variant="h6" fontWeight={800}>
                        Liste des patients
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Colonnes Classeur1 fixes + nouvelles colonnes detectees automatiquement lors des imports machine.
                      </Typography>
                    </Box>
                    <Box
                      sx={{
                        p: 1.25,
                        borderRadius: 2.5,
                        border: '1px solid rgba(94, 115, 141, 0.18)',
                        backgroundColor: 'rgba(255,255,255,0.8)',
                        minWidth: { md: 420 },
                      }}
                    >
                      <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" alignItems="center" sx={{ mb: 1 }}>
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={handleImportClick}
                          startIcon={<UploadFileOutlinedIcon />}
                          disabled={importing}
                          sx={{ textTransform: 'none', borderRadius: 2, fontWeight: 700, whiteSpace: 'nowrap' }}
                        >
                          {importing ? 'Import...' : 'Importer Excel'}
                        </Button>
                        <input
                          ref={fileInputRef}
                          type="file"
                          accept=".xlsx,.xls"
                          hidden
                          onChange={handleFileSelect}
                        />
                      </Stack>

                      <Stack direction="row" spacing={0.5} useFlexGap flexWrap="wrap" alignItems="center">
                        {extraColumns.length > INITIAL_DYNAMIC_COLUMNS_LIMIT && (
                          <Button
                            size="small"
                            variant="text"
                            onClick={() => setShowAllDynamicColumns((current) => !current)}
                            sx={{ textTransform: 'none', borderRadius: 2, fontWeight: 700 }}
                          >
                            {showAllDynamicColumns
                              ? 'Masquer colonnes dynamiques'
                              : `Afficher toutes les colonnes dynamiques (${extraColumns.length})`}
                          </Button>
                        )}
                        {patients.length > INITIAL_ROWS_LIMIT && (
                          <Button
                            size="small"
                            variant="text"
                            onClick={() => setShowAllRows((current) => !current)}
                            sx={{ textTransform: 'none', borderRadius: 2, fontWeight: 700 }}
                          >
                            {showAllRows
                              ? 'Masquer lignes supplementaires'
                              : `Afficher toutes les lignes (${patients.length})`}
                          </Button>
                        )}
                      </Stack>
                    </Box>
                  </Stack>

                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                    {selectedPatientsCountLabel}
                  </Typography>

                  {selectedPatientIds.length > 0 && (
                    <Box
                      sx={{
                        mb: 1.5,
                        p: 1,
                        borderRadius: 2.5,
                        border: '1px solid rgba(15, 63, 81, 0.22)',
                        background: 'linear-gradient(120deg, rgba(15,63,81,0.10), rgba(31,122,140,0.10))',
                        position: 'sticky',
                        top: 8,
                        zIndex: 5,
                        backdropFilter: 'blur(2px)',
                      }}
                    >
                      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} justifyContent="space-between" alignItems={{ xs: 'stretch', sm: 'center' }}>
                        <Typography variant="body2" fontWeight={700} sx={{ color: '#0f3f51' }}>
                          {selectedPatientsCountLabel}
                        </Typography>
                        <Stack direction="row" spacing={1}>
                          <Button
                            size="small"
                            variant="contained"
                            startIcon={<EditOutlinedIcon />}
                            onClick={handleEditSelected}
                            disabled={selectedPatientIds.length !== 1 || deletingSelection}
                            sx={{ textTransform: 'none', borderRadius: 2, fontWeight: 700, whiteSpace: 'nowrap' }}
                          >
                            Modifier
                          </Button>
                          <Button
                            size="small"
                            color="error"
                            variant="outlined"
                            startIcon={<DeleteOutlineOutlinedIcon />}
                            onClick={handleDeleteSelected}
                            disabled={!selectedPatientIds.length || deletingSelection}
                            sx={{ textTransform: 'none', borderRadius: 2, fontWeight: 700, whiteSpace: 'nowrap' }}
                          >
                            {deletingSelection ? 'Suppression...' : 'Supprimer'}
                          </Button>
                        </Stack>
                      </Stack>
                    </Box>
                  )}

                  <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 3, overflowX: 'auto' }}>
                    <Table size="small" sx={{ minWidth: Math.max(900, (fixedBaseColumns.length + tableDisplaySchemaFields.length + visibleExtraColumns.length) * 130) }}>
                      <TableHead>
                        <TableRow sx={{ background: 'linear-gradient(135deg, rgba(22,90,114,0.08), rgba(31,122,140,0.14))' }}>
                          <TableCell padding="checkbox" sx={{ fontWeight: 800 }}>
                            <Checkbox
                              size="small"
                              checked={allVisibleSelected}
                              indeterminate={selectedVisibleCount > 0 && !allVisibleSelected}
                              onChange={(event) => toggleSelectAllVisible(event.target.checked)}
                              inputProps={{ 'aria-label': 'Selectionner toutes les lignes visibles' }}
                            />
                          </TableCell>
                          {fixedBaseColumns.map((column) => (
                            <TableCell key={`fixed-head-${column.key}`} sx={{ fontWeight: 800 }}>{column.label}</TableCell>
                          ))}
                          {tableDisplaySchemaFields.length ? tableDisplaySchemaFields.map((field) => (
                            <TableCell key={field.id} sx={{ fontWeight: 800 }}>{field.label}</TableCell>
                          )) : (
                            <TableCell sx={{ fontWeight: 800 }}>Aucune structure importée</TableCell>
                          )}
                          {visibleExtraColumns.map((columnKey) => (
                            <TableCell key={`extra-head-${columnKey}`} sx={{ fontWeight: 800 }}>
                              {columnKey}
                            </TableCell>
                          ))}
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {visiblePatients.map((patient) => (
                          <TableRow
                            key={patient.id}
                            hover
                            onDoubleClick={() => beginEdit(patient)}
                            sx={{ cursor: 'pointer' }}
                          >
                            <TableCell padding="checkbox">
                              <Checkbox
                                size="small"
                                checked={selectedPatientIds.includes(patient.id)}
                                onChange={() => togglePatientSelection(patient.id)}
                                inputProps={{ 'aria-label': `Selectionner la ligne du patient ${patient.id}` }}
                              />
                            </TableCell>
                            {fixedBaseColumns.map((column) => (
                              <TableCell key={`${patient.id}-fixed-${column.key}`}>
                                {renderValue(resolveTableCellValue(patient, column.key))}
                              </TableCell>
                            ))}
                            {tableDisplaySchemaFields.length ? tableDisplaySchemaFields.map((field) => (
                              <TableCell key={`${patient.id}-${field.id}`}>
                                {renderValue(resolveTableCellValue(patient, field.key))}
                              </TableCell>
                            )) : (
                              <TableCell>Importez le modèle Excel (Classeur1) pour générer les colonnes.</TableCell>
                            )}
                            {visibleExtraColumns.map((columnKey) => (
                              <TableCell key={`${patient.id}-extra-${columnKey}`}>
                                {renderValue(formatExtraValue(columnKey, patient?.extra_data?.[columnKey]))}
                              </TableCell>
                            ))}
                          </TableRow>
                        ))}
                        {!patients.length && (
                          <TableRow>
                            <TableCell colSpan={Math.max(2, fixedBaseColumns.length + tableDisplaySchemaFields.length + visibleExtraColumns.length + 1)} align="center">
                              Aucun patient trouvé.
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </CardContent>
              </Card>
            </Stack>
          </Grid>
        </Grid>
        ) : (
          <Stack spacing={3}>
            <Card elevation={0} sx={{ borderRadius: 4, border: '1px solid rgba(94, 115, 141, 0.12)' }}>
              <CardContent>
                <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={2}>
                  <Box>
                    <Typography variant="h6" fontWeight={800}>Tableau d'analyse clinique</Typography>
                    <Typography variant="body2" color="text.secondary">
                      Vue professionnelle orientee activite, risques et qualite des donnees.
                    </Typography>
                  </Box>
                  <Tabs
                    value={analysisView}
                    onChange={(_, value) => setAnalysisView(value)}
                    variant="scrollable"
                    allowScrollButtonsMobile
                    sx={{ minHeight: 38 }}
                  >
                    <Tab value="synthese" label="Synthese" />
                    <Tab value="profils" label="Profils" />
                    <Tab value="comorbidites" label="Comorbidites" />
                    <Tab value="qualite" label="Qualite des donnees" />
                  </Tabs>
                </Stack>
              </CardContent>
            </Card>

            <Grid container spacing={2}>
              <Grid item xs={12} sm={6} md={3}>
                <Card elevation={0} sx={{ borderRadius: 3, border: '1px solid rgba(94, 115, 141, 0.12)' }}>
                  <CardContent>
                    <Typography variant="body2" color="text.secondary">Total patients</Typography>
                    <Typography variant="h4" fontWeight={900}>{analysisSummary.totalPatients}</Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Card elevation={0} sx={{ borderRadius: 3, border: '1px solid rgba(94, 115, 141, 0.12)' }}>
                  <CardContent>
                    <Typography variant="body2" color="text.secondary">Taux inclusion</Typography>
                    <Typography variant="h4" fontWeight={900}>{analysisKpis.inclusionRate}%</Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Card elevation={0} sx={{ borderRadius: 3, border: '1px solid rgba(94, 115, 141, 0.12)' }}>
                  <CardContent>
                    <Typography variant="body2" color="text.secondary">Age moyen</Typography>
                    <Typography variant="h4" fontWeight={900}>{analysisSummary.averageAge}</Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Card elevation={0} sx={{ borderRadius: 3, border: '1px solid rgba(94, 115, 141, 0.12)' }}>
                  <CardContent>
                    <Typography variant="body2" color="text.secondary">Completude moyenne</Typography>
                    <Typography variant="h4" fontWeight={900}>{analysisSummary.averageCompleteness}%</Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>

            {analysisView === 'synthese' && (
              <Stack spacing={3}>
                <Grid container spacing={3}>
                  <Grid item xs={12} lg={7}>
                    <Card elevation={0} sx={{ borderRadius: 4, border: '1px solid rgba(94, 115, 141, 0.12)' }}>
                      <CardContent>
                        <Typography variant="h6" fontWeight={800} sx={{ mb: 1.5 }}>Evolution mensuelle des inclusions</Typography>
                        {analysisSummary.monthlyInclusions.length ? (
                          <Box sx={{ height: 300 }}>
                            <Line data={monthlyInclusionChartData} options={defaultChartOptions} />
                          </Box>
                        ) : <Typography variant="body2" color="text.secondary">Aucune date exploitable pour les inclusions.</Typography>}
                      </CardContent>
                    </Card>
                  </Grid>
                  <Grid item xs={12} lg={5}>
                    <Card elevation={0} sx={{ borderRadius: 4, border: '1px solid rgba(94, 115, 141, 0.12)', height: '100%' }}>
                      <CardContent>
                        <Typography variant="h6" fontWeight={800} sx={{ mb: 1.5 }}>Indicateurs cles</Typography>
                        <Stack spacing={1.5}>
                          <Box>
                            <Typography variant="body2" color="text.secondary">Volume total complications</Typography>
                            <Typography variant="h5" fontWeight={900}>{analysisKpis.complicationsTotal}</Typography>
                          </Box>
                          <Box>
                            <Typography variant="body2" color="text.secondary">Etiologie dominante</Typography>
                            <Typography variant="h6" fontWeight={800}>{analysisKpis.topEtiology}</Typography>
                          </Box>
                          <Box>
                            <Typography variant="body2" color="text.secondary">Repartition sexe</Typography>
                            <Stack spacing={1} sx={{ mt: 0.5 }}>
                              {analysisSummary.sexCounts.map((item) => {
                                const percent = analysisSummary.totalPatients ? Math.round((item.count / analysisSummary.totalPatients) * 100) : 0;
                                return (
                                  <Box key={`sex-summary-${item.label}`}>
                                    <Stack direction="row" justifyContent="space-between">
                                      <Typography variant="body2">{item.label}</Typography>
                                      <Typography variant="body2" fontWeight={700}>{percent}%</Typography>
                                    </Stack>
                                    <LinearProgress variant="determinate" value={percent} sx={{ mt: 0.5, height: 7, borderRadius: 999 }} />
                                  </Box>
                                );
                              })}
                            </Stack>
                          </Box>
                        </Stack>
                      </CardContent>
                    </Card>
                  </Grid>
                </Grid>

                <Card elevation={0} sx={{ borderRadius: 4, border: '1px solid rgba(94, 115, 141, 0.12)' }}>
                  <CardContent>
                    <Typography variant="h6" fontWeight={800} sx={{ mb: 1.5 }}>Complications dans le temps (barres empilees)</Typography>
                    {analysisSummary.monthlyComplications.length ? (
                      <Box sx={{ height: 320 }}>
                        <Bar
                          data={monthlyComplicationsChartData}
                          options={{
                            ...defaultChartOptions,
                            scales: {
                              x: { stacked: true },
                              y: {
                                ...(defaultChartOptions.scales?.y || {}),
                                stacked: true,
                              },
                            },
                          }}
                        />
                      </Box>
                    ) : <Typography variant="body2" color="text.secondary">Aucune date exploitable pour les complications.</Typography>}
                  </CardContent>
                </Card>
              </Stack>
            )}

            {analysisView === 'profils' && (
              <Stack spacing={3}>
                <Card elevation={0} sx={{ borderRadius: 4, border: '1px solid rgba(94, 115, 141, 0.12)' }}>
                  <CardContent>
                    <Typography variant="h6" fontWeight={800} sx={{ mb: 0.5 }}>Graphe 3D profil patient</Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                      Projection 3D interactive: age, comorbidites et complications.
                    </Typography>
                    {analysisSummary.profile3dPoints.length ? (
                      <>
                        <Box sx={{ px: 1, mb: 1.5 }}>
                          <Typography variant="caption" color="text.secondary">Angle 3D: {profile3dAngle}°</Typography>
                          <Slider
                            value={profile3dAngle}
                            onChange={(_, value) => setProfile3dAngle(Number(value))}
                            min={0}
                            max={85}
                            step={1}
                            valueLabelDisplay="auto"
                            size="small"
                          />
                        </Box>
                        <Box sx={{ height: 360 }}>
                          <Bubble data={profileProjectedBubbleData} options={profileBubbleOptions} />
                        </Box>
                      </>
                    ) : <Typography variant="body2" color="text.secondary">Aucune donnee suffisante pour le graphe 3D.</Typography>}
                  </CardContent>
                </Card>

                <Card elevation={0} sx={{ borderRadius: 4, border: '1px solid rgba(94, 115, 141, 0.12)' }}>
                  <CardContent>
                    <Typography variant="h6" fontWeight={800} sx={{ mb: 1.5 }}>Distribution age par sexe</Typography>
                    <Box sx={{ height: 320 }}>
                      <Bar data={ageSexHistogramData} options={defaultChartOptions} />
                    </Box>
                  </CardContent>
                </Card>

                <Card elevation={0} sx={{ borderRadius: 4, border: '1px solid rgba(94, 115, 141, 0.12)' }}>
                  <CardContent>
                    <Typography variant="h6" fontWeight={800} sx={{ mb: 1.5 }}>Etiologie IRC vers statut inclusion (barres groupees)</Typography>
                    {analysisSummary.etiologyInclusionGrouped.labels.length ? (
                      <Box sx={{ height: 330 }}>
                        <Bar data={etiologyInclusionChartData} options={defaultChartOptions} />
                      </Box>
                    ) : <Typography variant="body2" color="text.secondary">Aucune donnee suffisante pour le graphe etiologie/inclusion.</Typography>}
                  </CardContent>
                </Card>
              </Stack>
            )}

            {analysisView === 'comorbidites' && (
              <Stack spacing={3}>
                <Card elevation={0} sx={{ borderRadius: 4, border: '1px solid rgba(94, 115, 141, 0.12)' }}>
                  <CardContent>
                    <Typography variant="h6" fontWeight={800} sx={{ mb: 2 }}>Barres des comorbidites les plus frequentes</Typography>
                    <Stack spacing={1.5}>
                      {analysisSummary.topComorbidities.length ? analysisSummary.topComorbidities.map((item) => {
                        const percent = analysisSummary.totalPatients
                          ? Math.round((item.count / analysisSummary.totalPatients) * 100)
                          : 0;
                        return (
                          <Box key={`comorb-${item.label}`}>
                            <Stack direction="row" justifyContent="space-between" spacing={1}>
                              <Typography variant="body2">{item.label}</Typography>
                              <Typography variant="body2" fontWeight={700}>{item.count} ({percent}%)</Typography>
                            </Stack>
                            <LinearProgress
                              variant="determinate"
                              value={percent}
                              sx={{
                                mt: 0.75,
                                height: 8,
                                borderRadius: 999,
                                '& .MuiLinearProgress-bar': {
                                  backgroundColor: '#1f7a8c',
                                },
                              }}
                            />
                          </Box>
                        );
                      }) : (
                        <Typography variant="body2" color="text.secondary">Aucune donnee comorbidite exploitable.</Typography>
                      )}
                    </Stack>
                  </CardContent>
                </Card>

                <Card elevation={0} sx={{ borderRadius: 4, border: '1px solid rgba(94, 115, 141, 0.12)' }}>
                  <CardContent>
                    <Typography variant="h6" fontWeight={800} sx={{ mb: 1.5 }}>Top combinaisons de comorbidites</Typography>
                    {analysisSummary.topComorbidityCombinations.length ? (
                      <Box sx={{ height: 340 }}>
                        <Bar
                          data={comorbidityCombinationChartData}
                          options={{
                            ...defaultChartOptions,
                            indexAxis: 'y',
                          }}
                        />
                      </Box>
                    ) : (
                      <Typography variant="body2" color="text.secondary">Aucune combinaison de comorbidites disponible.</Typography>
                    )}
                  </CardContent>
                </Card>
              </Stack>
            )}

            {analysisView === 'qualite' && (
              <Stack spacing={3}>
                <Grid container spacing={3}>
                  <Grid item xs={12} md={6}>
                    <Card elevation={0} sx={{ borderRadius: 4, border: '1px solid rgba(94, 115, 141, 0.12)' }}>
                      <CardContent>
                        <Typography variant="h6" fontWeight={800} sx={{ mb: 1.5 }}>Statut inclusion</Typography>
                        <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2 }}>
                          <Table size="small">
                            <TableHead>
                              <TableRow>
                                <TableCell sx={{ fontWeight: 800 }}>Statut</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 800 }}>Patients</TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {analysisSummary.inclusionCounts.length ? analysisSummary.inclusionCounts.map((item) => (
                                <TableRow key={`inc-${item.label}`}>
                                  <TableCell>{item.label}</TableCell>
                                  <TableCell align="right">{item.count}</TableCell>
                                </TableRow>
                              )) : (
                                <TableRow>
                                  <TableCell colSpan={2} align="center">Aucune donnee</TableCell>
                                </TableRow>
                              )}
                            </TableBody>
                          </Table>
                        </TableContainer>
                      </CardContent>
                    </Card>
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <Card elevation={0} sx={{ borderRadius: 4, border: '1px solid rgba(94, 115, 141, 0.12)' }}>
                      <CardContent>
                        <Typography variant="h6" fontWeight={800} sx={{ mb: 1.5 }}>Top etiologies IRC</Typography>
                        <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2 }}>
                          <Table size="small">
                            <TableHead>
                              <TableRow>
                                <TableCell sx={{ fontWeight: 800 }}>Etiologie</TableCell>
                                <TableCell align="right" sx={{ fontWeight: 800 }}>Patients</TableCell>
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {analysisSummary.topEtiologies.length ? analysisSummary.topEtiologies.map((item) => (
                                <TableRow key={`etio-${item.label}`}>
                                  <TableCell>{item.label}</TableCell>
                                  <TableCell align="right">{item.count}</TableCell>
                                </TableRow>
                              )) : (
                                <TableRow>
                                  <TableCell colSpan={2} align="center">Aucune donnee</TableCell>
                                </TableRow>
                              )}
                            </TableBody>
                          </Table>
                        </TableContainer>
                      </CardContent>
                    </Card>
                  </Grid>
                </Grid>
              </Stack>
            )}
          </Stack>
        )}
          </>
        ) : (
          <Stack spacing={3}>
            <Card elevation={0} sx={{ borderRadius: 4, border: '1px solid rgba(94, 115, 141, 0.12)' }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="h5" fontWeight={900}>
                  Modele AI
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  Espace dedie aux modeles IA: experimentation, evaluation et suivi des performances.
                </Typography>
              </CardContent>
            </Card>

            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Card elevation={0} sx={{ borderRadius: 4, border: '1px solid rgba(94, 115, 141, 0.12)' }}>
                  <CardContent>
                    <Typography variant="h6" fontWeight={800} sx={{ mb: 1 }}>
                      Entrainement du modele
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Zone reservee pour lancer les entrainements, choisir les features et comparer les versions du modele.
                    </Typography>
                    <Button variant="contained" sx={{ mt: 2 }} disabled>
                      Configurer (bientot)
                    </Button>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} md={6}>
                <Card elevation={0} sx={{ borderRadius: 4, border: '1px solid rgba(94, 115, 141, 0.12)' }}>
                  <CardContent>
                    <Typography variant="h6" fontWeight={800} sx={{ mb: 1 }}>
                      Evaluation et inference
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Zone reservee pour la prediction IA, la qualite du modele et la visualisation des metriques cliniques.
                    </Typography>
                    <Button variant="outlined" sx={{ mt: 2 }} disabled>
                      Ouvrir module IA (bientot)
                    </Button>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </Stack>
        )}
      </Stack>
        </Grid>
      </Grid>

      <Dialog open={isEditDialogOpen} onClose={closeEditDialog} fullWidth maxWidth="md">
        <DialogTitle>Modifier la ligne sélectionnée</DialogTitle>
        <Box component="form" onSubmit={handleSave}>
          <DialogContent dividers sx={{ display: 'grid', gap: 2 }}>
            <TextField label="Nom" name="nom" value={form.nom} onChange={handleChange} required fullWidth size="small" />
            <TextField label="Prénom" name="prenom" value={form.prenom} onChange={handleChange} required fullWidth size="small" />
            <TextField label="Âge" name="age" type="number" value={form.age} onChange={handleChange} fullWidth size="small" />
            <TextField select label="Sexe" name="sexe" value={form.sexe} onChange={handleChange} fullWidth size="small">
              <MenuItem value="">Sélectionner</MenuItem>
              <MenuItem value="M">Homme</MenuItem>
              <MenuItem value="F">Femme</MenuItem>
              <MenuItem value="O">Autre</MenuItem>
            </TextField>
            <TextField label="Maladie" name="maladie" value={form.maladie} onChange={handleChange} fullWidth size="small" />
            <TextField
              label="Date de naissance"
              name="date_naissance"
              type="date"
              value={form.date_naissance}
              onChange={handleChange}
              fullWidth
              size="small"
              InputLabelProps={{ shrink: true }}
            />

            {schemaTemplate?.fields?.length ? (
              <Box
                sx={{
                  p: 1.5,
                  borderRadius: 2,
                  border: '1px solid rgba(94, 115, 141, 0.18)',
                  backgroundColor: 'rgba(255,255,255,0.8)',
                  maxHeight: 320,
                  overflowY: 'auto',
                  display: 'grid',
                  gap: 1.25,
                }}
              >
                <Typography variant="subtitle2" fontWeight={800}>
                  Modifier les champs de la ligne
                </Typography>
                {schemaTemplate.fields.map((field) => {
                  const value = schemaAnswers[field.key];

                  if (field.field_type === 'auto') {
                    return (
                      <TextField
                        key={field.id}
                        label={field.label}
                        value={value || ''}
                        size="small"
                        fullWidth
                        disabled
                      />
                    );
                  }

                  if (field.field_type === 'single_choice' || field.field_type === 'boolean') {
                    return (
                      <TextField
                        key={field.id}
                        select
                        label={field.label}
                        value={value || ''}
                        onChange={(event) => handleSchemaAnswerChange(field, event.target.value)}
                        size="small"
                        fullWidth
                      >
                        <MenuItem value="">Selectionner</MenuItem>
                        {(field.choices || []).map((choice) => (
                          <MenuItem key={`${field.id}-dlg-${choice}`} value={choice}>{choice}</MenuItem>
                        ))}
                      </TextField>
                    );
                  }

                  if (field.field_type === 'multiple_choice') {
                    return (
                      <TextField
                        key={field.id}
                        select
                        label={field.label}
                        value={Array.isArray(value) ? value : []}
                        onChange={(event) => handleSchemaAnswerChange(field, event.target.value)}
                        size="small"
                        fullWidth
                        SelectProps={{
                          multiple: true,
                          renderValue: (selected) => selected.join(', '),
                        }}
                      >
                        {(field.choices || []).map((choice) => (
                          <MenuItem key={`${field.id}-dlg-m-${choice}`} value={choice}>{choice}</MenuItem>
                        ))}
                      </TextField>
                    );
                  }

                  if (field.field_type === 'date') {
                    return (
                      <TextField
                        key={field.id}
                        label={field.label}
                        type="date"
                        value={value || ''}
                        onChange={(event) => handleSchemaAnswerChange(field, event.target.value)}
                        size="small"
                        fullWidth
                        InputLabelProps={{ shrink: true }}
                      />
                    );
                  }

                  if (field.field_type === 'integer') {
                    return (
                      <TextField
                        key={field.id}
                        label={field.label}
                        type="number"
                        value={value || ''}
                        onChange={(event) => handleSchemaAnswerChange(field, event.target.value)}
                        size="small"
                        fullWidth
                      />
                    );
                  }

                  return (
                    <TextField
                      key={field.id}
                      label={field.label}
                      value={value || ''}
                      onChange={(event) => handleSchemaAnswerChange(field, event.target.value)}
                      size="small"
                      fullWidth
                      multiline={field.field_type === 'text_long'}
                      minRows={field.field_type === 'text_long' ? 2 : undefined}
                    />
                  );
                })}
              </Box>
            ) : null}

            {renderDynamicExtraFields('Colonnes dynamiques de cette ligne')}

          </DialogContent>
          <DialogActions>
            <Button type="button" onClick={closeEditDialog}>Annuler</Button>
            <Button type="submit" variant="contained" disabled={saving}>Enregistrer</Button>
          </DialogActions>
        </Box>
      </Dialog>
    </Box>
  );
}

export default PatientsManagement;
