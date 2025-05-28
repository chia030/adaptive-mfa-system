FROM python:3.13-slim

WORKDIR /
COPY ../.env ./.env  
COPY /shared_lib ./shared_lib
RUN pip install --no-cache-dir -e ./shared_lib
COPY risk_engine/ ./risk_engine/
COPY risk_engine/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# WORKDIR /risk_engine/app/db
# RUN python create_tables.py

WORKDIR /risk_engine
# CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8001"]
RUN chmod +x entrypoint.sh
CMD ["./entrypoint.sh"]
