FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /opt/fabflow
RUN useradd --create-home --uid 10001 fabflow
COPY pyproject.toml README.md ./
COPY app ./app
COPY simulator ./simulator

FROM base AS api
RUN python -m pip install .
USER fabflow
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

FROM base AS dashboard
RUN python -m pip install ".[dashboard]"
USER fabflow
EXPOSE 8501
CMD ["python", "-m", "streamlit", "run", "app/dashboard/main.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true", "--browser.gatherUsageStats=false"]
