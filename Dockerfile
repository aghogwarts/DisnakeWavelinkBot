FROM openjdk:17-slim-bullseye
RUN apt-get update &&  apt-get upgrade -y \
    && apt install libpq-dev gcc -y \
    && apt install python3 -y \
    && apt install python3-pip -y
RUN python3.9 -m pip install --upgrade pip
COPY . /src
RUN pip install -r /src/requirements.txt
WORKDIR /src
CMD ["python3", "main.py" ]
