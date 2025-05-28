FROM python:3.13-slim

WORKDIR /
COPY ../.env ./.env
COPY /shared_lib ./shared_lib
RUN pip install --no-cache-dir -e ./shared_lib
COPY mfa_handler/ ./mfa_handler/
COPY mfa_handler/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# WORKDIR /mfa_handler/app/db
# RUN python create_tables.py

WORKDIR /mfa_handler
# CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8002"]
RUN chmod +x entrypoint.sh
CMD ["./entrypoint.sh"]
