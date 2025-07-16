from conexionDB import cur

# Impresión de datos de cada DB

cur.execute('SELECT * FROM usuarios;')

data = cur.fetchall()

for entry in data:
    print(entry)
print(" ")

cur.execute('SELECT * FROM rides;')

data = cur.fetchall()

for entry in data:
    print(entry)
print(" ")

cur.execute('SELECT * FROM rideParticipations;')

data = cur.fetchall()

for entry in data:
    print(entry)
print(" ")