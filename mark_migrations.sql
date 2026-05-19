INSERT INTO django_migrations (app, name, applied) 
VALUES ('users', '0005_alter_role_id_alter_utilisateur_id', NOW());

INSERT INTO django_migrations (app, name, applied) 
VALUES ('users', '0006_utilisateur_personal_notes', NOW());

SELECT 'Migrations marked as applied' AS result;
