FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV EMBEDDING_CACHE_DIR=/opt/models

COPY requirements.txt requirements-etl.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-etl.txt

RUN python -c "from fastembed import TextEmbedding; m = TextEmbedding('BAAI/bge-small-en-v1.5', cache_dir='/opt/models'); print(len(list(m.embed(['warm up']))[0]))"

COPY app ./app
COPY etl ./etl
COPY sql ./sql

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
