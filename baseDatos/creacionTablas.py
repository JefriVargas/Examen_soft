from conexionDB import cur, connect

# creación de las tablas

# Tabla usuarios
cur.execute(""" 
    CREATE TABLE usuarios(
        alias VARCHAR(50) PRIMARY KEY NOT NULL,
        nombre VARCHAR(50) NOT NULL,
        carPlate VARCHAR(20)
    );
""")

# Tabla rides
cur.execute(""" 
    CREATE TABLE rides(
        id SERIAL PRIMARY KEY,
        rideDateAndTime TIMESTAMP NOT NULL,
        finalAddress VARCHAR(255) NOT NULL,
        allowedSpaces INT NOT NULL,
        rideDriver VARCHAR(50) NOT NULL,
        status VARCHAR(20) CHECK (status IN ('ready', 'inprogress', 'done')),
        FOREIGN KEY (rideDriver) REFERENCES usuarios(alias) ON DELETE CASCADE
    );
""")

# Tabla rideParticipations
cur.execute("""
    CREATE TABLE rideParticipations(
        id SERIAL PRIMARY KEY,
        rideId INT NOT NULL,
        participant VARCHAR(50) NOT NULL,
        confirmation TIMESTAMP,
        destination VARCHAR(255) NOT NULL,
        occupiedSpaces INT NOT NULL,
        status VARCHAR(20) CHECK (status IN (
            'waiting', 'rejected', 'confirmed', 
            'missing', 'notmarked', 'inprogress', 'done'
        )),
        FOREIGN KEY (rideId) REFERENCES rides(id) ON DELETE CASCADE,
        FOREIGN KEY (participant) REFERENCES usuarios(alias) ON DELETE CASCADE,
        UNIQUE (rideId, participant)
    );
""")

# confirmar acciones y registrarlo en la base de datos 
connect.commit()
