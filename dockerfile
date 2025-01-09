#!/bin/bash

FROM python:3.9-slim

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application files
COPY . /app
WORKDIR /app

# Run the app
CMD ["uvicorn", "arabic_dict_api:app", "--host", "0.0.0.0", "--port", "8000"]
