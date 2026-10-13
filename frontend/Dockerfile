FROM node:24-alpine AS base

WORKDIR /app

RUN addgroup -g 1001 app && \
    adduser -D -u 1001 -G app app

FROM base AS deps
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM base AS builder
COPY --from=deps /app/node_modules /app/node_modules
COPY . .
RUN npm run build

FROM nginx:1.27-alpine AS runtime

RUN addgroup -g 1001 app && \
    adduser -D -u 1001 -G app app

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q --spider http://localhost:80/ || exit 1

EXPOSE 80

USER app

CMD ["nginx", "-g", "daemon off;"]