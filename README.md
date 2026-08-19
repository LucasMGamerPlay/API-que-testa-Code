# CodePulse Benchmark API

API pública para medir e comparar a velocidade de snippets em JavaScript, Python, Rust, Go e C#, inspirada em ferramentas como JSBench.

## Rodar localmente

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Abra http://127.0.0.1:8000 para usar a interface ou http://127.0.0.1:8000/docs para a documentação OpenAPI.

JavaScript exige Node.js instalado, Python usa o interpretador que iniciou a API, Rust exige `rustc`, Go exige o Go SDK e C# exige o .NET SDK.

## Rodar com Docker

O contêiner instala todas as cinco toolchains automaticamente, sem alterar as instalações do computador host. Com o Docker Desktop iniciado:

```powershell
docker compose build
docker compose run --rm codepulse pytest -q
docker compose up
```

Abra http://127.0.0.1:8765. Para parar:

```powershell
docker compose down
```

## API

`POST /api/v1/benchmarks` executa um snippet:

```json
{"language":"javascript","code":"return 1 + 1","iterations":10000,"warmups":1000,"timeout_ms":2000}
```

`POST /api/v1/benchmarks/compare` recebe `benchmarks` com 2 a 20 itens e retorna `opsPerSecond`, tempo total, iterações e o item mais rápido.

## Segurança para produção

O executor usa processos filhos, timeout e limites de payload. Isso é adequado para desenvolvimento e uma implantação controlada, mas não deve receber código arbitrário diretamente na internet sem uma sandbox real: execute workers em containers efêmeros sem rede, com usuário sem privilégios, limites de CPU/memória, filesystem somente leitura, rate limiting persistente e autenticação/quota.

## Testes

```powershell
pytest
```
