# Usar una imagen base de Python
# FROM python:3.9-slim
# FROM python:3.10-alpine
FROM python:3.10-slim

# Datadog config
RUN DD_API_KEY=4ca9b95447eb0d7b3f9ae8a271816db9 \
    DD_SITE="datadoghq.com" \
    bash -c "$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_script.sh)"

# Establecer el directorio de trabajo
WORKDIR /app
# WORKDIR /code

# Copiar los archivos requeridos
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Exponer el puerto que usará la aplicación
# EXPOSE 5000
EXPOSE 8080

# Comando para ejecutar la aplicación
# CMD ["python", "app.py"]
# CMD ["flask", "run", "--host=0.0.0.0"]
CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]