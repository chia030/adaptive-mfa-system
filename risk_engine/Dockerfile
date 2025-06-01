FROM python:3.13-slim

WORKDIR /
COPY ../.env ./.env  
COPY /shared_lib ./shared_lib
RUN pip install --no-cache-dir -e ./shared_lib
COPY risk_engine/ ./risk_engine/
COPY risk_engine/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# install test dependencies
RUN pip install --no-cache-dir pytest pytest-asyncio faker aiosqlite

WORKDIR /risk_engine

RUN chmod +x entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]

# default command to launch uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
