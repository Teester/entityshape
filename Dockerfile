FROM python:3.9-alpine

WORKDIR /app

COPY . .
RUN pip install -r requirements.txt

EXPOSE 5000

ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_ENV=development

CMD ["flask", "run"]

# Build and run command: docker build -t es-image . && docker run --name entityshape --rm -d -p 5000:5000 es-image
# example request: http://localhost:5000/api?entityschema=E1&entity=Q482&url=https://geokb.wikibase.cloud
# pyshexy request: http://localhost:5000/pyshexy?entityschema=E1&entity=Q45&url=https://wiki.demo5280.com