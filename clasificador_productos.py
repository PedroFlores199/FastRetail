from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
import boto3
import sqlite3

app = FastAPI()

# Configuración de AWS
AWS_REGION = 'us-east-1'
BUCKET_NAME = 'fastretail-imagenes-catalogo'
s3_client = boto3.client('s3', region_name=AWS_REGION)
rekognition_client = boto3.client('rekognition', region_name=AWS_REGION)


# Configuración de la Base de Datos SQLite
def init_db():
    conn = sqlite3.connect('fastretail.db')
    cursor = conn.cursor()
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS clasificaciones
                   (
                       id
                       INTEGER
                       PRIMARY
                       KEY
                       AUTOINCREMENT,
                       nombre_archivo
                       TEXT,
                       etiquetas
                       TEXT
                   )
                   ''')
    conn.commit()
    conn.close()


init_db()


@app.get("/", response_class=HTMLResponse)
async def index():
    # Frontend básico integrado
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>FastRetail - Clasificador IA</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 50px; background-color: #f4f4f9; }
            .container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); max-width: 500px; margin: auto; }
            button { background-color: #007BFF; color: white; padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; }
            button:hover { background-color: #0056b3; }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Subida de Productos - FastRetail</h2>
            <form action="/clasificar/" enctype="multipart/form-data" method="post">
                <input name="file" type="file" required accept="image/jpeg, image/png">
                <button type="submit">Analizar Imagen</button>
            </form>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.post("/clasificar/")
async def clasificar_imagen(file: UploadFile = File(...)):
    try:
        # 1. Leer la imagen
        contenido_imagen = await file.read()

        # 2. Subir imagen a AWS S3
        s3_client.put_object(Bucket=BUCKET_NAME, Key=file.filename, Body=contenido_imagen)

        # 3. Analizar imagen con Amazon Rekognition
        respuesta = rekognition_client.detect_labels(
            Image={'S3Object': {'Bucket': BUCKET_NAME, 'Name': file.filename}},
            MaxLabels=5,
            MinConfidence=80.0
        )

        # 4. Extraer etiquetas
        etiquetas = [label['Name'] for label in respuesta['Labels']]
        etiquetas_str = ", ".join(etiquetas)

        # 5. Guardar resultados en Base de Datos
        conn = sqlite3.connect('fastretail.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO clasificaciones (nombre_archivo, etiquetas) VALUES (?, ?)",
                       (file.filename, etiquetas_str))
        conn.commit()
        conn.close()

        return {
            "mensaje": "Clasificación exitosa",
            "archivo": file.filename,
            "etiquetas_detectadas": etiquetas
        }

    except Exception as e:
        return {"error": str(e)}