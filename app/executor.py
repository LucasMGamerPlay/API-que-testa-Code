from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

SUPPORTED_LANGUAGES = {"javascript", "python", "rust", "go", "csharp"}
MAX_CODE_LENGTH = 50_000
MAX_ITERATIONS = 100_000
MAX_WARMUPS = 10_000


class BenchmarkError(ValueError):
    """An expected error produced while preparing or running a benchmark."""


def _build_source(language: str, code: str, iterations: int, warmups: int) -> str:
    if language == "javascript":
        return f"""const {{ performance }} = require('node:perf_hooks');
const snippet = () => {{
{code}
}};
for (let i = 0; i < {warmups}; i++) snippet();
const start = performance.now();
for (let i = 0; i < {iterations}; i++) snippet();
const elapsedMs = performance.now() - start;
process.stdout.write(JSON.stringify({{ elapsedMs, iterations: {iterations} }}));
"""
    if language == "rust":
        return f"""use std::time::Instant;

fn snippet() {{
{chr(10).join('    ' + line if line else '    ' for line in code.splitlines())}
}}

fn main() {{
    for _ in 0..{warmups} {{ snippet(); }}
    let start = Instant::now();
    for _ in 0..{iterations} {{ snippet(); }}
    let elapsed_ms = start.elapsed().as_secs_f64() * 1000.0;
    println!(r#"{{{{\"elapsedMs\":{{}},\"iterations\":{iterations}}}}}"#, elapsed_ms);
}}
"""
    if language == "go":
        return f'''package main

import ("encoding/json"; "fmt"; "time")

func snippet() {{
{chr(10).join('    ' + line if line else '    ' for line in code.splitlines())}
}}

func main() {{
    for i := 0; i < {warmups}; i++ {{ snippet() }}
    start := time.Now()
    for i := 0; i < {iterations}; i++ {{ snippet() }}
    elapsedMs := float64(time.Since(start).Nanoseconds()) / 1000000
    result, _ := json.Marshal(map[string]interface{{}}{{"elapsedMs": elapsedMs, "iterations": {iterations}}})
    fmt.Println(string(result))
}}
'''
    if language == "csharp":
        return f'''using System;
using System.Diagnostics;
using System.Text.Json;

static void Snippet()
{{
{chr(10).join('    ' + line if line else '    ' for line in code.splitlines())}
}}

for (var i = 0; i < {warmups}; i++) Snippet();
var stopwatch = Stopwatch.StartNew();
for (var i = 0; i < {iterations}; i++) Snippet();
stopwatch.Stop();
Console.WriteLine(JsonSerializer.Serialize(new {{ elapsedMs = stopwatch.Elapsed.TotalMilliseconds, iterations = {iterations} }}));
'''
    return f"""import json
import time

def snippet():
{chr(10).join('    ' + line if line else '    ' for line in code.splitlines())}

for _ in range({warmups}):
    snippet()
start = time.perf_counter()
for _ in range({iterations}):
    snippet()
elapsed_ms = (time.perf_counter() - start) * 1000
print(json.dumps({{"elapsedMs": elapsed_ms, "iterations": {iterations}}}))
"""


def run_benchmark(language: str, code: str, iterations: int, warmups: int, timeout_ms: int) -> dict[str, Any]:
    if language not in SUPPORTED_LANGUAGES:
        raise BenchmarkError(f"Unsupported language: {language}")
    if not code.strip():
        raise BenchmarkError("Code cannot be empty")
    if len(code) > MAX_CODE_LENGTH:
        raise BenchmarkError(f"Code exceeds {MAX_CODE_LENGTH} characters")
    if not 1 <= iterations <= MAX_ITERATIONS:
        raise BenchmarkError(f"Iterations must be between 1 and {MAX_ITERATIONS}")
    if not 0 <= warmups <= MAX_WARMUPS:
        raise BenchmarkError(f"Warmups must be between 0 and {MAX_WARMUPS}")
    if not 50 <= timeout_ms <= 10_000:
        raise BenchmarkError("Timeout must be between 50 and 10000 milliseconds")

    source = _build_source(language, code, iterations, warmups)
    suffix = {"javascript": ".js", "python": ".py", "rust": ".rs", "go": ".go", "csharp": ".cs"}[language]
    go_runtime = shutil.which("go") or r"C:\Program Files\Go\bin\go.exe"
    command = {"javascript": ["node", "--no-addons"], "python": [sys.executable, "-I"], "rust": ["rustc", "-O"], "go": [go_runtime, "build", "-trimpath"], "csharp": ["dotnet", "build", "--nologo", "-c", "Release"]}[language]

    with tempfile.TemporaryDirectory() as temp_dir:
        script_path = Path(temp_dir) / f"benchmark{suffix}"
        script_path.write_text(source, encoding="utf-8")
        executable_path = script_path.with_suffix(".exe")
        try:
            if language in {"rust", "go"}:
                compiled = subprocess.run(
                    [*command, *( [str(script_path), "-o", str(executable_path)] if language == "rust" else ["-o", str(executable_path), str(script_path)] )],
                    capture_output=True,
                    text=True,
                    timeout=max(timeout_ms / 1000, 30),
                    cwd=temp_dir,
                )
                if compiled.returncode != 0:
                    raise BenchmarkError((compiled.stderr or f"{language} compilation failed").strip()[-2_000:])
                command = [str(executable_path)]
            elif language == "csharp":
                project_path = Path(temp_dir) / "benchmark.csproj"
                project_path.write_text("<Project Sdk=\"Microsoft.NET.Sdk\"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net9.0</TargetFramework><OptimizationPreference>Speed</OptimizationPreference><ImplicitUsings>enable</ImplicitUsings></PropertyGroup></Project>", encoding="utf-8")
                compiled = subprocess.run([*command, str(project_path)], capture_output=True, text=True, timeout=max(timeout_ms / 1000, 30), cwd=temp_dir)
                if compiled.returncode != 0:
                    raise BenchmarkError((compiled.stdout + compiled.stderr).strip()[-2_000:])
                executable_name = "benchmark.exe" if os.name == "nt" else "benchmark"
                command = [str(Path(temp_dir) / "bin" / "Release" / "net9.0" / executable_name)]
            completed = subprocess.run(
                [*command, str(script_path)] if language in {"javascript", "python"} else command,
                capture_output=True,
                text=True,
                timeout=timeout_ms / 1000,
                cwd=temp_dir,
            )
        except FileNotFoundError as error:
            runtime = {"javascript": "node", "python": "python", "rust": "rustc", "go": "go", "csharp": "dotnet"}[language]
            raise BenchmarkError(f"Runtime not found: {runtime}") from error
        except subprocess.TimeoutExpired as error:
            raise BenchmarkError("Benchmark exceeded its timeout") from error

    if completed.returncode != 0:
        message = (completed.stderr or "Benchmark failed").strip()[-2_000:]
        raise BenchmarkError(message)
    try:
        result = json.loads(completed.stdout)
        elapsed_ms = float(result["elapsedMs"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise BenchmarkError("Benchmark returned an invalid result") from error

    return {
        "elapsedMs": round(elapsed_ms, 4),
        "opsPerSecond": round(iterations / (elapsed_ms / 1000), 2) if elapsed_ms else None,
        "iterations": iterations,
        "warmups": warmups,
    }
