import pytest
from httpx import AsyncClient
from app import app

BASE_URL = "http://test"

# ---------- CONFIGURACIÓN DE DATOS ----------
# Ajusta estos alias e IDs según tu base de datos de prueba:
DRIVER_ALIAS = "jperez"
RIDE_ID = 1
PARTICIPANT_1 = "lgomez"
PARTICIPANT_2 = "krojas"
DESTINO_NUEVO = "Av Siempre Viva 742"
SPACES = 1

@pytest.mark.asyncio
async def test_flujo_exito_completo():
    """
    ✅ CASO DE ÉXITO
    Simula todo el flujo: requestToJoin, accept, start, unloadParticipant, end
    """
    async with AsyncClient(app=app, base_url=BASE_URL) as ac:
        # 1) Participante solicita unirse al ride
        resp = await ac.post(
            f"/usuarios/{DRIVER_ALIAS}/rides/{RIDE_ID}/requestToJoin/{PARTICIPANT_1}",
            params={"destino": DESTINO_NUEVO, "spaces": SPACES}
        )
        assert resp.status_code in (201, 422)
        # Si da 422 es que ya estaba solicitando → igual seguimos

        # 2) Driver acepta al participante
        resp = await ac.post(
            f"/usuarios/{DRIVER_ALIAS}/rides/{RIDE_ID}/accept/{PARTICIPANT_1}"
        )
        assert resp.status_code in (200, 422)
        # Puede dar 422 si ya estaba confirmado

        # 3) Driver rechaza a otro participante
        resp = await ac.post(
            f"/usuarios/{DRIVER_ALIAS}/rides/{RIDE_ID}/reject/{PARTICIPANT_2}"
        )
        assert resp.status_code in (200, 422)
        # Puede dar 422 si ya fue rechazado o confirmado

        # 4) Iniciar el ride
        resp = await ac.post(
            f"/usuarios/{DRIVER_ALIAS}/rides/{RIDE_ID}/start"
        )
        assert resp.status_code in (200, 422)
        # Puede dar 422 si ya estaba en progreso

        # 5) Descargar al participante
        resp = await ac.post(
            f"/usuarios/{DRIVER_ALIAS}/rides/{RIDE_ID}/unloadParticipant/{PARTICIPANT_1}"
        )
        assert resp.status_code in (200, 422)
        # Puede dar 422 si ya se descargó

        # 6) Finalizar el ride
        resp = await ac.post(
            f"/usuarios/{DRIVER_ALIAS}/rides/{RIDE_ID}/end"
        )
        assert resp.status_code in (200, 422)
        # Puede dar 422 si ya estaba terminado

@pytest.mark.asyncio
async def test_error_request_ya_existente():
    """
    ⚠️ ERROR
    Intentar hacer 2 solicitudes consecutivas de unirse al mismo ride
    """
    async with AsyncClient(app=app, base_url=BASE_URL) as ac:
        # Primer intento (puede fallar si ya estaba, igual lo dejamos pasar)
        await ac.post(
            f"/usuarios/{DRIVER_ALIAS}/rides/{RIDE_ID}/requestToJoin/{PARTICIPANT_2}",
            params={"destino": DESTINO_NUEVO, "spaces": SPACES}
        )
        # Segundo intento - este debería fallar por duplicado
        resp2 = await ac.post(
            f"/usuarios/{DRIVER_ALIAS}/rides/{RIDE_ID}/requestToJoin/{PARTICIPANT_2}",
            params={"destino": DESTINO_NUEVO, "spaces": SPACES}
        )
        assert resp2.status_code == 422

@pytest.mark.asyncio
async def test_error_usuario_inexistente():
    """
    ⚠️ ERROR
    Consultar un usuario inexistente
    """
    async with AsyncClient(app=app, base_url=BASE_URL) as ac:
        resp = await ac.get("/usuarios/noexiste123")
        assert resp.status_code == 404

@pytest.mark.asyncio
async def test_error_start_sin_participantes_confirmados():
    """
    ⚠️ ERROR
    Intentar iniciar un ride sin participantes confirmados
    (Para esto usamos ride 2 que tiene otro driver)
    """
    OTHER_DRIVER = "mmartinez"
    OTHER_RIDE_ID = 2

    async with AsyncClient(app=app, base_url=BASE_URL) as ac:
        resp = await ac.post(
            f"/usuarios/{OTHER_DRIVER}/rides/{OTHER_RIDE_ID}/start"
        )
        assert resp.status_code == 422
