FROM node:22-alpine

WORKDIR /app

COPY package*.json ./
COPY dist/ ./dist/

ENV NODE_ENV=production
ENV PORT=80

RUN npm install --ignore-scripts --omit-dev

CMD ["node", "dist/server.js"]