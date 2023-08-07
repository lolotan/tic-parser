FROM python:3.11.4-slim-bullseye

RUN pip install pyserial
RUN pip install paho-mqtt

WORKDIR /application/

COPY tic_parser.py .

ENTRYPOINT ["python", "tic_parser.py"]