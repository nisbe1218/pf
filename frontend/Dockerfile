FROM node:18-alpine

WORKDIR /app

# Copier les fichiers de dépendances et installer
# Si le dossier est vide (pour le premier lancement), ça passera quand même
COPY package*.json ./
RUN npm install || true

# Copier le reste du projet
COPY . .

EXPOSE 3000

CMD ["npm", "start"]
