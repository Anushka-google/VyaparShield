FROM node:20-alpine

WORKDIR /app

# Install dependencies first for Docker caching
COPY package*.json ./
RUN npm install

# Copy application source
COPY . .

EXPOSE 3000

# Start Vite with external host binding for Docker networking
CMD ["npm", "run", "dev", "--", "--host"]
