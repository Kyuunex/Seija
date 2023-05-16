FROM python:3.11-slim-bullseye

COPY . /tmp/seija/

RUN pip3 install --trusted-host pypi.python.org -r /tmp/seija/requirements.txt /tmp/seija

CMD ["python3", "-m", "seija"]
