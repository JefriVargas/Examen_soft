import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import app  # Ajusta este import al nombre de tu módulo principal

# Dobles para simular cursor y conexión
class DummyCursor:
    def __init__(self):
        self.fetchone_results = []
        self.fetchall_results = []
        self.executed = []

    def execute(self, sql, params=None):
        # Registramos la consulta para posibles inspecciones
        self.executed.append((sql, params))

    def fetchone(self):
        return self.fetchone_results.pop(0) if self.fetchone_results else None

    def fetchall(self):
        return self.fetchall_results

class DummyConnect:
    def commit(self): pass
    def rollback(self): pass

@pytest.fixture(autouse=True)
def override_db(monkeypatch):
    """
    Reemplaza cur y connect del módulo principal por dobles.
    """
    stub_cur = DummyCursor()
    stub_conn = DummyConnect()
    monkeypatch.setattr(app, 'cur', stub_cur)
    monkeypatch.setattr(app, 'connect', stub_conn)
    return stub_cur

client = TestClient(app.app)

# ——— PRUEBAS UNITARIAS ———

# 1. GET /usuarios/{alias} - éxito

def test_get_usuario_success(override_db):
    """
    Caso de ÉXITO: /usuarios/{alias} devuelve 200 y datos correctos.
    """
    # Preparamos el stub para devolver un usuario
    override_db.fetchone_results = [('juan123','Juan Pérez')]
    response = client.get('/usuarios/juan123')
    assert response.status_code == 200
    assert response.json() == {'alias':'juan123','nombre':'Juan Pérez'}

# 2. GET /usuarios/{alias} - error 404

def test_get_usuario_not_found(override_db):
    """
    Caso de ERROR: alias inexistente -> 404.
    """
    override_db.fetchone_results = [None]
    response = client.get('/usuarios/noexiste')
    assert response.status_code == 404
    assert response.json()['detail'] == 'Usuario no encontrado'

# 3. GET /usuarios/{alias}/rides - error usuario no existe

def test_listar_rides_user_not_found(override_db):
    """
    Caso de ERROR: /usuarios/{alias}/rides con usuario inexistente -> 404.
    """
    override_db.fetchone_results = [None]  # validación SELECT 1
    response = client.get('/usuarios/pepito/rides')
    assert response.status_code == 404
    assert response.json()['detail'] == 'Usuario no encontrado'

# 4. GET /usuarios/{alias}/rides - éxito

def test_listar_rides_success(override_db):
    """
    Caso de ÉXITO: lista de rides para usuario existente.
    """
    dt = datetime(2025,7,20,14,30)
    override_db.fetchone_results = [(1,)]  # validación SELECT 1
    override_db.fetchall_results = [  
        (1, dt, 'Av X 123', 4, 'juan123', 'ready')
    ]
    response = client.get('/usuarios/juan123/rides')
    assert response.status_code == 200
    expected = [{
        'id': 1,
        'rideDateAndTime': '2025/07/20 14:30',
        'finalAddress': 'Av X 123',
        'allowedSpaces': 4,
        'rideDriver': 'juan123',
        'status': 'ready'
    }]
    assert response.json() == expected
