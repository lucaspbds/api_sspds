from fastapi.testclient import TestClient

import app.main as main_module
from database.exceptions import ErroConexaoBanco


client = TestClient(main_module.app)


def test_health_live():
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_ready_ok(monkeypatch):
    monkeypatch.setattr(main_module, "validar_conexao", lambda: True)
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


def test_health_ready_falha_conexao(monkeypatch):
    def _falhar():
        raise ErroConexaoBanco("Falha ao conectar")

    monkeypatch.setattr(main_module, "validar_conexao", _falhar)
    response = client.get("/health/ready")
    assert response.status_code == 503