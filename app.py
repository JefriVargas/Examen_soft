
from typing import Optional
from baseDatos.conexionDB import connect,cur
from fastapi.responses import JSONResponse
import json
from datetime import datetime
from fastapi import status
from psycopg2 import DatabaseError

from fastapi import FastAPI, HTTPException
from typing import List


app = FastAPI()

@app.get('/')
def funciona():
    return{"hola, chau"}

@app.get("/usuarios")
def listar_usuarios():
    cur.execute("SELECT alias, nombre FROM usuarios;")
    rows = cur.fetchall()
    return [{"alias": a, "nombre": n} for (a, n) in rows]


@app.get("/usuarios/{alias}")
def get_usuario(alias: str):
    cur.execute("SELECT alias, nombre FROM usuarios WHERE alias = %s;", (alias,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    a, n = row
    return {"alias": a, "nombre": n}

@app.get("/usuarios/{alias}/rides")
def listar_rides(alias: str):
    # Primero verificamos que el usuario exista:
    cur.execute("SELECT 1 FROM usuarios WHERE alias = %s;", (alias,))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    cur.execute("""
        SELECT id, rideDateAndTime, finalAddress, driver, status
          FROM rides
         WHERE driver = %s;
    """, (alias,))
    rides = cur.fetchall()
    if not rides:
        raise HTTPException(status_code=404, detail="El usuario no tiene rides registrados")

    return [
        {
            "id":      r[0],
            "rideDateAndTime": r[1].strftime("%Y/%m/%d %H:%M"),
            "finalAddress":    r[2],
            "driver":          r[3],
            "status":          r[4],
        }
        for r in rides
    ]
    
