
FROM python:3.10

# working directory 
WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# copy all files to working directoyuy
COPY . .

# turn on port, ?? 
EXPOSE 8000

# running fastapi with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]