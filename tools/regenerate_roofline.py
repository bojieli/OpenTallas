#!/usr/bin/env python3
"""Regenerate every roofline artifact as parallel processes.

``python3 tools/run_roofline_studies.py --force`` does the same work in one
process and takes hours now that every point is priced on the per-token
operator graph.  This splits it into its independent pieces -- the two primary
studies (each re-running its sensitivity tables on ``ROOFLINE_WORKERS``
workers), the two quantised variants, the two context ladders and one process
per candidate model -- runs them ``--jobs`` at a time, longest first, and then
the layers that read their output: ``tools/decode_critical_path.py``,
``tools/wafer_vs_array_study.py``, ``tools/serial_latency_report.py`` and
``tools/run_speculative_roofline.py`` (``SPECULATIVE_WORKERS`` workers, at most 4:
each peaks at 6-10 GB).  ``--layers-only`` runs just that second half.  Every
piece writes disjoint files by the code path ``run_all`` uses, so the bytes are
the same as a single-process run.

After it: ``python3 tools/audit_prose_figure_coverage.py``, update the two
untriaged-count annotations if the census moved, ``make check-figures``.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import run_roofline_studies as S  # noqa: E402


def pieces(output: Path) -> list[tuple[str, list[str], dict[str, str]]]:
    base = [sys.executable, str(ROOT / "tools" / "run_roofline_studies.py"), "--output", str(output), "--force"]
    out: list[tuple[str, list[str], dict[str, str]]] = []
    for study in S.STUDIES:
        out.append((f"primary:{study}", base + ["--part", f"primary:{study}"], {}))
    # the heaviest candidates first: large MoE models at the primary context
    order = sorted(S.CANDIDATE_MODELS, key=lambda c: (c[0].endswith(("-8k", "-1m", "-200k")), c[0]))
    for slug, *_ in order:
        out.append((f"candidate:{slug}", base + ["--candidates", slug], {}))
    for study in S.STUDIES:
        out.append((f"quantised:{study}", base + ["--part", f"quantised:{study}"], {}))
        out.append((f"ladder:{study}", base + ["--part", f"ladder:{study}"], {}))
    return out


def run(output: Path, jobs: int, primary_workers: int, log_dir: Path) -> int:
    log_dir.mkdir(parents=True, exist_ok=True)
    queue = pieces(output)
    running: list[tuple[str, subprocess.Popen, float]] = []
    failed: list[str] = []
    start = time.time()
    while queue or running:
        while queue and len(running) < jobs:
            name, cmd, extra = queue.pop(0)
            env = dict(os.environ, **extra)
            env["ROOFLINE_WORKERS"] = str(primary_workers if name.startswith("primary") else 1)
            log = open(log_dir / (name.replace(":", "_") + ".log"), "w")
            running.append((name, subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT),
                            time.time()))
            print(f"[{time.time() - start:7.0f} s] start {name}", flush=True)
        time.sleep(5)
        for item in list(running):
            name, proc, t0 = item
            if proc.poll() is not None:
                running.remove(item)
                status = "ok" if proc.returncode == 0 else f"FAILED ({proc.returncode})"
                if proc.returncode:
                    failed.append(name)
                print(f"[{time.time() - start:7.0f} s] {status} {name} after {time.time() - t0:.0f} s", flush=True)
    if failed:
        print("failed pieces: " + ", ".join(failed))
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--output", type=Path, default=S.OUTPUT_ROOT)
    ap.add_argument("--jobs", type=int, default=8, help="concurrent study processes")
    ap.add_argument("--primary-workers", type=int, default=4, help="sensitivity workers per primary study")
    ap.add_argument("--speculative-workers", type=int, default=4,
                    help="each worker peaks at 6-10 GB; 4 keeps the layer under ~30 GB")
    ap.add_argument("--logs", type=Path, default=Path(os.environ.get("TMPDIR", "/tmp")) / "roofline-regen-logs")
    ap.add_argument("--skip-layers", action="store_true",
                    help="stop after the studies (no critical-path report, no speculative layer)")
    ap.add_argument("--layers-only", action="store_true", help="only the layers that read the studies")
    args = ap.parse_args(argv)
    if args.layers_only:
        return layers(args.speculative_workers)
    if run(args.output, args.jobs, args.primary_workers, args.logs):
        return 1
    if args.skip_layers or args.output.resolve() != S.OUTPUT_ROOT.resolve():
        return 0
    return layers(args.speculative_workers)


def layers(speculative_workers: int) -> int:
    """Everything that reads the regenerated studies, in dependency order: the standalone bottom-up
    study (reads the V4.1 study rows), the wafer-vs-array study built on it, the serial-latency
    report, and the speculative layer."""
    for tool, extra in (("decode_critical_path.py", []), ("wafer_vs_array_study.py", ["--workers", "4"]),
                        ("serial_latency_report.py", [])):
        subprocess.run([sys.executable, str(ROOT / "tools" / tool), *extra], cwd=ROOT, check=True)
    env = dict(os.environ, SPECULATIVE_WORKERS=str(speculative_workers))
    subprocess.run([sys.executable, str(ROOT / "tools" / "run_speculative_roofline.py"), "--force"],
                   cwd=ROOT, env=env, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
