FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV WEB_HOST=0.0.0.0
ENV WEB_PORT=7860
ENV USE_LIVE_MARKET_DATA=false

EXPOSE 7860

CMD ["python", "web_app.py"]
