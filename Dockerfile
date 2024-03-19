FROM python:3.12-alpine as builder
COPY . /app
WORKDIR /app
RUN pip install --user --no-cache-dir -r requirements.txt
RUN playwright install

FROM python:3.12-alpine as app
COPY --from=builder /root/.local /root/.local
COPY --from=builder /app .

ENV PATH=/root/.local:$PATH
EXPOSE 5000

CMD ["python3", "run.py"]
