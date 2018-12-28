FROM python:3.5-alpine  AS build-env

# You can build the docker image with the command :
# docker build --no-cache -t seances .

# You can create a container with :
# docker run -it --rm seances [ID_CINEMA]

RUN pip install -U --no-cache-dir allocine

FROM gcr.io/distroless/python3

COPY --from=build-env /usr/local/lib/python3.5/site-packages /usr/local/lib/python3.5/site-packages
COPY --from=build-env /usr/local/bin/seances.py /usr/local/bin/seances.py

ENV PYTHONPATH=/usr/local/lib/python3.5/site-packages
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

ENTRYPOINT ["python", "/usr/local/bin/seances.py"]