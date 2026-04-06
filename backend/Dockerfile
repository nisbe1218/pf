FROM python:3.11-slim

WORKDIR /app

# Empêche Python d'écrire des fichiers .pyc et force l'affichage des logs
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Installation des dépendances système requises pour PostgreSQL
RUN apt-get update \
    && apt-get install -y libpq-dev gcc \
    && apt-get clean

# Installation des dépendances Python
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copier le code source
COPY . /app/

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
