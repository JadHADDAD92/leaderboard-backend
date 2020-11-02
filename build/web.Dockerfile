FROM tiangolo/uvicorn-gunicorn-fastapi:python3.7

COPY ./leaderboard /app/app
COPY ./requirements.txt /app/requirements.txt
COPY ./build/prestart.sh /app/prestart.sh
RUN pip install --upgrade pip
RUN pip install -r /app/requirements.txt
