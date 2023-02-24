from python:alpine

COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt && \
    mkdir -p /streamfiles

ENV STREAMFILE_FOLDER=/streamfiles

CMD ["python", "src/main.py"]