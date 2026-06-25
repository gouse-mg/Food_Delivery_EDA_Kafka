FROM python:3.11-slim

WORKDIR /app

COPY r.txt .
RUN pip install --no-cache-dir -r r.txt

COPY . .

EXPOSE 8000

CMD ["python", "-u", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000","--reload"]
