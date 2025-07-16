import pytest
from httpx import AsyncClient
from app import app

@pytest.mark.asyncio
async def test_flujo_exito_completo():
    """
    ✅ Caso de prueba de ÉXITO
    Flujo feliz: listar usuarios, obtener usuario, listar rides, detalle de ride
    * Se asume que hay datos cargados en la DB *
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # 1) Listar usuarios
        resp = await ac.get("/usuarios")
        assert resp.status_code == 200
        usuarios = resp.json()
        assert isinstance(usuarios, list)
        alias = usuarios[0]["alias"]

        # 2) Obtener detalle de usuario
        resp = await ac.get(f"/usuarios/{alias}")
        assert resp.status_code == 200
        assert resp.json()["alias"] == alias

        # 3) Listar rides del usuario
        resp = await ac.get(f"/usuarios/{alias}/rides")
        if resp.status_code == 404:
            pytest.skip("Usuario no tiene rides registrados")
        else:
            assert resp.status_code == 200
            rides = resp.json()
            ride_id = rides[0]["id"]

            # 4) Obtener detalle de un ride
            resp = await ac.get(f"/usuarios/{alias}/rides/{ride_id}")
            assert resp.status_code == 200
            ride_info = resp.json()["ride"]
            assert ride_info["id"] == ride_id

@pytest.mark.asyncio
async def test_error_usuario_no_existe():
    """
    ⚠️ Caso de ERROR
    Consultar datos de usuario inexistente
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.get("/usuarios/usuario_inexistente")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Usuario no encontrado"

@pytest.mark.asyncio
async def test_error_ride_no_existe():
    """
    ⚠️ Caso de ERROR
    Obtener detalle de ride que no existe para un driver existente
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        alias_valido = "jperez"  # asegúrate que existe
        ride_id_invalido = 99999
        resp = await ac.get(f"/usuarios/{alias_valido}/rides/{ride_id_invalido}")
        assert resp.status_code == 404

@pytest.mark.asyncio
async def test_error_requestToJoin_doble_solicitud():
    """
    ⚠️ Caso de ERROR
    Intentar unirse dos veces al mismo ride
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        driver = "jperez"         # conductor válido
        rideid = 1                # ride válido en estado 'ready'
        participante = "lgomez"   # participante válido
        destino = "Av Siempre Viva 742"
        spaces = 1

        # Primer request (debería funcionar si no existe)
        resp1 = await ac.post(
            f"/usuarios/{driver}/rides/{rideid}/requestToJoin/{participante}",
            params={"destino": destino, "spaces": spaces}
        )
        assert resp1.status_code in [201, 422]  # puede dar 422 si ya está

        # Segundo request (debería fallar si ya existe)
        resp2 = await ac.post(
            f"/usuarios/{driver}/rides/{rideid}/requestToJoin/{participante}",
            params={"destino": destino, "spaces": spaces}
        )
        assert resp2.status_code == 422
