FROM alpine:latest

COPY . /root

WORKDIR /root
RUN apk add --no-cache python3 cmd:pip3 ffmpeg
RUN pip3 install -U pip && pip3 install -r requirements.txt && pip cache purge

CMD ["hypercorn", "-b", "0.0.0.0:8090", "microclient:app"]