FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy
WORKDIR /app
COPY scraper/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY scraper/ .
CMD ["python", "scraper.py"]
