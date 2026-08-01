FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Hugging Face Spaces expects the app on port 7860
ENV PORT=7860
EXPOSE 7860

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:7860", "--workers", "2", "--threads", "4", "--timeout", "120"]
