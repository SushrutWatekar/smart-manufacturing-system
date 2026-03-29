FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt
EXPOSE 8000
ENV FLASK_APP=main.py
ENV FLASK_RUN_PORT=8000
ENV FLASK_ENV=production
# CMD ["/bin/sh", "-c", "echo 'Delaying startup by 10 seconds...'; sleep 10; flask run --host=0.0.0.0"]
CMD ["sh", "-c", "sleep 10 && flask run --host=0.0.0.0"]
