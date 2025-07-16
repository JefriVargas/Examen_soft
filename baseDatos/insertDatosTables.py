from conexionDB import cur, connect
from datetime import datetime, timedelta

# Insertar datos en tabla usuarios

usuarios = [
    ('jperez', 'Juan Pérez', 'ABC123'),
    ('lgomez', 'Laura Gómez', None),
    ('mmartinez', 'Marcos Martínez', 'XYZ987'),
    ('krojas', 'Karen Rojas', None),
    ('pquintero', 'Pedro Quintero', 'LMN456')
]

for alias, nombre, carPlate in usuarios:
    cur.execute("""
        INSERT INTO usuarios (alias, nombre, carPlate) VALUES (%s, %s, %s);
    """, (alias, nombre, carPlate))

# Insertar datos en tabla rides

rides = [
    (datetime.now() + timedelta(days=1), "Av Javier Prado 456, San Borja", 3, 'jperez', 'ready'),
    (datetime.now() + timedelta(days=2), "Av Brasil 1234, Lima", 2, 'mmartinez', 'ready')
]

for rideDateAndTime, finalAddress, allowedSpaces, rideDriver, status in rides:
    cur.execute("""
        INSERT INTO rides (rideDateAndTime, finalAddress, allowedSpaces, rideDriver, status)
        VALUES (%s, %s, %s, %s, %s);
    """, (rideDateAndTime, finalAddress, allowedSpaces, rideDriver, status))

# Obtener IDs generados en rides para usarlos en rideParticipations
cur.execute("SELECT id, rideDriver FROM rides;")
rides_ids = cur.fetchall()  # lista de tuplas (id, rideDriver)

# Insertar datos en rideParticipations

ride_participations = [
    # rideId, participant, confirmation, destination, occupiedSpaces, status
    (rides_ids[0][0], 'lgomez', None, "Av Aramburú 245, Surquillo", 1, 'waiting'),
    (rides_ids[0][0], 'krojas', None, "Av Canadá 333, La Victoria", 1, 'waiting'),
    (rides_ids[1][0], 'pquintero', None, "Av La Marina 999, San Miguel", 1, 'waiting')
]

for rideId, participant, confirmation, destination, occupiedSpaces, status in ride_participations:
    cur.execute("""
        INSERT INTO rideParticipations (rideId, participant, confirmation, destination, occupiedSpaces, status)
        VALUES (%s, %s, %s, %s, %s, %s);
    """, (rideId, participant, confirmation, destination, occupiedSpaces, status))

# Confirmar cambios
connect.commit()
