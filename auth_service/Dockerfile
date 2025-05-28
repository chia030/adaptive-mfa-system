FROM python:3.13-slim

WORKDIR /
COPY ../.env ./.env  
COPY /shared_lib ./shared_lib
RUN pip install --no-cache-dir -e ./shared_lib
COPY auth_service/ ./auth_service/
COPY auth_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# WORKDIR /auth_service/app/db
# RUN python create_tables.py

WORKDIR /auth_service
# CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
RUN chmod +x entrypoint.sh
CMD ["./entrypoint.sh"]
