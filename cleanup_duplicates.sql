-- Remove duplicate auth_permission rows (keep first, remove rest)
DELETE FROM auth_permission 
WHERE ctid NOT IN (
  SELECT MIN(ctid) FROM auth_permission GROUP BY id
);

-- Remove duplicate django_content_type rows
DELETE FROM django_content_type 
WHERE ctid NOT IN (
  SELECT MIN(ctid) FROM django_content_type GROUP BY id
);

-- Remove duplicate django_migrations rows
DELETE FROM django_migrations 
WHERE ctid NOT IN (
  SELECT MIN(ctid) FROM django_migrations GROUP BY id
);

-- Remove duplicate users_role rows (by nom)
DELETE FROM users_role 
WHERE ctid NOT IN (
  SELECT MIN(ctid) FROM users_role GROUP BY nom
);

-- Remove duplicate users_utilisateur rows (by email)
DELETE FROM users_utilisateur 
WHERE ctid NOT IN (
  SELECT MIN(ctid) FROM users_utilisateur GROUP BY email
);

-- Remove duplicate auth_group rows (by name)
DELETE FROM auth_group 
WHERE ctid NOT IN (
  SELECT MIN(ctid) FROM auth_group GROUP BY name
);

-- Clean invalid icc_charlson values
UPDATE patients_patient SET icc_charlson = 0 
WHERE icc_charlson IS NULL OR icc_charlson::text = '' OR icc_charlson::text !~ '^[0-9]+$';

SELECT 'Cleanup completed' AS result;
