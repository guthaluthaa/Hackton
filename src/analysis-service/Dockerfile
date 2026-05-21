FROM python:3.12-slim

WORKDIR /app

# PyMuPDF distribui wheels pré-compiladas — sem dependências de sistema adicionais
COPY src/analysis-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/analysis-service/ .

CMD ["python", "main.py"]
