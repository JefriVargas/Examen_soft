from conexionDB import cur, connect

cur.execute(""" 
    DROP TABLE IF EXISTS usuarios CASCADE;
""")

cur.execute(""" 
    DROP TABLE IF EXISTS rides CASCADE;
""")

cur.execute(""" 
    DROP TABLE IF EXISTS rideParticipations CASCADE;
""")

connect.commit()