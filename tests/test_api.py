from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthcheck() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_python_benchmark() -> None:
    response = client.post(
        "/api/v1/benchmarks",
        json={"language": "python", "code": "value = sum(range(10))", "iterations": 5, "warmups": 1},
    )
    assert response.status_code == 200
    assert response.json()["result"]["iterations"] == 5


def test_rust_benchmark() -> None:
    response = client.post(
        "/api/v1/benchmarks",
        json={"language": "rust", "code": "let value = 1 + 1;", "iterations": 2, "warmups": 0},
    )
    assert response.status_code == 200
    assert response.json()["result"]["iterations"] == 2


def test_go_benchmark() -> None:
    response = client.post(
        "/api/v1/benchmarks",
        json={"language": "go", "code": "value := 1 + 1\n_ = value", "iterations": 2, "warmups": 0},
    )
    assert response.status_code == 200


def test_csharp_benchmark() -> None:
    response = client.post(
        "/api/v1/benchmarks",
        json={"language": "csharp", "code": "var value = 1 + 1;", "iterations": 2, "warmups": 0},
    )
    assert response.status_code == 200


def test_compare_requires_two_benchmarks() -> None:
    response = client.post(
        "/api/v1/benchmarks/compare",
        json={"benchmarks": [{"language": "python", "code": "x = 1"}]},
    )
    assert response.status_code == 422


def test_timeout_is_reported() -> None:
    response = client.post(
        "/api/v1/benchmarks",
        json={"language": "python", "code": "while True: pass", "iterations": 1, "timeout_ms": 100},
    )
    assert response.status_code == 400
    assert "timeout" in response.json()["detail"].lower()
