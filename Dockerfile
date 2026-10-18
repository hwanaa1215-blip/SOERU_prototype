FROM node:22-bookworm-slim AS web
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/index.html frontend/tsconfig.json frontend/vite.config.ts ./
COPY frontend/src ./src
COPY frontend/public ./public
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 WEB_DIST=/app/frontend/dist
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/*.py ./
COPY samples /app/samples
COPY --from=web /build/dist /app/frontend/dist
RUN useradd --uid 10001 --create-home appuser
USER appuser
CMD ["sh", "-c", "exec python -m uvicorn server:create_app --factory --host 0.0.0.0 --port ${PORT:-8080} --no-access-log"]
