from conexionDB import cur, connect
from datetime import datetime, timedelta

# Insertar datos en tabla usuarios

usuarios = [
    # 5 originales
    ('jperez', 'Juan Pérez', 'ABC123'),
    ('lgomez', 'Laura Gómez', None),
    ('mmartinez', 'Marcos Martínez', 'XYZ987'),
    ('krojas', 'Karen Rojas', None),
    ('pquintero', 'Pedro Quintero', 'LMN456'),

    # 15 nuevos
    ('cvaldez', 'Carla Valdez', 'QWE789'),
    ('rhernandez', 'Ricardo Hernández', None),
    ('jlopez', 'Jorge López', 'JKL321'),
    ('mpalacios', 'María Palacios', None),
    ('avargas', 'Andrés Vargas', 'POI654'),
    ('sramirez', 'Sandra Ramírez', None),
    ('gmendoza', 'Gustavo Mendoza', 'MNB987'),
    ('vfernandez', 'Valeria Fernández', None),
    ('dmorales', 'Diego Morales', 'HGF432'),
    ('emartin', 'Elena Martín', None),
    ('tcastillo', 'Tomás Castillo', 'VBN567'),
    ('lreyes', 'Liliana Reyes', None),
    ('ojimenez', 'Oscar Jiménez', 'CVB210'),
    ('yrodriguez', 'Yolanda Rodríguez', None),
    ('fgarcia', 'Felipe García', 'ZXC765')
]

for alias, nombre, carPlate in usuarios:
    cur.execute("""
        INSERT INTO usuarios (alias, nombre, carPlate) VALUES (%s, %s, %s);
    """, (alias, nombre, carPlate))


# Insertar datos en tabla rides

rides = [
    (datetime.now() + timedelta(days=1), "Av Javier Prado 456, San Borja", 3, 'jperez', 'ready'),
    (datetime.now() + timedelta(days=2), "Av Brasil 1234, Lima", 2, 'mmartinez', 'ready'),
    (datetime.now() + timedelta(days=3), "Av La Marina 789, San Miguel", 4, 'cvaldez', 'ready'),
    (datetime.now() + timedelta(days=4), "Av Benavides 555, Miraflores", 3, 'jlopez', 'ready')
]

for rideDateAndTime, finalAddress, allowedSpaces, rideDriver, status in rides:
    cur.execute("""
        INSERT INTO rides (rideDateAndTime, finalAddress, allowedSpaces, rideDriver, status)
        VALUES (%s, %s, %s, %s, %s);
    """, (rideDateAndTime, finalAddress, allowedSpaces, rideDriver, status))


# Obtener IDs generados en rides para rideParticipations
cur.execute("SELECT id FROM rides;")
rides_ids = [row[0] for row in cur.fetchall()]

# Insertar datos en rideParticipations
ride_participations = [
    # rideId, participant, confirmation, destination, occupiedSpaces, status
    (rides_ids[0], 'lgomez', None, "Av Aramburú 245, Surquillo", 1, 'waiting'),
    (rides_ids[0], 'krojas', None, "Av Canadá 333, La Victoria", 1, 'waiting'),
    (rides_ids[1], 'pquintero', None, "Av La Marina 999, San Miguel", 1, 'waiting'),
    (rides_ids[2], 'rhernandez', None, "Av Angamos 321, Surquillo", 1, 'waiting'),
    (rides_ids[2], 'mpalacios', None, "Av Arequipa 678, Lima", 1, 'waiting'),
    (rides_ids[2], 'avargas', None, "Av Venezuela 123, Breña", 1, 'waiting'),
    (rides_ids[3], 'sramirez', None, "Av Ricardo Palma 456, Miraflores", 1, 'waiting'),
    (rides_ids[3], 'gmendoza', None, "Av 28 de Julio 789, Miraflores", 1, 'waiting'),
    (rides_ids[3], 'vfernandez', None, "Av Reducto 234, Miraflores", 1, 'waiting')
]

for rideId, participant, confirmation, destination, occupiedSpaces, status in ride_participations:
    cur.execute("""
        INSERT INTO rideParticipations (rideId, participant, confirmation, destination, occupiedSpaces, status)
        VALUES (%s, %s, %s, %s, %s, %s);
    """, (rideId, participant, confirmation, destination, occupiedSpaces, status))


# Confirmar cambios en la base de datos
connect.commit()
