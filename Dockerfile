# syntax=docker/dockerfile:1
FROM python:3.10
WORKDIR /cc_event_bot

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
