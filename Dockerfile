# Wildfire Calendar: Streamlit app image
FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/romiisromie/wildfire-calendar" \
      org.opencontainers.image.description="Harmonized 25-year MODIS + VIIRS wildfire calendar (NASA Space Apps 2026)" \
      org.opencontainers.image.licenses="NOASSERTION"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
