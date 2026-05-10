import time
import os
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Attr
from fastapi import FastAPI, HTTPException, Request
from prometheus_fastapi_instrumentator import Instrumentator
from dotenv import load_dotenv

load_dotenv()

APP_ENV = os.getenv("APP_ENV", "local")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
tabla_clientes = dynamodb.Table(os.getenv("TABLA_CLIENTES", "Clientes"))
tabla_productos = dynamodb.Table(os.getenv("TABLA_PRODUCTOS", "Productos"))
tabla_domicilios = dynamodb.Table(os.getenv("TABLA_DOMICILIOS", "Domicilios"))

app = FastAPI(title="Microservicio Catálogos", description=f"Ambiente actual: {APP_ENV}")

Instrumentator().instrument(app).expose(app)

def parse_decimals(obj):
    if isinstance(obj, list): return [parse_decimals(i) for i in obj]
    elif isinstance(obj, dict): return {k: parse_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal): return float(obj)
    return obj

# ==========================================
#          SECCIÓN: PRODUCTOS
# ==========================================
@app.post("/productos", status_code=201)
async def crear_producto(request: Request):
    try:
        body = await request.json()
        precio = body.get('Precio Base')
        if isinstance(precio, float): raise ValueError('El Precio Base no acepta centavos.')
        if not isinstance(precio, int) or precio <= 0: raise ValueError('Precio Base debe ser entero positivo.')
        
        nuevo_item = {'ID': int(time.time()), 'Nombre': body['Nombre'], 'Unidad de Medida': body['Unidad de Medida'], 'Precio Base': precio}
        tabla_productos.put_item(Item=nuevo_item)
        return {'mensaje': 'Producto creado', 'id': nuevo_item['ID'], 'ambiente': APP_ENV}
    except Exception as e: raise HTTPException(status_code=400, detail=str(e))

@app.get("/productos")
def obtener_productos():
    return parse_decimals(tabla_productos.scan().get('Items', []))

@app.get("/productos/{id}")
def obtener_producto_por_id(id: int):
    resp = tabla_productos.get_item(Key={'ID': id})
    if 'Item' in resp: return parse_decimals(resp['Item'])
    raise HTTPException(status_code=404, detail="Producto no encontrado")

@app.put("/productos/{id}")
async def actualizar_producto(id: int, request: Request):
    check = tabla_productos.get_item(Key={'ID': id})
    if 'Item' not in check: raise HTTPException(status_code=404, detail="Producto no encontrado")
    body = await request.json()
    item_actualizado = check['Item']
    item_actualizado.update(body)
    item_actualizado['ID'] = id
    tabla_productos.put_item(Item=item_actualizado)
    return {'mensaje': 'Producto actualizado', 'id': id}

@app.delete("/productos/{id}")
def eliminar_producto(id: int):
    check = tabla_productos.get_item(Key={'ID': id})
    if 'Item' not in check: raise HTTPException(status_code=404, detail="Producto no existe")
    tabla_productos.delete_item(Key={'ID': id})
    return {'mensaje': 'Producto eliminado exitosamente'}

# ==========================================
#          SECCIÓN: CLIENTES
# ==========================================
@app.post("/clientes", status_code=201)
async def crear_cliente(request: Request):
    body = await request.json()
    nuevo_item = {'ID': int(time.time()), 'Nombre': body['Nombre'], 'NComercial': body.get('NComercial', ''), 'RFC': body['RFC'], 'Correo': body['Correo'], 'Telefono': body.get('Telefono', 0)}
    tabla_clientes.put_item(Item=nuevo_item)
    return {'mensaje': 'Cliente registrado', 'id': nuevo_item['ID'], 'ambiente': APP_ENV}

@app.get("/clientes")
def obtener_clientes():
    return parse_decimals(tabla_clientes.scan().get('Items', []))

@app.get("/clientes/{id}")
def obtener_cliente_por_id(id: int):
    resp = tabla_clientes.get_item(Key={'ID': id})
    if 'Item' in resp: return parse_decimals(resp['Item'])
    raise HTTPException(status_code=404, detail="Cliente no encontrado")

@app.put("/clientes/{id}")
async def actualizar_cliente(id: int, request: Request):
    check = tabla_clientes.get_item(Key={'ID': id})
    if 'Item' not in check: raise HTTPException(status_code=404, detail="Cliente no encontrado")
    body = await request.json()
    item_actualizado = check['Item']
    item_actualizado.update(body)
    item_actualizado['ID'] = id
    tabla_clientes.put_item(Item=item_actualizado)
    return {'mensaje': 'Cliente actualizado', 'id': id}

@app.delete("/clientes/{id}")
def eliminar_cliente(id: int):
    check = tabla_clientes.get_item(Key={'ID': id})
    if 'Item' not in check: raise HTTPException(status_code=404, detail="Cliente no existe")
    tabla_clientes.delete_item(Key={'ID': id})
    return {'mensaje': 'Cliente eliminado'}

# ==========================================
#          SECCIÓN: DOMICILIOS
# ==========================================
@app.post("/domicilios", status_code=201)
async def crear_domicilio(request: Request):
    body = await request.json()
    cliente_id = body.get('ClienteID')
    if 'Item' not in tabla_clientes.get_item(Key={'ID': cliente_id}): raise HTTPException(status_code=404, detail="ClienteID no existe")
    nuevo_item = {'ID': int(time.time()), 'ClienteID': cliente_id, 'Domicilio': body['Domicilio'], 'Colonia': body['Colonia'], 'Municipio': body['Municipio'], 'Estado': body['Estado'], 'Tipo de Direccion': body['Tipo de Direccion']}
    tabla_domicilios.put_item(Item=nuevo_item)
    return {'mensaje': 'Domicilio creado', 'id': nuevo_item['ID']}

@app.get("/domicilios")
def obtener_domicilios():
    return parse_decimals(tabla_domicilios.scan().get('Items', []))

@app.get("/clientes/{id}/domicilios")
def obtener_domicilios_por_cliente(id: int):
    return parse_decimals(tabla_domicilios.scan(FilterExpression=Attr('ClienteID').eq(id)).get('Items', []))

@app.get("/domicilios/{id}")
def obtener_domicilio_por_id(id: int):
    resp = tabla_domicilios.get_item(Key={'ID': id})
    if 'Item' in resp: return parse_decimals(resp['Item'])
    raise HTTPException(status_code=404, detail="Domicilio no encontrado")

@app.put("/domicilios/{id}")
async def actualizar_domicilio(id: int, request: Request):
    check = tabla_domicilios.get_item(Key={'ID': id})
    if 'Item' not in check: raise HTTPException(status_code=404, detail="Domicilio no encontrado")
    body = await request.json()
    if 'ClienteID' in body: raise HTTPException(status_code=400, detail="No se puede modificar el ClienteID")
    item_actualizado = check['Item']
    item_actualizado.update(body)
    item_actualizado['ID'] = id
    tabla_domicilios.put_item(Item=item_actualizado)
    return {'mensaje': 'Domicilio actualizado exitosamente', 'id': id}

@app.delete("/domicilios/{id}")
def eliminar_domicilio(id: int):
    check = tabla_domicilios.get_item(Key={'ID': id})
    if 'Item' not in check: raise HTTPException(status_code=404, detail="Domicilio no existe")
    tabla_domicilios.delete_item(Key={'ID': id})
    return {'mensaje': 'Domicilio eliminado'}