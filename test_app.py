# tests/test_app.py

import pytest
from fastapi.testclient import TestClient
from psycopg2 import DatabaseError
from datetime import datetime
import app  # Ajusta si tu módulo principal no se llama app.py

client = TestClient(app.app)


# ——— Dobles de base de datos —————————————————————————————————————————————————

class DummyCursor:
    def __init__(self):
        self.fetchone_results = []
        self.fetchall_results = []
        self.rowcount = 1  # necesario para endpoints que usan rowcount
    def execute(self, query, params=None):
        # Simula DatabaseError si está en to_raise
        if hasattr(self, "to_raise"):
            err = self.to_raise
            del self.to_raise
            raise err
    def fetchone(self):
        # Simula DatabaseError si está en to_raise
        if hasattr(self, "to_raise"):
            err = self.to_raise
            del self.to_raise
            raise err
        return self.fetchone_results.pop(0) if self.fetchone_results else None
    def fetchall(self):
        # Simula DatabaseError si está en to_raise
        if hasattr(self, "to_raise"):
            err = self.to_raise
            del self.to_raise
            raise err
        return self.fetchall_results.pop(0) if self.fetchall_results else []

class DummyConnect:
    def commit(self): pass
    def rollback(self): pass

@pytest.fixture(autouse=True)
def override_db(monkeypatch):
    """
    Parchea `app.cur` y `app.connect` antes de cada test
    para usar dobles en lugar de la base real.
    """
    cur = DummyCursor()
    conn = DummyConnect()
    monkeypatch.setattr(app, "cur", cur)
    monkeypatch.setattr(app, "connect", conn)
    return cur


# ————————————————————————————————————————————————————————————————————————————————————
# TESTS PARA GET /usuarios/{alias}
# ————————————————————————————————————————————————————————————————————————————————————

def test_get_usuario_success(override_db):
    """
    ÉXITO: /usuarios/{alias} devuelve 200 y los datos correctos.
    """
    override_db.fetchone_results = [("juan123", "Juan Pérez")]
    resp = client.get("/usuarios/juan123")
    assert resp.status_code == 200
    assert resp.json() == {"alias": "juan123", "nombre": "Juan Pérez"}


def test_get_usuario_not_found(override_db):
    """
    ERROR: alias no existe → 404 Usuario no encontrado.
    """
    override_db.fetchone_results = [None]
    resp = client.get("/usuarios/nadie")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Usuario no encontrado"


def test_get_usuario_db_error(override_db):
    """
    ERROR: DatabaseError en ejecución → 500 Internal Server Error.
    """
    override_db.to_raise = DatabaseError("boom")
    resp = client.get("/usuarios/juan123")
    assert resp.status_code == 500


def test_get_usuario_generic_error(override_db):
    """
    ERROR: excepción genérica no manejada → 500 Internal Server Error.
    """
    override_db.to_raise = Exception("ups")
    resp = client.get("/usuarios/juan123")
    assert resp.status_code == 500


# ————————————————————————————————————————————————————————————————————————————————————
# TESTS PARA GET /usuarios/{alias}/rides
# ————————————————————————————————————————————————————————————————————————————————————

def test_listar_rides_success(override_db):
    """
    ÉXITO: /usuarios/{alias}/rides devuelve lista de rides.
    """
    dt = datetime(2025, 7, 21, 15, 0)
    # 1) Validación de usuario
    override_db.fetchone_results = [(1,)]
    # 2) fetchall devuelve lista de rides
    override_db.fetchall_results = [[
        (42, dt, "Av Prueba 123", 4, "juan123", "ready")
    ]]
    resp = client.get("/usuarios/juan123/rides")
    assert resp.status_code == 200
    expected = [{
        "id": 42,
        "rideDateAndTime": dt.strftime("%Y/%m/%d %H:%M"),
        "finalAddress": "Av Prueba 123",
        "allowedSpaces": 4,
        "rideDriver": "juan123",
        "status": "ready"
    }]
    assert resp.json() == expected


def test_listar_rides_user_not_found(override_db):
    """
    ERROR: usuario no existe → 404 Usuario no encontrado.
    """
    override_db.fetchone_results = [None]
    resp = client.get("/usuarios/inexistente/rides")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Usuario no encontrado"


def test_listar_rides_db_error_validation(override_db):
    """
    ERROR: DatabaseError al validar usuario → 500 Internal Server Error.
    """
    override_db.to_raise = DatabaseError("err validar")
    resp = client.get("/usuarios/juan123/rides")
    assert resp.status_code == 500


def test_listar_rides_db_error_fetch(override_db):
    """
    ERROR: DatabaseError al traer rides → 500 Internal Server Error.
    """
    override_db.fetchone_results = [(1,)]
    override_db.to_raise = DatabaseError("err fetch")
    resp = client.get("/usuarios/juan123/rides")
    assert resp.status_code == 500


# ————————————————————————————————————————————————————————————————————————————————————
# TESTS PARA GET /usuarios/{alias}/rides/{rideid}
# ————————————————————————————————————————————————————————————————————————————————————

def test_detalle_ride_success(override_db):
    """
    ÉXITO: /usuarios/{alias}/rides/{rideid} devuelve datos de ride con participantes.
    """
    dt = datetime(2025, 7, 22, 18, 30)
    # 1) Usuario existe
    override_db.fetchone_results = [(1,)]
    # 2) Ride encontrado
    override_db.fetchone_results.append((99, dt, "Av Detalle 456", 2, "juan123", "ready"))
    # 3) Participantes
    override_db.fetchall_results = [[
        ("luna23", None, "Av Dest 1", 1, "waiting", 5, 3, 1, 1, 0)
    ]]

    resp = client.get("/usuarios/juan123/rides/99")
    assert resp.status_code == 200
    data = resp.json()["ride"]
    assert data["id"] == 99
    assert data["rideDriver"] == "juan123"
    assert data["allowedSpaces"] == 2
    parts = data["participants"]
    assert len(parts) == 1
    assert parts[0]["participant"]["alias"] == "luna23"


def test_detalle_ride_user_not_found(override_db):
    """
    ERROR: usuario no existe → 404 Usuario no encontrado.
    """
    override_db.fetchone_results = [None]
    resp = client.get("/usuarios/x/rides/1")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Usuario no encontrado"


def test_detalle_ride_not_found(override_db):
    """
    ERROR: ride no encontrado → 404 Ride no encontrado para el usuario.
    """
    dt = datetime(2025, 7, 22, 18, 30)
    override_db.fetchone_results = [(1,)]
    override_db.fetchone_results.append(None)
    resp = client.get("/usuarios/juan123/rides/1234")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Ride no encontrado para el usuario"


def test_detalle_ride_db_error(override_db):
    """
    ERROR: DatabaseError en SQL → 500 Internal Server Error.
    """
    override_db.to_raise = DatabaseError("boom detalle")
    resp = client.get("/usuarios/juan123/rides/1")
    assert resp.status_code == 500
