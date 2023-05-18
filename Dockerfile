FROM python:3.9-alpine

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_ENV=development

CMD ["flask", "run"]


# alternative code
# # Use an official Python runtime as the base image
# FROM python:3.9-slim

# # Set the working directory in the container
# WORKDIR /app

# # Copy the Python files into the container
# COPY app.py compareshape.py shape.py /app/

# # Install the required Python packages
# RUN pip install flask flask_cors requests

# # Set the environment variables for Flask
# ENV FLASK_APP=app.py
# ENV FLASK_ENV=development

# # Expose port 5000
# EXPOSE 5000

# # Set the entry point for the container
# ENTRYPOINT ["flask", "run", "--host=0.0.0.0", "--port=5000", "--debugger", "--reload"]
