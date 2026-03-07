from unittest.mock import patch

from fastapi.testclient import TestClient

# Mock the engine before importing the app to avoid initialization overhead/errors
# We patch it in the core module because app.py imports it from there.
with patch("auragraph.core.engine.AuroraGraphEngine") as MockEngine:
    mock_instance = MockEngine.return_value
    from auragraph.app import app


client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "model" in data
    assert "db" in data

def test_query_endpoint():
    # Setup mock return for engine.predict
    mock_instance.predict.return_value = {
        "response": "Test response",
        "context": ["Source 1"],
        "retrieval_ms": 10.0,
        "generation_ms": 100.0,
        "sources": [{"filename": "test.txt", "page": 1}]
    }

    response = client.post("/query", json={"query": "test question", "stream": False})

    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "Test response"
    assert data["context"] == ["Source 1"]

    # Verify the mock was called correctly
    mock_instance.predict.assert_called_with("test question", stream=False)

def test_query_streaming_unsupported():
    response = client.post("/query", json={"query": "test", "stream": True})
    assert response.status_code == 200
    data = response.json()
    assert "error" in data
    assert "not supported" in data.get("error", "").lower()
