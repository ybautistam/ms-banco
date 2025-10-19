# mbancos/Dockerfile
FROM python:3.11-slim

# Opcional: hace que Python no cree .pyc y loguee sin buffer
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 1) Instala dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Copia solo el código de tu servicio (según tu árbol de carpetas)
COPY . . 


CMD ["uvicorn", "main.app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]

#para railway
CMD ["sh", "-c", "uvicorn main.app:app --host 0.0.0.0 --port ${PORT:-8000}"]