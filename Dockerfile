FROM python:3.9-alpine

COPY requirements.txt /tmp/
RUN pip install --requirement /tmp/requirements.txt
COPY jenkins_exporter.py /
RUN addgroup -S jenkins && adduser -S jenkins -G jenkins
USER jenkins

ENTRYPOINT ["/jenkins_exporter.py"]

