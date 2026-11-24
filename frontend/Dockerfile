# =========================================================================
# Stage 1: Build production static bundle
# =========================================================================
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first for Docker layer caching
COPY package*.json ./
RUN npm install

# Copy application source
COPY . .

# Build-time environment variables for Vite
ARG VITE_API_URL
ARG VITE_BACKEND_URL
ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_BACKEND_URL=${VITE_BACKEND_URL}

# Compile TypeScript and bundle with Vite
RUN npm run build

# =========================================================================
# Stage 2: Production Nginx Server
# =========================================================================
FROM nginx:1.27-alpine AS runner

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
