FROM python:3.11-slim-bookworm AS build-env

# You can build the docker image with the command :
# docker build --no-cache -t seances .

# You can create a container with :
# docker run -it --rm seances [ID_CINEMA]

WORKDIR /src
COPY pyproject.toml README.md LICENSE MANIFEST.in seances.py ./
COPY allocine ./allocine

RUN pip install -U --no-cache-dir --target /app . \
&& find /app | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf

FROM gcr.io/distroless/python3-debian12

COPY --from=build-env /app /app

ENV PYTHONPATH=/app
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

ENTRYPOINT ["python", "/app/bin/seances.py"]
