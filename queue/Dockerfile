FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8004
ENV FLASK_APP=main.py
ENV FLASK_RUN_PORT=8004
ENV FLASK_ENV=production
CMD ["sh", "-c", "sleep 10 && flask run --host=0.0.0.0"]
