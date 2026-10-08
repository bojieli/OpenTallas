#!/usr/bin/env python3
"""Exactness reference fixtures: verify regenerated goldens against the COMMITTED oracle digests, derive the Qwen ROM
KV history from the TP4 gold, and mark fixture trees KEEP for the fleet sweeper.

    fixtures.py verify  --gold DIR --ref results/.../oracle.json [--out verify.json]
    fixtures.py history --gold DIR/P8191 --out DIR
    fixtures.py keep    --root DIR --note TEXT

The goldens are deterministic (tools/qwen_hbmacc_position_oracle_gpu.py, ISA golden on the local GPU, bit-checked
primitives), so a regenerated file is accepted only when its sha256 equals the digest committed with the published
evidence (results/rtl/qwen_hbmacc_p8191_20261004/gold_tp{2,4}/oracle*.json): every layer X, pre-P KV, current-token
KV, the x preload, the head Xnorm/logits/argmax.  The KV history (qwen-P8191-full36-history-r1/history in the
published Qwen ROM token) is the TP4 gold's kv_pre as raw little-endian u32 (tools/qwen_rom_rt_token_stream4_w12.py),
pinned by results/rtl/qwen_rom_combined_p0_20261005/linked_expected/expected.json (L0 die0).

Sweeper rule (tools/fleet/sweep.py): a deletion unit is kept when a STATUS.md sits inside it (find -maxdepth 4), and
units are whole dirs at most 3 levels under a sweep root, so `keep` writes a STATUS.md into EVERY directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HISTORY_L0_DIE0 = "190fcd6d3cd94bba849b4082990090cbedba5ddd9a756f82624d225f5c721876"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def verify(a):
    ref = json.loads(a.ref.read_text())
    gold = a.gold.resolve()
    rows, bad, checked = [], [], 0
    for pos, want in ref["per_position"].items():
        pdir = gold / f"P{pos}"
        files = {"x_preload_sha256": [(pdir / "x_preload.hex", want["x_preload_sha256"])]}
        for key, v in want["layer_x_sha256"].items():
            n, d = key[1:].split("_die")
            files.setdefault("layer_x", []).append((pdir / f"L{int(n):02d}_die{d}_x.hex", v))
        for key, v in want["kv_pre_sha256"].items():
            files.setdefault("kv_pre", []).append((pdir / "kv_pre" / f"{key}.npy", v))
        for key, v in want["kv_at_P_sha256"].items():
            files.setdefault("kv_at_P", []).append((pdir / "kv_at_P" / f"{key}.json", v))
        if "head" in want:
            h = want["head"]
            for k, v in h.items():
                if k.startswith("head_die"):
                    files.setdefault("head_xnorm", []).append((pdir / f"{k}_xnorm.hex", v["xnorm_sha256"]))
            files["logits"] = [(pdir / "logits.npy", h["logits_sha256"])]
            got = json.loads((pdir / "head.json").read_text()) if (pdir / "head.json").exists() else {}
            for k in ("next_token", "next_logit_bits"):
                checked += 1
                if got.get(k) != h[k]:
                    bad.append(f"P{pos} head {k}: {got.get(k)} != {h[k]}")
            for k, v in h.items():
                if k.startswith("head_die"):
                    for f in ("argmax_local", "logit_bits", "row0", "rows"):
                        checked += 1
                        if got.get(k, {}).get(f) != v[f]:
                            bad.append(f"P{pos} {k}.{f}: {got.get(k, {}).get(f)} != {v[f]}")
        if "token" in want:
            checked += 1
        for kind, lst in files.items():
            n_ok = 0
            for p, v in lst:
                checked += 1
                g = sha(p) if p.exists() else None
                if g != v:
                    bad.append(f"{p.relative_to(gold)}: {g} != {v}")
                else:
                    n_ok += 1
            rows.append({"position": pos, "kind": kind, "files": len(lst), "match": n_ok})
    top = json.loads((gold / "oracle.json").read_text()) if (gold / "oracle.json").exists() else {}
    for k in ("tokens_sha256", "embedding_npz_sha256", "head_program_sha256", "layers", "tp", "groups",
              "kv_format", "su_width_arith", "oracle_source_sha256"):
        checked += 1
        if top.get(k) != ref.get(k):
            bad.append(f"oracle.json {k}: {top.get(k)} != {ref.get(k)}")
    rec = {"schema": "opentallas.exactness.fixture-verify.v1", "at": time.strftime("%FT%TZ", time.gmtime()),
           "gold": str(gold), "ref": str(a.ref), "ref_sha256": sha(a.ref), "checked": checked,
           "mismatches": len(bad), "first_mismatches": bad[:40], "kinds": rows,
           "verdict": "PASS" if not bad else "FAIL"}
    out = a.out or gold / "verify.json"
    out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: rec[k] for k in ("gold", "checked", "mismatches", "verdict")}))
    return 0 if not bad else 1


def history(a):
    src = a.gold.resolve() / "kv_pre"
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    man = {}
    for p in sorted(src.glob("L*_die*.npy")):
        b = out / (p.stem + ".bin")
        np.load(p).astype("<u4").tofile(b)
        man[p.stem] = {"bin_sha256": sha(b), "npy_sha256": sha(p)}
    if len(man) != 144:
        raise SystemExit(f"expected 144 layer-die KV histories, got {len(man)}")
    ok = man["L0_die0"]["bin_sha256"] == HISTORY_L0_DIE0
    (out / "MANIFEST.json").write_text(json.dumps({
        "schema": "opentallas.exactness.qwen-kv-history.v1", "derived_from": str(src),
        "rule": "np.load(kv_pre/L{n}_die{d}.npy).astype('<u4').tofile(L{n}_die{d}.bin)",
        "pin": {"L0_die0": HISTORY_L0_DIE0,
                "source": "results/rtl/qwen_rom_combined_p0_20261005/linked_expected/expected.json"},
        "pin_match": ok, "files": man}, indent=1) + "\n")
    print(json.dumps({"history": str(out), "files": len(man), "pin_match": ok}))
    return 0 if ok else 1


def keep(a):
    root = a.root.resolve()
    text = (f"# KEEP -- exactness reference fixture (do not sweep)\n\n{a.note}\n\n"
            f"Owner: exactness harness (tools/exactness, benches.json). Regenerate: tools/exactness/regen_fixtures.sh.\n"
            f"Marked {time.strftime('%Y-%m-%d %H:%M %Z')}.\n")
    n = 0
    for d in [root, *sorted(p for p in root.rglob("*") if p.is_dir() and not p.is_symlink())]:
        (d / "STATUS.md").write_text(text)
        n += 1
    print(f"KEEP STATUS.md in {n} dirs under {root}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--gold", type=Path, required=True)
    v.add_argument("--ref", type=Path, required=True)
    v.add_argument("--out", type=Path)
    h = sub.add_parser("history")
    h.add_argument("--gold", type=Path, required=True)
    h.add_argument("--out", type=Path, required=True)
    k = sub.add_parser("keep")
    k.add_argument("--root", type=Path, required=True)
    k.add_argument("--note", required=True)
    a = ap.parse_args()
    sys.exit({"verify": verify, "history": history, "keep": keep}[a.cmd](a))


if __name__ == "__main__":
    main()
