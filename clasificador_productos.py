from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
import boto3
import sqlite3

app = FastAPI()

AWS_REGION = 'us-east-1'
BUCKET_NAME = 'fastretail-imagenes-catalogo'
s3_client = boto3.client('s3', region_name=AWS_REGION)
rekognition_client = boto3.client('rekognition', region_name=AWS_REGION)


def init_db():
    conn = sqlite3.connect('fastretail.db')
    cursor = conn.cursor()
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS classifications
                   (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       file_name TEXT,
                       labels TEXT
                   )
                   ''')
    conn.commit()
    conn.close()


init_db()


@app.get("/", response_class=HTMLResponse)
async def index():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>FastRetail</title>
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
            <form action="/classify/" enctype="multipart/form-data" method="post">
                <input name="file" type="file" required accept="image/jpeg, image/png">
                <button type="submit">Analizar Imagen</button>
            </form>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.post("/classify/")
async def classify_image(file: UploadFile = File(...)):
    try:
        image_content = await file.read()

        s3_client.put_object(Bucket=BUCKET_NAME, Key=file.filename, Body=image_content)

        response = rekognition_client.detect_labels(
            Image={'S3Object': {'Bucket': BUCKET_NAME, 'Name': file.filename}},
            MaxLabels=5,
            MinConfidence=80.0
        )

        labels = [label['Name'] for label in response['Labels']]
        labels_str = ", ".join(labels)

        conn = sqlite3.connect('fastretail.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO classifications (file_name, labels) VALUES (?, ?)",
                       (file.filename, labels_str))
        conn.commit()
        conn.close()

        return {
            "mensaje": "Clasificación exitosa",
            "archivo": file.filename,
            "etiquetas_detectadas": labels
        }

    except Exception as e:
        return {"error": str(e)}
