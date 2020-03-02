FROM python:2.7

RUN mkdir -p /usr/src/logan/Input
RUN mkdir /usr/src/logan/Output
WORKDIR /usr/src/logan/

COPY ./main_script.py /usr/src/logan

CMD ["python", "main_script.py"]
