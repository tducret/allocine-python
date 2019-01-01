FROM python:3.5-alpine  AS build-env

# You can build the docker image with the command :
# docker build --no-cache -t seances .

# You can create a container with :
# docker run -it --rm seances [ID_CINEMA]

RUN pip install -U --no-cache-dir --target /app allocine \
&& find /app | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf

FROM gcr.io/distroless/python3

COPY --from=build-env /app /app

ENV PYTHONPATH=/app
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

ENTRYPOINT ["python", "/app/bin/seances.py"]