import psycopg2 as pg2

# Conexión con la base de datos 
connect = pg2.connect(database = 'Software', user = 'postgres', password = 12345678, port = 5433)
cur = connect.cursor()
