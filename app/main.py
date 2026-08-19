from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .executor import BenchmarkError, run_benchmark

app = FastAPI(
    title="CodePulse Benchmark API",
    version="1.0.0",
    description="API pública para comparar a velocidade de snippets de código.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class BenchmarkRequest(BaseModel):
    language: str = Field(default="javascript", pattern="^(javascript|python|rust|go|csharp)$")
    code: str = Field(min_length=1, max_length=50_000)
    iterations: int = Field(default=10_000, ge=1, le=100_000)
    warmups: int = Field(default=1_000, ge=0, le=10_000)
    timeout_ms: int = Field(default=2_000, ge=50, le=10_000)


class CompareRequest(BaseModel):
    benchmarks: list[BenchmarkRequest] = Field(min_length=2, max_length=20)


@app.exception_handler(BenchmarkError)
async def benchmark_error_handler(_: Request, error: BenchmarkError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(error)})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/benchmarks")
def benchmark(payload: BenchmarkRequest) -> dict[str, Any]:
    started = time.perf_counter()
    result = run_benchmark(**payload.model_dump())
    result["durationMs"] = round((time.perf_counter() - started) * 1000, 2)
    return {"result": result}


@app.post("/api/v1/benchmarks/compare")
def compare(payload: CompareRequest) -> dict[str, Any]:
    results = []
    for index, item in enumerate(payload.benchmarks):
        result = run_benchmark(**item.model_dump())
        results.append({"id": index + 1, "label": f"Snippet {index + 1}", **result})
    fastest = max(results, key=lambda item: item["opsPerSecond"] or 0)
    for result in results:
        result["relativeToFastest"] = round((fastest["opsPerSecond"] / result["opsPerSecond"]) if result["opsPerSecond"] else 0, 2)
    return {"results": results, "fastestId": fastest["id"]}


app.mount("/", StaticFiles(directory=Path(__file__).parent.parent / "static", html=True), name="static")
