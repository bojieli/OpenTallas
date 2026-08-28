#!/usr/bin/env python3
"""Measure a local OpenAI-compatible vLLM endpoint without altering it.

This intentionally records a shared/contended service observation.  It does
not stop other endpoints, change model settings, or attribute whole-GPU energy
to the benchmark requests.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import subprocess
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs" / "benchmarks" / "local_gpu_break_even.json"
DEFAULT_RESULT_ROOT = ROOT / "results" / "gpu" / "local_rtx_pro_6000"


class MeasurementError(RuntimeError):
    """Raised when the governed measurement contract is not satisfied."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def strict_json(path: Path) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise MeasurementError(f"duplicate JSON key {key!r} in {path}")
            result[key] = value
        return result

    try:
        decoded = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise MeasurementError(f"cannot read strict JSON {path}: {exc}") from exc
    if not isinstance(decoded, dict):
        raise MeasurementError(f"expected an object in {path}")
    return decoded


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != 1:
        raise MeasurementError("unsupported benchmark schema_version")
    endpoint = config.get("endpoint", {})
    gpu = config.get("gpu", {})
    request = config.get("request", {})
    policy = config.get("contamination_policy", {})
    if not str(endpoint.get("base_url", "")).startswith("http://127.0.0.1:"):
        raise MeasurementError(
            "the governed benchmark is restricted to a loopback endpoint"
        )
    for field in (
        "api_model",
        "expected_root",
        "expected_max_model_len",
        "request_timeout_s",
    ):
        if field not in endpoint:
            raise MeasurementError(f"endpoint.{field} is required")
    for field in ("expected_name", "expected_uuid", "sample_period_s"):
        if field not in gpu:
            raise MeasurementError(f"gpu.{field} is required")
    if policy.get("label") != "shared_contended":
        raise MeasurementError(
            "this local campaign must remain labelled shared_contended"
        )
    if policy.get("whole_gpu_energy_attribution_allowed") is not False:
        raise MeasurementError("whole-GPU energy attribution must be forbidden")
    if request.get("stream") is not True or request.get("include_usage") is not True:
        raise MeasurementError("streaming usage reporting is required")
    if request.get("temperature") != 0:
        raise MeasurementError("temperature must be zero")
    completion_tokens = int(request.get("completion_tokens", 0))
    if completion_tokens <= 0 or completion_tokens > 256:
        raise MeasurementError("completion_tokens must be in 1..256")
    max_len = int(endpoint["expected_max_model_len"])
    sweep = config.get("sweep")
    if not isinstance(sweep, list) or not sweep:
        raise MeasurementError("at least one sweep point is required")
    for index, point in enumerate(sweep):
        if not isinstance(point, dict):
            raise MeasurementError(f"sweep[{index}] must be an object")
        prompt_tokens = int(point.get("prompt_tokens", 0))
        concurrency = int(point.get("concurrency", 0))
        repetitions = int(point.get("repetitions", 0))
        if prompt_tokens <= 0 or prompt_tokens + completion_tokens > max_len:
            raise MeasurementError(f"sweep[{index}] exceeds the model context contract")
        if concurrency not in (1, 2):
            raise MeasurementError(f"sweep[{index}] concurrency must be one or two")
        if repetitions <= 0 or repetitions > 10:
            raise MeasurementError(f"sweep[{index}] repetitions must be in 1..10")


def json_request(
    url: str,
    payload: dict[str, Any] | None,
    timeout_s: float,
) -> dict[str, Any]:
    data = (
        None
        if payload is None
        else json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )
    request = Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data is not None else {},
        method="POST" if data is not None else "GET",
    )
    try:
        with urlopen(request, timeout=timeout_s) as response:
            body = response.read()
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise MeasurementError(f"HTTP {exc.code} from {url}: {body[:1000]}") from exc
    except URLError as exc:
        raise MeasurementError(f"cannot reach {url}: {exc}") from exc
    try:
        decoded = json.loads(body)
    except json.JSONDecodeError as exc:
        raise MeasurementError(
            f"non-JSON response from {url}: {body[:1000]!r}"
        ) from exc
    if not isinstance(decoded, dict):
        raise MeasurementError(f"expected a JSON object from {url}")
    return decoded


def endpoint_snapshot(base_url: str, timeout_s: float) -> dict[str, Any]:
    return json_request(f"{base_url.rstrip('/')}/v1/models", None, timeout_s)


def select_endpoint_model(snapshot: dict[str, Any], model_id: str) -> dict[str, Any]:
    rows = snapshot.get("data")
    if not isinstance(rows, list):
        raise MeasurementError("endpoint /v1/models response has no data list")
    matches = [
        row for row in rows if isinstance(row, dict) and row.get("id") == model_id
    ]
    if len(matches) != 1:
        raise MeasurementError(
            f"expected exactly one endpoint model named {model_id!r}"
        )
    return matches[0]


def validate_endpoint_contract(
    config: dict[str, Any], snapshot: dict[str, Any]
) -> dict[str, Any]:
    expected = config["endpoint"]
    model = select_endpoint_model(snapshot, str(expected["api_model"]))
    if model.get("root") != expected["expected_root"]:
        raise MeasurementError(
            f"endpoint root changed: {model.get('root')!r} != {expected['expected_root']!r}"
        )
    if int(model.get("max_model_len", -1)) != int(expected["expected_max_model_len"]):
        raise MeasurementError("endpoint max_model_len changed")
    return model


def stable_endpoint_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Remove vLLM response-generated IDs/timestamps before stability checks."""

    rows = snapshot.get("data")
    if not isinstance(rows, list):
        raise MeasurementError("endpoint /v1/models response has no data list")
    stable_rows = []
    for row in rows:
        if not isinstance(row, dict):
            raise MeasurementError("endpoint /v1/models data contains a non-object")
        permissions = []
        for permission in row.get("permission", []):
            if not isinstance(permission, dict):
                raise MeasurementError("endpoint model permission is not an object")
            permissions.append(
                {
                    key: value
                    for key, value in permission.items()
                    if key not in {"id", "created"}
                }
            )
        stable_rows.append(
            {
                key: value
                for key, value in row.items()
                if key not in {"id", "created", "permission"}
            }
            | {"id": row.get("id"), "permission": permissions}
        )
    return {
        "object": snapshot.get("object"),
        "data": sorted(stable_rows, key=lambda item: str(item.get("id"))),
    }


def run_command(arguments: list[str]) -> str:
    process = subprocess.run(
        arguments,
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if process.returncode != 0:
        raise MeasurementError(
            f"command failed ({process.returncode}): {' '.join(arguments)}\n{process.stderr.strip()}"
        )
    return process.stdout


GPU_FIELDS = (
    "timestamp",
    "name",
    "uuid",
    "memory.total",
    "memory.used",
    "power.draw",
    "power.limit",
    "utilization.gpu",
    "utilization.memory",
    "temperature.gpu",
)


def parse_csv_row(text: str, fields: tuple[str, ...]) -> dict[str, str]:
    rows = list(csv.reader(line for line in text.splitlines() if line.strip()))
    if len(rows) != 1 or len(rows[0]) != len(fields):
        raise MeasurementError(f"unexpected nvidia-smi output for {fields}: {text!r}")
    return {field: value.strip() for field, value in zip(fields, rows[0])}


def gpu_sample(gpu_uuid: str) -> dict[str, Any]:
    query = ",".join(GPU_FIELDS)
    row = parse_csv_row(
        run_command(
            [
                "nvidia-smi",
                "-i",
                gpu_uuid,
                f"--query-gpu={query}",
                "--format=csv,noheader,nounits",
            ]
        ),
        GPU_FIELDS,
    )
    numeric = {
        "memory.total": "memory_total_mib",
        "memory.used": "memory_used_mib",
        "power.draw": "power_draw_w",
        "power.limit": "power_limit_w",
        "utilization.gpu": "gpu_utilization_percent",
        "utilization.memory": "memory_utilization_percent",
        "temperature.gpu": "temperature_c",
    }
    result: dict[str, Any] = {
        "nvidia_smi_timestamp": row["timestamp"],
        "name": row["name"],
        "uuid": row["uuid"],
    }
    for source, destination in numeric.items():
        try:
            result[destination] = float(row[source])
        except ValueError:
            result[destination] = None
    return result


def compute_process_inventory() -> list[dict[str, Any]]:
    fields = ("gpu_uuid", "pid", "process_name", "used_memory")
    output = run_command(
        [
            "nvidia-smi",
            "--query-compute-apps=" + ",".join(fields),
            "--format=csv,noheader,nounits",
        ]
    )
    result = []
    for raw in csv.reader(line for line in output.splitlines() if line.strip()):
        if len(raw) != len(fields):
            raise MeasurementError(f"unexpected compute-process row: {raw!r}")
        row = {field: value.strip() for field, value in zip(fields, raw)}
        result.append(
            {
                "gpu_uuid": row["gpu_uuid"],
                "pid": int(row["pid"]),
                "process_name": row["process_name"],
                "used_memory_mib": None
                if row["used_memory"] in {"N/A", "[N/A]"}
                else float(row["used_memory"]),
            }
        )
    return sorted(result, key=lambda item: (item["gpu_uuid"], item["pid"]))


def validate_gpu_contract(config: dict[str, Any], sample: dict[str, Any]) -> None:
    expected = config["gpu"]
    if sample.get("uuid") != expected["expected_uuid"]:
        raise MeasurementError("selected GPU UUID does not match the governed config")
    if sample.get("name") != expected["expected_name"]:
        raise MeasurementError("selected GPU name does not match the governed config")


def tokenize(base_url: str, model: str, prompt: str, timeout_s: float) -> list[int]:
    decoded = json_request(
        f"{base_url.rstrip('/')}/tokenize",
        {"model": model, "prompt": prompt},
        timeout_s,
    )
    tokens = decoded.get("tokens")
    if not isinstance(tokens, list) or not all(
        isinstance(token, int) for token in tokens
    ):
        raise MeasurementError("tokenizer response did not include integer tokens")
    if decoded.get("count") != len(tokens):
        raise MeasurementError("tokenizer count does not match its token list")
    return tokens


def exact_prompt_tokens(config: dict[str, Any], target: int) -> list[int]:
    endpoint = config["endpoint"]
    request = config["request"]
    seed = str(request["prompt_seed"]).strip() + " "
    base = tokenize(
        endpoint["base_url"],
        endpoint["api_model"],
        seed,
        float(endpoint["request_timeout_s"]),
    )
    if not base:
        raise MeasurementError("prompt seed tokenized to an empty sequence")
    repeats = math.ceil(target / len(base)) + 2
    tokens: list[int] = []
    for _ in range(4):
        tokens = tokenize(
            endpoint["base_url"],
            endpoint["api_model"],
            seed * repeats,
            float(endpoint["request_timeout_s"]),
        )
        if len(tokens) >= target:
            break
        # Token boundaries can merge between repeated natural-language seeds,
        # so the isolated-seed token count slightly overestimates the combined
        # rate. Grow from the measured deficit instead of assuming additivity.
        repeats += math.ceil((target - len(tokens)) / max(1, len(base) - 1)) + 2
    if len(tokens) < target:
        raise MeasurementError(f"could not construct a {target}-token prompt")
    return tokens[:target]


def parse_sse_blocks(lines: Iterable[bytes]) -> list[str]:
    """Return joined data payloads from an SSE byte-line stream."""

    blocks: list[str] = []
    data_lines: list[str] = []
    for raw in lines:
        line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
        if not line:
            if data_lines:
                blocks.append("\n".join(data_lines))
                data_lines = []
            continue
        if line.startswith(":"):
            continue
        field, separator, value = line.partition(":")
        if field == "data":
            data_lines.append(
                value[1:] if separator and value.startswith(" ") else value
            )
    if data_lines:
        blocks.append("\n".join(data_lines))
    return blocks


def completion_payload(
    config: dict[str, Any], prompt_tokens: list[int]
) -> dict[str, Any]:
    request = config["request"]
    return {
        "model": config["endpoint"]["api_model"],
        "prompt": prompt_tokens,
        "max_tokens": int(request["completion_tokens"]),
        "temperature": request["temperature"],
        "seed": int(request["seed"]),
        "ignore_eos": bool(request["ignore_eos"]),
        "stream": True,
        "stream_options": {"include_usage": True},
    }


def measure_completion(
    config: dict[str, Any],
    prompt_tokens: list[int],
    request_id: str,
    release: threading.Barrier,
) -> dict[str, Any]:
    endpoint = config["endpoint"]
    payload = completion_payload(config, prompt_tokens)
    encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = Request(
        f"{endpoint['base_url'].rstrip('/')}/v1/completions",
        data=encoded,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    release.wait()
    started = time.monotonic()
    started_utc = utc_now()
    raw_events: list[dict[str, Any]] = []
    content_event_times: list[float] = []
    usage: dict[str, Any] | None = None
    finish_reason: str | None = None
    server_id: str | None = None
    try:
        with urlopen(request, timeout=float(endpoint["request_timeout_s"])) as response:
            if response.status != 200:
                raise MeasurementError(
                    f"completion request returned HTTP {response.status}"
                )
            data_lines: list[str] = []
            while True:
                raw = response.readline()
                if not raw:
                    if data_lines:
                        payload_text = "\n".join(data_lines)
                        raw_events.append(
                            {"at_s": time.monotonic() - started, "data": payload_text}
                        )
                    break
                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                if line:
                    if line.startswith("data:"):
                        value = line[5:]
                        data_lines.append(value[1:] if value.startswith(" ") else value)
                    continue
                if not data_lines:
                    continue
                event_time = time.monotonic() - started
                payload_text = "\n".join(data_lines)
                data_lines = []
                raw_events.append({"at_s": event_time, "data": payload_text})
                if payload_text == "[DONE]":
                    continue
                try:
                    event = json.loads(payload_text)
                except json.JSONDecodeError as exc:
                    raise MeasurementError(
                        f"invalid SSE JSON: {payload_text[:500]!r}"
                    ) from exc
                if not isinstance(event, dict):
                    raise MeasurementError("SSE event was not a JSON object")
                server_id = (
                    str(event.get("id", server_id)) if event.get("id") else server_id
                )
                if isinstance(event.get("usage"), dict):
                    usage = event["usage"]
                choices = event.get("choices")
                if isinstance(choices, list):
                    for choice in choices:
                        if not isinstance(choice, dict):
                            continue
                        text = choice.get("text")
                        if isinstance(text, str) and text:
                            content_event_times.append(event_time)
                        if choice.get("finish_reason") is not None:
                            finish_reason = str(choice["finish_reason"])
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise MeasurementError(
            f"HTTP {exc.code} from completion endpoint: {body[:1000]}"
        ) from exc
    except URLError as exc:
        raise MeasurementError(f"completion endpoint failed: {exc}") from exc
    ended_s = time.monotonic() - started
    if usage is None:
        raise MeasurementError(f"{request_id}: stream did not report usage")
    if not content_event_times:
        raise MeasurementError(f"{request_id}: stream had no content-bearing event")
    prompt_count = int(usage.get("prompt_tokens", -1))
    completion_count = int(usage.get("completion_tokens", -1))
    target_completion = int(config["request"]["completion_tokens"])
    failures = []
    if prompt_count != len(prompt_tokens):
        failures.append(
            f"usage prompt_tokens={prompt_count}, expected {len(prompt_tokens)}"
        )
    if completion_count != target_completion:
        failures.append(
            f"usage completion_tokens={completion_count}, expected {target_completion}"
        )
    ttft = content_event_times[0]
    final_content = content_event_times[-1]
    content_span = final_content - ttft
    after_ttft = ended_s - ttft
    return {
        "request_id": request_id,
        "status": "pass" if not failures else "fail",
        "acceptance_failures": failures,
        "started_at_utc": started_utc,
        "prompt_tokens": prompt_count,
        "completion_tokens": completion_count,
        "ttft_s": ttft,
        "end_to_end_s": ended_s,
        "last_content_s": final_content,
        "completion_tokens_s_end_to_end": completion_count / ended_s,
        "completion_tokens_s_after_ttft_proxy": completion_count / after_ttft
        if after_ttft > 0
        else None,
        "content_event_count": len(content_event_times),
        "content_event_rate_hz": (len(content_event_times) - 1) / content_span
        if content_span > 0 and len(content_event_times) > 1
        else None,
        "content_event_interarrival_s": [
            later - earlier
            for earlier, later in zip(content_event_times, content_event_times[1:])
        ],
        "chunk_timing_semantics": "content-bearing SSE event arrival; an event is not guaranteed to equal one token",
        "finish_reason": finish_reason,
        "server_request_id": server_id,
        "usage": usage,
        "raw_events": raw_events,
        "request_contract": {
            "method": "v1/completions",
            "prompt_token_ids_sha256": hashlib.sha256(
                json.dumps(prompt_tokens, separators=(",", ":")).encode("ascii")
            ).hexdigest(),
            "requested_prompt_tokens": len(prompt_tokens),
            "requested_completion_tokens": target_completion,
            "temperature": config["request"]["temperature"],
            "seed": config["request"]["seed"],
            "ignore_eos": config["request"]["ignore_eos"],
        },
    }


def sample_until_stopped(
    gpu_uuid: str,
    period_s: float,
    stop: threading.Event,
    zero: float,
    destination: list[dict[str, Any]],
) -> None:
    while not stop.is_set():
        try:
            sample = gpu_sample(gpu_uuid)
            sample["at_s"] = time.monotonic() - zero
            destination.append(sample)
        except Exception as exc:  # Preserve a sampling fault without killing requests.
            destination.append(
                {
                    "at_s": time.monotonic() - zero,
                    "sample_error": f"{type(exc).__name__}: {exc}",
                }
            )
        stop.wait(period_s)


def contaminated_energy_j(samples: list[dict[str, Any]]) -> float | None:
    valid = [
        (float(sample["at_s"]), float(sample["power_draw_w"]))
        for sample in samples
        if sample.get("power_draw_w") is not None and sample.get("at_s") is not None
    ]
    if len(valid) < 2:
        return None
    valid.sort()
    return sum(
        (power_a + power_b) * 0.5 * (time_b - time_a)
        for (time_a, power_a), (time_b, power_b) in zip(valid, valid[1:])
    )


def run_wave(
    config: dict[str, Any],
    prompt_tokens: list[int],
    point_index: int,
    repetition: int,
    raw_dir: Path,
) -> dict[str, Any]:
    concurrency = int(config["sweep"][point_index]["concurrency"])
    barrier = threading.Barrier(concurrency + 1)
    results: list[dict[str, Any] | None] = [None] * concurrency
    errors: list[str | None] = [None] * concurrency

    def worker(slot: int) -> None:
        request_id = f"p{point_index:02d}-r{repetition:02d}-c{slot:02d}"
        try:
            results[slot] = measure_completion(
                config, prompt_tokens, request_id, barrier
            )
        except Exception as exc:
            errors[slot] = f"{type(exc).__name__}: {exc}"

    threads = [
        threading.Thread(target=worker, args=(slot,), daemon=False)
        for slot in range(concurrency)
    ]
    samples: list[dict[str, Any]] = []
    stop = threading.Event()
    wave_zero = time.monotonic()
    sampler = threading.Thread(
        target=sample_until_stopped,
        args=(
            config["gpu"]["expected_uuid"],
            float(config["gpu"]["sample_period_s"]),
            stop,
            wave_zero,
            samples,
        ),
        daemon=False,
    )
    sampler.start()
    for thread in threads:
        thread.start()
    wave_started_utc = utc_now()
    barrier.wait()
    for thread in threads:
        thread.join()
    stop.set()
    sampler.join()
    wave_elapsed_s = time.monotonic() - wave_zero
    materialized = []
    for slot, result in enumerate(results):
        request_id = f"p{point_index:02d}-r{repetition:02d}-c{slot:02d}"
        if result is None:
            result = {
                "request_id": request_id,
                "status": "error",
                "error": errors[slot] or "worker returned no result",
                "raw_events": [],
            }
        raw_path = raw_dir / f"{request_id}.sse.json"
        raw_path.write_text(
            json.dumps(
                {
                    "request_id": request_id,
                    "contamination_label": "shared_contended",
                    "raw_events": result.pop("raw_events"),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        result["raw_sse_artifact"] = {
            "path": str(raw_path.relative_to(ROOT)),
            "sha256": sha256_file(raw_path),
            "size_bytes": raw_path.stat().st_size,
        }
        materialized.append(result)
    return {
        "point_index": point_index,
        "repetition": repetition,
        "prompt_tokens": len(prompt_tokens),
        "concurrency": concurrency,
        "started_at_utc": wave_started_utc,
        "elapsed_s": wave_elapsed_s,
        "requests": materialized,
        "gpu_samples": samples,
        "whole_gpu_window_energy_j": contaminated_energy_j(samples),
        "energy_semantics": config["contamination_policy"][
            "window_integrated_gpu_energy_semantics"
        ],
    }


def summarize_requests(waves: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for wave in waves:
        for request in wave["requests"]:
            if request.get("status") == "pass":
                grouped[(wave["prompt_tokens"], wave["concurrency"])].append(request)
    rows = []
    for (prompt_tokens, concurrency), requests in sorted(grouped.items()):
        rows.append(
            {
                "prompt_tokens": prompt_tokens,
                "concurrency": concurrency,
                "successful_requests": len(requests),
                "median_ttft_s": statistics.median(item["ttft_s"] for item in requests),
                "median_end_to_end_s": statistics.median(
                    item["end_to_end_s"] for item in requests
                ),
                "median_completion_tokens_s_end_to_end": statistics.median(
                    item["completion_tokens_s_end_to_end"] for item in requests
                ),
                "median_completion_tokens_s_after_ttft_proxy": statistics.median(
                    item["completion_tokens_s_after_ttft_proxy"] for item in requests
                ),
            }
        )
    return rows


def git_state() -> dict[str, Any]:
    try:
        head = run_command(["git", "-C", str(ROOT), "rev-parse", "HEAD"]).strip()
        status = run_command(["git", "-C", str(ROOT), "status", "--short"]).splitlines()
    except MeasurementError as exc:
        return {"error": str(exc)}
    return {"head": head, "worktree_clean": not status, "dirty_paths": status}


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# Local RTX PRO 6000 shared-serving measurement",
        "",
        "> **Evidence class: shared and contended.** This is a Qwen service-level",
        "> observation, not a clean peak-GPU benchmark, a DeepSeek-V4 comparison,",
        "> an OpenTallas implementation result, or attributable energy evidence.",
        "",
        f"- Status: **{result['status'].upper()}**",
        f"- Benchmark: `{result['benchmark_id']}`",
        f"- Generated: `{result['generated_at']}`",
        f"- Endpoint model: `{result['selected_endpoint_model']['id']}`",
        f"- Endpoint root: `{result['selected_endpoint_model']['root']}`",
        f"- GPU: `{result['gpu_before']['name']}`",
        f"- GPU UUID: `{result['gpu_before']['uuid']}`",
        "",
        "## Scenario medians",
        "",
        "Completion rate includes all completion tokens. The post-TTFT value is a",
        "service proxy; SSE chunk arrivals are not guaranteed to be token arrivals.",
        "",
        "| Prompt tokens | Concurrency | Requests | TTFT ms | End-to-end ms | Completion tok/s (E2E) | Completion tok/s (post-TTFT proxy) |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in result["summary"]:
        lines.append(
            "| {prompt_tokens} | {concurrency} | {successful_requests} | {ttft:.3f} | "
            "{e2e:.3f} | {rate:.3f} | {post:.3f} |".format(
                **row,
                ttft=row["median_ttft_s"] * 1000,
                e2e=row["median_end_to_end_s"] * 1000,
                rate=row["median_completion_tokens_s_end_to_end"],
                post=row["median_completion_tokens_s_after_ttft_proxy"],
            )
        )
    lines.extend(
        [
            "",
            "## Individual requests",
            "",
            "| Request | Prompt | Conc. | Status | TTFT ms | End-to-end ms | Completion tokens | Finish |",
            "| --- | ---: | ---: | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for wave in result["waves"]:
        for request in wave["requests"]:
            if request.get("status") in {"pass", "fail"}:
                lines.append(
                    f"| `{request['request_id']}` | {wave['prompt_tokens']} | "
                    f"{wave['concurrency']} | {request['status'].upper()} | "
                    f"{request['ttft_s'] * 1000:.3f} | "
                    f"{request['end_to_end_s'] * 1000:.3f} | "
                    f"{request['completion_tokens']} | {request['finish_reason']} |"
                )
            else:
                lines.append(
                    f"| `{request['request_id']}` | {wave['prompt_tokens']} | "
                    f"{wave['concurrency']} | ERROR | — | — | — | — |"
                )
    all_samples = [sample for wave in result["waves"] for sample in wave["gpu_samples"]]
    valid_power = [
        sample["power_draw_w"] for sample in all_samples if sample.get("power_draw_w")
    ]
    valid_util = [
        sample["gpu_utilization_percent"]
        for sample in all_samples
        if sample.get("gpu_utilization_percent") is not None
    ]
    lines.extend(["", "## Shared-GPU observation", ""])
    if valid_power:
        lines.append(
            f"Observed whole-GPU power samples spanned {min(valid_power):.2f}–"
            f"{max(valid_power):.2f} W; utilization samples spanned "
            f"{min(valid_util):.1f}–{max(valid_util):.1f}% when available."
        )
    else:
        lines.append("No valid power samples were captured.")
    lines.extend(
        [
            "",
            "Window-integrated joules are retained in `measurement.json` only as",
            "contaminated whole-GPU observations. They are not divided by requests or",
            "tokens and are not attributed to this benchmark because other workloads",
            "were active.",
            "",
            "## Claim boundary",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in result["claim_boundary"])
    lines.append("")
    return "\n".join(lines)


def endpoint_set(config: dict[str, Any]) -> list[str]:
    return [
        config["endpoint"]["base_url"],
        *config["contamination_policy"][
            "other_endpoints_must_not_be_stopped_or_changed"
        ],
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--result-root", type=Path, default=DEFAULT_RESULT_ROOT)
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="validate config, endpoint identity, and GPU identity without generating tokens",
    )
    arguments = parser.parse_args()
    config_path = arguments.config.resolve()
    config = strict_json(config_path)
    validate_config(config)
    timeout_s = float(config["endpoint"]["request_timeout_s"])
    before_endpoints = {
        endpoint: endpoint_snapshot(endpoint, timeout_s)
        for endpoint in endpoint_set(config)
    }
    selected_model = validate_endpoint_contract(
        config, before_endpoints[config["endpoint"]["base_url"]]
    )
    before_gpu = gpu_sample(config["gpu"]["expected_uuid"])
    validate_gpu_contract(config, before_gpu)
    if arguments.check_only:
        print(
            f"measurement contract verified: {selected_model['id']} on "
            f"{before_gpu['name']} ({config['contamination_policy']['label']})"
        )
        return 0

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = arguments.result_root.resolve() / run_id
    if run_dir.exists():
        raise MeasurementError(
            f"refusing to overwrite existing run directory {run_dir}"
        )
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True)
    prompt_cache: dict[int, list[int]] = {}
    for point in config["sweep"]:
        target = int(point["prompt_tokens"])
        prompt_cache.setdefault(target, exact_prompt_tokens(config, target))
    process_before = compute_process_inventory()
    waves = []
    for point_index, point in enumerate(config["sweep"]):
        target = int(point["prompt_tokens"])
        for repetition in range(int(point["repetitions"])):
            print(
                f"[{point_index + 1}/{len(config['sweep'])}] prompt={target}, "
                f"concurrency={point['concurrency']}, repetition={repetition + 1}",
                flush=True,
            )
            waves.append(
                run_wave(config, prompt_cache[target], point_index, repetition, raw_dir)
            )
    after_endpoints = {
        endpoint: endpoint_snapshot(endpoint, timeout_s)
        for endpoint in endpoint_set(config)
    }
    validate_endpoint_contract(config, after_endpoints[config["endpoint"]["base_url"]])
    after_gpu = gpu_sample(config["gpu"]["expected_uuid"])
    validate_gpu_contract(config, after_gpu)
    process_after = compute_process_inventory()
    requests = [request for wave in waves for request in wave["requests"]]
    failures = [request for request in requests if request.get("status") != "pass"]
    endpoint_stability = {
        endpoint: stable_endpoint_snapshot(before_endpoints[endpoint])
        == stable_endpoint_snapshot(after_endpoints[endpoint])
        for endpoint in before_endpoints
    }
    endpoint_byte_stability = {
        endpoint: before_endpoints[endpoint] == after_endpoints[endpoint]
        for endpoint in before_endpoints
    }
    result = {
        "schema_version": 1,
        "benchmark_id": config["benchmark_id"],
        "generated_at": utc_now(),
        "status": "pass"
        if not failures and all(endpoint_stability.values())
        else "fail",
        "evidence_class": config["evidence_class"],
        "contamination_label": config["contamination_policy"]["label"],
        "config": {
            "path": str(config_path.relative_to(ROOT)),
            "sha256": sha256_file(config_path),
            "contents": config,
        },
        "runner": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": sha256_file(Path(__file__).resolve()),
            "size_bytes": Path(__file__).resolve().stat().st_size,
        },
        "git": git_state(),
        "selected_endpoint_model": selected_model,
        "endpoint_snapshots": {"before": before_endpoints, "after": after_endpoints},
        "endpoint_stability": endpoint_stability,
        "endpoint_byte_stability": endpoint_byte_stability,
        "endpoint_stability_semantics": "semantic /v1/models comparison excluding response-generated created timestamps and permission IDs; full raw snapshots are retained",
        "gpu_before": before_gpu,
        "gpu_after": after_gpu,
        "compute_processes_before": process_before,
        "compute_processes_after": process_after,
        "waves": waves,
        "summary": summarize_requests(waves),
        "failed_request_count": len(failures),
        "whole_gpu_energy_attribution_allowed": False,
        "claim_boundary": config["claim_boundary"],
    }
    measurement_path = run_dir / "measurement.json"
    measurement_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report_path = run_dir / "REPORT.md"
    report_path.write_text(render_report(result), encoding="utf-8")
    print(f"wrote {measurement_path.relative_to(ROOT)}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except MeasurementError as exc:
        raise SystemExit(f"measurement error: {exc}") from exc
