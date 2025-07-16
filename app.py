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

    
@app.get("/usuarios/{alias}/rides/{rideid}")
def detalle_ride(alias: str, rideid: int):
    # 1) Validar usuario
    cur.execute("SELECT 1 FROM usuarios WHERE alias = %s;", (alias,))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # 2) Obtener datos del ride
    cur.execute("""
        SELECT id, rideDateAndTime, finalAddress, driver, status, capacity
          FROM rides
         WHERE driver = %s AND id = %s;
    """, (alias, rideid))
    fila = cur.fetchone()
    if not fila:
        raise HTTPException(status_code=404, detail="Ride no encontrado para el usuario")

    id_, dt, addr, drv, st, cap = fila

    # 3) Obtener participantes con sus estadísticas previas
    cur.execute("""
        SELECT
          rp.participant,
          rp.confirmation,
          rp.destination,
          rp.occupiedSpaces,
          rp.status,
          COUNT(*) FILTER (
            WHERE r2.rideDateAndTime < %s
          ) AS previousRidesTotal,
          COUNT(*) FILTER (
            WHERE r2.rideDateAndTime < %s AND rp2.status = 'completed'
          ) AS previousRidesCompleted,
          COUNT(*) FILTER (
            WHERE r2.rideDateAndTime < %s AND rp2.status = 'missing'
          ) AS previousRidesMissing,
          COUNT(*) FILTER (
            WHERE r2.rideDateAndTime < %s AND rp2.status = 'waiting'
          ) AS previousRidesNotMarked,
          COUNT(*) FILTER (
            WHERE r2.rideDateAndTime < %s AND rp2.status = 'rejected'
          ) AS previousRidesRejected
        FROM ride_participants rp
        JOIN rides r2 ON rp.ride_id = r2.id
        LEFT JOIN ride_participants rp2
          ON rp.participant = rp2.participant
        WHERE rp.ride_id = %s
        GROUP BY rp.participant, rp.confirmation, rp.destination,
                 rp.occupiedSpaces, rp.status;
    """, (dt, dt, dt, dt, dt, rideid))

    participantes = []
    for part, conf, dest, occ, estado, tot, comp, miss, notm, rej in cur.fetchall():
        participantes.append({
            "confirmation": conf,
            "participant": {
                "alias": part,
                "previousRidesTotal": tot,
                "previousRidesCompleted": comp,
                "previousRidesMissing": miss,
                "previousRidesNotMarked": notm,
                "previousRidesRejected": rej
            },
            "destination": dest,
            "occupiedSpaces": occ,
            "status": estado
        })

    # 4) Construir la respuesta
    return {
        "ride": {
            "id": id_,
            "rideDateAndTime": dt.strftime("%Y/%m/%d %H:%M"),
            "finalAddress": addr,
            "driver": drv,
            "status": st,
            "capacity": cap,
            "participants": participantes
        }
    }


def valida_ride_y_usuario(driver: str, rideid: int, alias: Optional[str] = None):
    # helper para POST: chequear driver existe, ride existe, y opcionalmente que participant exista
    cur.execute("SELECT 1 FROM usuarios WHERE alias = %s;", (driver,))
    if not cur.fetchone():
        raise HTTPException(404, "Driver no encontrado")

    cur.execute("SELECT capacity, status FROM rides WHERE id = %s AND driver = %s;", (rideid, driver))
    ride = cur.fetchone()
    if not ride:
        raise HTTPException(404, "Ride no encontrado para el driver")
    capacity, status = ride

    if alias:
        cur.execute("SELECT 1 FROM usuarios WHERE alias = %s;", (alias,))
        if not cur.fetchone():
            raise HTTPException(404, "Usuario participante no existe")

    return capacity, status


@app.post("/usuarios/{driver}/rides/{rideid}/requestToJoin/{alias}")
def request_to_join(driver: str, rideid: int, alias: str, destino: str, spaces: int):
    # 1) Validar ride, driver y participant
    capacity, status_ride = valida_ride_y_usuario(driver, rideid, alias)
    if status_ride != "ready":
        raise HTTPException(422, "El ride no está abierto para unirse")

    # 2) Verificar que no esté ya en la lista
    cur.execute("SELECT 1 FROM ride_participants WHERE ride_id=%s AND participant=%s;", (rideid, alias))
    if cur.fetchone():
        raise HTTPException(422, "Ya solicitó unirse a este ride")

    # 3) Espacios disponibles
    cur.execute("SELECT COALESCE(SUM(occupiedSpaces),0) FROM ride_participants WHERE ride_id=%s;", (rideid,))
    used = cur.fetchone()[0]
    if used + spaces > capacity:
        raise HTTPException(422, "No hay asientos suficientes")

    # 4) Insertar solicitud
    try:
        cur.execute("""
            INSERT INTO ride_participants(ride_id, participant, confirmation, destination, occupiedSpaces, status)
            VALUES (%s,%s,NULL,%s,%s,'waiting');
        """, (rideid, alias, destino, spaces))
        connect.commit()
    except DatabaseError as e:
        connect.rollback()
        raise HTTPException(500, str(e))

    return JSONResponse(status_code=201, content={"detail": "Solicitud enviada"})


@app.post("/usuarios/{driver}/rides/{rideid}/accept/{alias}")
def accept_participante(driver: str, rideid: int, alias: str):
    capacity, status_ride = valida_ride_y_usuario(driver, rideid)
    if status_ride != "ready":
        raise HTTPException(422, "No se puede aceptar, ride no está 'ready'")

    # Obtener espacios que solicitó
    cur.execute("""
        SELECT occupiedSpaces, confirmation
          FROM ride_participants
         WHERE ride_id=%s AND participant=%s;
    """, (rideid, alias))
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Participante no encontró la solicitud")
    spaces, conf = row
    if conf is True:
        raise HTTPException(422, "Ya fue aceptado")
    # Verificar cupos
    cur.execute("SELECT COALESCE(SUM(occupiedSpaces),0) FROM ride_participants WHERE ride_id=%s AND confirmation = true;", (rideid,))
    used = cur.fetchone()[0]
    if used + spaces > capacity:
        raise HTTPException(422, "No hay asientos suficientes para aceptar")

    cur.execute("""
        UPDATE ride_participants
           SET confirmation = TRUE, status = 'confirmed'
         WHERE ride_id=%s AND participant=%s;
    """, (rideid, alias))
    connect.commit()
    return {"detail": "Participante aceptado"}


@app.post("/usuarios/{driver}/rides/{rideid}/reject/{alias}")
def reject_participante(driver: str, rideid: int, alias: str):
    _, status_ride = valida_ride_y_usuario(driver, rideid)
    if status_ride != "ready":
        raise HTTPException(422, "No se puede rechazar, ride no está 'ready'")

    cur.execute("""
        UPDATE ride_participants
           SET confirmation = FALSE, status = 'rejected'
         WHERE ride_id=%s AND participant=%s
           AND confirmation IS NULL;
    """, (rideid, alias))
    if cur.rowcount == 0:
        raise HTTPException(422, "No hay solicitud pendiente para rechazar")
    connect.commit()
    return {"detail": "Participante rechazado"}


@app.post("/usuarios/{driver}/rides/{rideid}/start")
def start_ride(driver: str, rideid: int):
    _, status_ride = valida_ride_y_usuario(driver, rideid)
    if status_ride != "ready":
        raise HTTPException(422, "Solo se puede arrancar un ride en estado 'ready'")

    # Al menos un participante confirmado
    cur.execute("""
        SELECT 1 FROM ride_participants
         WHERE ride_id=%s AND confirmation = TRUE;
    """, (rideid,))
    if not cur.fetchone():
        raise HTTPException(422, "No hay participantes aceptados para arrancar")

    cur.execute("UPDATE rides SET status = 'in_progress' WHERE id = %s;", (rideid,))
    connect.commit()
    return {"detail": "Ride iniciado"}


@app.post("/usuarios/{driver}/rides/{rideid}/end")
def end_ride(driver: str, rideid: int):
    _, status_ride = valida_ride_y_usuario(driver, rideid)
    if status_ride != "in_progress":
        raise HTTPException(422, "Solo se puede terminar un ride en estado 'in_progress'")

    cur.execute("UPDATE rides SET status = 'completed' WHERE id = %s;", (rideid,))
    connect.commit()
    return {"detail": "Ride finalizado"}


@app.post("/usuarios/{driver}/rides/{rideid}/unloadParticipant/{alias}")
def unload_participant(driver: str, rideid: int, alias: str):
    _, status_ride = valida_ride_y_usuario(driver, rideid)
    if status_ride != "in_progress":
        raise HTTPException(422, "Solo se pueden descargar pasajeros en un ride en curso")

    cur.execute("""
        UPDATE ride_participants
           SET status = 'unloaded'
         WHERE ride_id=%s AND participant=%s
           AND confirmation = TRUE
           AND status = 'in_progress';
    """, (rideid, alias))
    if cur.rowcount == 0:
        raise HTTPException(422, "El participante no está en ruta o ya fue descargado")
    connect.commit()
    return {"detail": "Participante descargado"}