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
    try:
        # 1) Validar que el usuario existe
        cur.execute("SELECT 1 FROM usuarios WHERE alias = %s;", (alias,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        # 2) Obtener los rides usando las columnas correctas
        cur.execute("""
            SELECT
                id,
                rideDateAndTime,
                finalAddress,
                allowedSpaces,
                rideDriver,
                status
            FROM rides
            WHERE rideDriver = %s
            ORDER BY rideDateAndTime DESC;
        """, (alias,))
        filas = cur.fetchall()

    except DatabaseError as e:
        connect.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error de base de datos al listar rides: {e.pgerror or str(e)}"
        )

    # 3) Si no hay rides, devolvemos lista vacía
    if not filas:
        return []

    # 4) Construir la respuesta usando los nuevos campos
    return [
        {
            "id":               r[0],
            "rideDateAndTime":  r[1].strftime("%Y/%m/%d %H:%M"),
            "finalAddress":     r[2],
            "allowedSpaces":    r[3],
            "rideDriver":       r[4],
            "status":           r[5]
        }
        for r in filas
    ]
    

@app.get("/usuarios/{alias}/rides/{rideid}")
def detalle_ride(alias: str, rideid: int):
    try:
        # 1) Validar que el usuario existe
        cur.execute("SELECT 1 FROM usuarios WHERE alias = %s;", (alias,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        # 2) Obtener datos del ride (nombres de columna actualizados)
        cur.execute("""
            SELECT
                id,
                rideDateAndTime,
                finalAddress,
                allowedSpaces,
                rideDriver,
                status
            FROM rides
            WHERE rideDriver = %s AND id = %s;
        """, (alias, rideid))
        ride = cur.fetchone()
        if not ride:
            raise HTTPException(status_code=404, detail="Ride no encontrado para el usuario")

        id_, dt, addr, spaces, drv, st = ride

        # 3) Obtener participantes y sus estadísticas previas
        cur.execute("""
            SELECT
                rp.participant,
                rp.confirmation,
                rp.destination,
                rp.occupiedSpaces,
                rp.status,
                -- Totales previos antes de dt:
                (SELECT COUNT(*)
                   FROM rideParticipations rp2
                   JOIN rides r2 ON rp2.rideId = r2.id
                  WHERE rp2.participant = rp.participant
                    AND r2.rideDateAndTime < %s
                ) AS previousRidesTotal,
                (SELECT COUNT(*)
                   FROM rideParticipations rp2
                   JOIN rides r2 ON rp2.rideId = r2.id
                  WHERE rp2.participant = rp.participant
                    AND r2.rideDateAndTime < %s
                    AND rp2.status = 'done'
                ) AS previousRidesCompleted,
                (SELECT COUNT(*)
                   FROM rideParticipations rp2
                   JOIN rides r2 ON rp2.rideId = r2.id
                  WHERE rp2.participant = rp.participant
                    AND r2.rideDateAndTime < %s
                    AND rp2.status = 'missing'
                ) AS previousRidesMissing,
                (SELECT COUNT(*)
                   FROM rideParticipations rp2
                   JOIN rides r2 ON rp2.rideId = r2.id
                  WHERE rp2.participant = rp.participant
                    AND r2.rideDateAndTime < %s
                    AND rp2.status = 'notmarked'
                ) AS previousRidesNotMarked,
                (SELECT COUNT(*)
                   FROM rideParticipations rp2
                   JOIN rides r2 ON rp2.rideId = r2.id
                  WHERE rp2.participant = rp.participant
                    AND r2.rideDateAndTime < %s
                    AND rp2.status = 'rejected'
                ) AS previousRidesRejected
            FROM rideParticipations rp
           WHERE rp.rideId = %s;
        """, (dt, dt, dt, dt, dt, rideid))

        participantes = []
        for (part, conf_ts, dest, occ, estado,
             tot, comp, miss, notm, rej) in cur.fetchall():
            participantes.append({
                "confirmation": conf_ts,      # Timestamp de confirmación o null
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

    except DatabaseError as e:
        connect.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error de base de datos al obtener detalle de ride: {e.pgerror or str(e)}"
        )

    # 4) Armar y devolver la respuesta
    return {
        "ride": {
            "id": id_,
            "rideDateAndTime": dt.strftime("%Y/%m/%d %H:%M"),
            "finalAddress": addr,
            "rideDriver": drv,
            "status": st,
            "allowedSpaces": spaces,
            "participants": participantes
        }
    }


def valida_ride_y_usuario(driver: str, rideid: int, alias: Optional[str] = None):
    # Comprueba que driver y ride existen, y opcionalmente que el participant existe
    cur.execute("SELECT 1 FROM usuarios WHERE alias = %s;", (driver,))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Driver no encontrado")

    cur.execute("""
        SELECT allowedSpaces, status
          FROM rides
         WHERE id = %s AND rideDriver = %s;
    """, (rideid, driver))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Ride no encontrado para el driver")
    allowed_spaces, status_ride = row

    if alias:
        cur.execute("SELECT 1 FROM usuarios WHERE alias = %s;", (alias,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Usuario participante no existe")

    return allowed_spaces, status_ride


@app.api_route("/usuarios/{driver}/rides/{rideid}/requestToJoin/{alias}", methods=["GET", "POST"])
def request_to_join(driver: str, rideid: int, alias: str, destino: str, spaces: int):
    try:
        allowed_spaces, status_ride = valida_ride_y_usuario(driver, rideid, alias)
        if status_ride != "ready":
            raise HTTPException(status_code=422, detail="El ride no está abierto para unirse")

        # 2) Verificar que no esté ya en la lista
        cur.execute("""
            SELECT 1
              FROM rideParticipations
             WHERE rideId = %s AND participant = %s;
        """, (rideid, alias))
        if cur.fetchone():
            raise HTTPException(status_code=422, detail="Ya solicitó unirse a este ride")

        # 3) Espacios disponibles
        cur.execute("""
            SELECT COALESCE(SUM(occupiedSpaces),0)
              FROM rideParticipations
             WHERE rideId = %s;
        """, (rideid,))
        used = cur.fetchone()[0]
        if used + spaces > allowed_spaces:
            raise HTTPException(status_code=422, detail="No hay asientos suficientes")

        # 4) Insertar solicitud
        cur.execute("""
            INSERT INTO rideParticipations
                (rideId, participant, confirmation, destination, occupiedSpaces, status)
            VALUES (%s, %s, NULL, %s, %s, 'waiting');
        """, (rideid, alias, destino, spaces))
        connect.commit()
        return JSONResponse(status_code=201, content={"detail": "Solicitud enviada"})

    except DatabaseError as e:
        connect.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error de base de datos al solicitar unirse: {e.pgerror or str(e)}"
        )


@app.api_route("/usuarios/{driver}/rides/{rideid}/accept/{alias}", methods=["GET", "POST"])
def accept_participante(driver: str, rideid: int, alias: str):
    try:
        allowed_spaces, status_ride = valida_ride_y_usuario(driver, rideid)
        if status_ride != "ready":
            raise HTTPException(status_code=422, detail="No se puede aceptar, ride no está 'ready'")

        # Obtener espacios solicitados y estado
        cur.execute("""
            SELECT occupiedSpaces, confirmation
              FROM rideParticipations
             WHERE rideId = %s AND participant = %s;
        """, (rideid, alias))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Participante no encontró la solicitud")
        spaces, confirmation_ts = row

        if confirmation_ts is not None:
            raise HTTPException(status_code=422, detail="Ya fue procesada la solicitud")

        # Verificar cupos confirmados
        cur.execute("""
            SELECT COALESCE(SUM(occupiedSpaces),0)
              FROM rideParticipations
             WHERE rideId = %s AND status = 'confirmed';
        """, (rideid,))
        used = cur.fetchone()[0]
        if used + spaces > allowed_spaces:
            raise HTTPException(status_code=422, detail="No hay asientos suficientes para aceptar")

        cur.execute("""
            UPDATE rideParticipations
               SET status = 'confirmed',
                   confirmation = NOW()
             WHERE rideId = %s AND participant = %s;
        """, (rideid, alias))
        connect.commit()
        return {"detail": "Participante aceptado"}

    except DatabaseError as e:
        connect.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error de base de datos al aceptar participante: {e.pgerror or str(e)}"
        )


@app.api_route("/usuarios/{driver}/rides/{rideid}/reject/{alias}", methods=["GET", "POST"])
def reject_participante(driver: str, rideid: int, alias: str):
    try:
        _, status_ride = valida_ride_y_usuario(driver, rideid)
        if status_ride != "ready":
            raise HTTPException(status_code=422, detail="No se puede rechazar, ride no está 'ready'")

        cur.execute("""
            UPDATE rideParticipations
               SET status = 'rejected',
                   confirmation = NOW()
             WHERE rideId = %s
               AND participant = %s
               AND status = 'waiting';
        """, (rideid, alias))

        if cur.rowcount == 0:
            raise HTTPException(status_code=422, detail="No hay solicitud pendiente para rechazar")
        connect.commit()
        return {"detail": "Participante rechazado"}

    except DatabaseError as e:
        connect.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error de base de datos al rechazar participante: {e.pgerror or str(e)}"
        )


@app.api_route("/usuarios/{driver}/rides/{rideid}/start", methods=["GET", "POST"])
def start_ride(driver: str, rideid: int):
    try:
        _, status_ride = valida_ride_y_usuario(driver, rideid)
        if status_ride != "ready":
            raise HTTPException(status_code=422, detail="Solo se puede arrancar un ride en estado 'ready'")

        # Al menos un participante confirmado
        cur.execute("""
            SELECT 1
              FROM rideParticipations
             WHERE rideId = %s AND status = 'confirmed';
        """, (rideid,))
        if not cur.fetchone():
            raise HTTPException(status_code=422, detail="No hay participantes aceptados para arrancar")

        cur.execute("""
            UPDATE rides
               SET status = 'inprogress'
             WHERE id = %s;
        """, (rideid,))
        connect.commit()
        return {"detail": "Ride iniciado"}

    except DatabaseError as e:
        connect.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error de base de datos al iniciar ride: {e.pgerror or str(e)}"
        )


@app.api_route("/usuarios/{driver}/rides/{rideid}/end", methods=["GET", "POST"])
def end_ride(driver: str, rideid: int):
    try:
        _, status_ride = valida_ride_y_usuario(driver, rideid)
        if status_ride != "inprogress":
            raise HTTPException(status_code=422, detail="Solo se puede terminar un ride en estado 'inprogress'")

        cur.execute("""
            UPDATE rides
               SET status = 'done'
             WHERE id = %s;
        """, (rideid,))
        connect.commit()
        return {"detail": "Ride finalizado"}

    except DatabaseError as e:
        connect.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error de base de datos al terminar ride: {e.pgerror or str(e)}"
        )


@app.api_route("/usuarios/{driver}/rides/{rideid}/unloadParticipant/{alias}", methods=["GET", "POST"])
def unload_participant(driver: str, rideid: int, alias: str):
    
    try:
        _, status_ride = valida_ride_y_usuario(driver, rideid)
        if status_ride != "inprogress":
            raise HTTPException(status_code=422, detail="Solo se pueden descargar pasajeros en un ride en curso")

        cur.execute("""
            UPDATE rideParticipations
               SET status = 'done'
             WHERE rideId = %s
               AND participant = %s
               AND status = 'inprogress';
        """, (rideid, alias))

        if cur.rowcount == 0:
            raise HTTPException(status_code=422, detail="El participante no está en ruta o ya fue descargado")
        connect.commit()
        return {"detail": "Participante descargado"}

    except DatabaseError as e:
        connect.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error de base de datos al descargar participante: {e.pgerror or str(e)}"
        )