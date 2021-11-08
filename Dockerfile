FROM python:3.9

WORKDIR /DisnakeWavelinkBot

COPY requirements.txt /DisnakeWavelinkBot

RUN pip3 install -r requirements.txt

COPY . /DisnakeWavelinkBot


CMD ["python3", "main.py"]