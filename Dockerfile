FROM openjdk:17-slim-bullseye
RUN apt-get update &&  apt-get upgrade -y \
    && apt install libpq-dev gcc -y \
    && apt install python3 -y \
    && apt install python3-pip -y
RUN python3.9 -m pip install --upgrade pip
COPY . /app
RUN pip install -r /app/requirements.txt
WORKDIR /app
CMD ["python3", "main.py" ]
