FROM mirror.gcr.io/library/node:22-alpine AS frontend

WORKDIR /web
COPY Web/package.json Web/package-lock.json* ./
RUN npm ci --ignore-scripts || npm install
COPY Web/ ./
RUN npm run build

FROM mirror.gcr.io/library/python:3.12-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend /web/dist /app/Web/dist

VOLUME ["/app/data"]

CMD ["python", "main.py"]
