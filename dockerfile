FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
COPY prompt.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "arabic_dict_api.py"]
