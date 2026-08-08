FROM python:3.14-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LANTERN_BIND_HOST=0.0.0.0 \
    LANTERN_PORT=8769 \
    LANTERN_ALLOW_PRIVATE_HTTP=1

WORKDIR /app

RUN addgroup -S lantern && adduser -S -G lantern -h /app lantern
COPY --chown=lantern:lantern pyproject.toml README_EN.md LICENSE ./
COPY --chown=lantern:lantern src ./src
RUN pip install --no-cache-dir --no-deps .

USER lantern
EXPOSE 8769
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8769/health', timeout=2)"

ENTRYPOINT ["mail-lantern"]
