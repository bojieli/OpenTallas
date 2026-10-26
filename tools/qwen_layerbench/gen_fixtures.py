#!/usr/bin/env python3
"""LAYERBENCH-QWEN fixtures (TOK.QW.BENCH.2): TP4 golden of every representative Qwen3-8B ROM layer at P8191.

    gen_fixtures.py gold     --fx FX --out GOLD [--py PY] [--threads N]      regenerate (CPU, fleet host)
    gen_fixtures.py manifest --gold GOLD [--history H] --out DIR [--budget-mb 5]
    gen_fixtures.py archive  --src [HOST:]DIR --name NAME                      copy to the AGIdock archive

The arithmetic is NOT re-derived here: `gold` runs the committed ISA golden tools/qwen_hbmacc_position_oracle_gpu.py
(--device cpu; the same command as tools/exactness/regen_fixtures.sh and tools/qwen_tokpass/run_1018.sh step gold),
then tools/exactness/fixtures.py verify (every file must equal the digest committed with the published evidence,
results/rtl/qwen_hbmacc_p8191_20261004/gold_tp4/oracle.json) and fixtures.py history (KV history, L0_die0 pinned).
Inputs (FX): prep/tp4 = the pinned TP4 stage-image prep of the released Qwen3-8B checkpoint (image sha256 pins in the
prep and in oracle.json prep_sha256), inputs/prompt_tokens_8192.txt, inputs/prompt_embedding.npz.

Representative layers (roles in MANIFEST.json):
  L0 cold     in  P8191/x_preload.hex                    out P8191/L00_die{d}_x.hex   kv out kv_at_P/L0_die{d}.json
  Ln chained  in  P8191/L{n-1}_die{d}_x.hex (n=1..35)     out P8191/L{n}_die{d}_x.hex
  KV attn Ln  in  kv_pre/L{n}_die{d}.npy (= history bin)  + the token's Q/K/V      out kv_at_P/L{n}_die{d}.json
  LM head     in  P8191/L35_die{d}_x.hex                  out head_die{d}_xnorm.hex, logits.npy, head.json (argmax)
`manifest` writes MANIFEST.json (path, sha256, bytes, role, committed copy or regenerable) and copies the small files
(priority: head.json, x_preload, layer X, kv_at_P, head xnorm) into DIR within --budget-mb.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "results/rtl/qwen_hbmacc_p8191_20261004/gold_tp4/oracle.json"
ARCHIVE = "ubuntu@155.103.253.53:/archive/opentallas-fixtures"
ARCHIVE_SSH = ["ssh", "-i", "/home/ubuntu/.ssh/agidock_ot", "-o", "ConnectTimeout=20", "-o", "ServerAliveInterval=30"]
ENVTP = {"QWEN_O4_TP": "4", "QWEN_O4_GROUPS": "6144", "HDC_SU_WIDTH": "1024", "HDC_KV_FMT": "fp8"}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return (ROOT / "SOURCE_COMMIT").read_text().strip() if (ROOT / "SOURCE_COMMIT").exists() else "unknown"


def gold(a) -> int:
    fx, out = a.fx.resolve(), a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, **ENVTP, OMP_NUM_THREADS=str(a.threads))
    cmd = [a.py, str(ROOT / "tools/qwen_hbmacc_position_oracle_gpu.py"), "--run", "--device", "cpu",
           "--prep-dir", str(fx / "prep/tp4"), "--layers", "36", "--head",
           "--tokens", str(fx / "inputs/prompt_tokens_8192.txt"), "--positions", "8191",
           "--embedding-npz", str(fx / "inputs/prompt_embedding.npz"), "--out", str(out)]
    t0 = time.time()
    rc = subprocess.call(cmd, env=env, cwd=ROOT)
    print(f"oracle rc={rc} wall_s={time.time() - t0:.0f}", flush=True)
    if rc:
        return 4
    fxt = ROOT / "tools/exactness/fixtures.py"
    if subprocess.call([sys.executable, str(fxt), "verify", "--gold", str(out), "--ref", str(REF),
                        "--out", str(out / "verify.json")], cwd=ROOT):
        return 5
    hist = a.history or (out.parent / "history")
    return 6 if subprocess.call([sys.executable, str(fxt), "history", "--gold", str(out / "P8191"),
                                 "--out", str(hist)], cwd=ROOT) else 0


def role(rel: str):
    n = Path(rel).name
    if n == "x_preload.hex":
        return "L0.in", 1
    if n == "head.json":
        return "head.out.argmax", 0
    if n == "logits.npy":
        return "head.out.logits", 5
    if n.startswith("head_die") and n.endswith("_xnorm.hex"):
        return "head.out.xnorm", 4
    if n.endswith("_x.hex") and n.startswith("L"):
        L = int(n[1:3])
        return (f"L{L}.out;L{L + 1}.in" if L < 35 else "L35.out;head.in"), 2
    if "/kv_at_P/" in "/" + rel:
        return f"KV.{n.split('_')[0]}.out", 3
    if "/kv_pre/" in "/" + rel:
        return f"KV.{n.split('_')[0]}.in(history npy)", 9
    if n.endswith(".bin") and n.startswith("L"):
        return f"KV.{n.split('_')[0]}.in(history bin)", 9
    return "meta", 6


def manifest(a) -> int:
    g = a.gold.resolve()
    out = a.out.resolve()
    files = []
    roots = [("gold", g)] + ([("history", a.history.resolve())] if a.history else [])
    for tag, r in roots:
        for p in sorted(x for x in r.rglob("*") if x.is_file() and x.name != "STATUS.md"):
            rel = str(p.relative_to(r))
            ro, pri = role(rel)
            files.append({"tree": tag, "path": rel, "sha256": sha(p), "bytes": p.stat().st_size, "role": ro,
                          "_pri": pri, "_abs": p})
    budget = int(a.budget_mb * 1024 * 1024)
    used = 0
    small = out / "small"
    for f in sorted(files, key=lambda f: (f["_pri"], f["path"])):
        if f["_pri"] < 9 and used + f["bytes"] <= budget:
            dst = small / f["tree"] / f["path"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f["_abs"], dst)
            used += f["bytes"]
            f["committed"] = str(dst.relative_to(ROOT)) if dst.is_relative_to(ROOT) else str(dst)
        else:
            f["committed"] = None
    ver = json.loads((g / "verify.json").read_text()) if (g / "verify.json").exists() else {}
    ref = json.loads(REF.read_text())
    rec = {
        "schema": "opentallas.layerbench.qwen.fixtures.v1", "lane": "LAYERBENCH-QWEN TOK.QW.BENCH.2",
        "at": time.strftime("%FT%TZ", time.gmtime()), "generator": "tools/qwen_layerbench/gen_fixtures.py",
        "generator_commit": git_head(),
        "golden_code": {"oracle": "tools/qwen_hbmacc_position_oracle_gpu.py --device cpu",
                        "oracle_source_sha256": ref.get("oracle_source_sha256")},
        "checkpoint": {"model": "Qwen3-8B (released checkpoint, W12 TP4 stage images)",
                       "prep_sha256": ref.get("prep_sha256"), "tokens_sha256": ref.get("tokens_sha256"),
                       "embedding_npz_sha256": ref.get("embedding_npz_sha256"),
                       "head_program_sha256": ref.get("head_program_sha256")},
        "shape": {"tp": ref.get("tp"), "groups": ref.get("groups"), "layers": ref.get("layers"),
                  "kv_format": ref.get("kv_format"), "position": 8191},
        "verify_vs_committed_digests": {"ref": str(REF.relative_to(ROOT)), "verdict": ver.get("verdict"),
                                        "checked": ver.get("checked"), "mismatches": ver.get("mismatches")},
        "source_trees": {t: str(r) for t, r in roots}, "archive": a.archive,
        "committed_bytes": used, "budget_bytes": budget,
        "files": [{k: v for k, v in f.items() if not k.startswith("_")} for f in files],
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "MANIFEST.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({"files": len(files), "committed": sum(1 for f in files if f["committed"]),
                      "committed_bytes": used, "verify": ver.get("verdict")}))
    return 0 if ver.get("verdict") == "PASS" else 1


def archive(a) -> int:
    dst = f"/archive/opentallas-fixtures/{a.name}"
    host_dst = ARCHIVE.split(":")[0]
    if subprocess.call(ARCHIVE_SSH + [host_dst, f"mkdir -p {dst}"]):
        return 2
    src = a.src
    if ":" in src:                       # fleet host -> archive through this machine (fleet hosts lack the key)
        h, d = src.split(":", 1)
        pipe = (f"ssh {h} 'tar -C {d} -cf - .' | " + " ".join(ARCHIVE_SSH) + f" {host_dst} 'tar -C {dst} -xf -'")
    else:
        pipe = f"tar -C {src} -cf - . | " + " ".join(ARCHIVE_SSH) + f" {host_dst} 'tar -C {dst} -xf -'"
    rc = subprocess.call(["bash", "-o", "pipefail", "-c", pipe])
    print(f"archive {src} -> {host_dst}:{dst} rc={rc}")
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("gold"); s.add_argument("--fx", type=Path, required=True); s.add_argument("--out", type=Path, required=True)
    s.add_argument("--history", type=Path); s.add_argument("--py", default=sys.executable); s.add_argument("--threads", type=int, default=64)
    s = sub.add_parser("manifest"); s.add_argument("--gold", type=Path, required=True); s.add_argument("--history", type=Path)
    s.add_argument("--out", type=Path, required=True); s.add_argument("--budget-mb", type=float, default=5.0)
    s.add_argument("--archive", default=None)
    s = sub.add_parser("archive"); s.add_argument("--src", required=True); s.add_argument("--name", required=True)
    a = ap.parse_args()
    return {"gold": gold, "manifest": manifest, "archive": archive}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
