#!/usr/bin/env python3
"""kc8 (OPT_KC8=1 over kc7): the original gather component gate; no changed oracle/cases."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dsrom_reindex_candidates as gate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--gold", type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise ValueError("fresh output required; prior failures are immutable")
    exp = "rtl/experimental/dsrom_reindex_kc7_20261005/"
    gate.KG_SRC = ["rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv",
                   exp + "ot_hdc_v41x_idx_kgather_kc7.sv",
                   exp + "tb_hdc_v41x_idx_kgather_kc7.sv",
                   "rtl/test/hdc_v41x_idx_kgather.cpp"]
    original_build = gate.kg_build
    gate.kg_build = lambda obj, params: original_build(obj, dict(params, OPT_KC6=1, OPT_KC7=1, OPT_KC8=1))
    try:
        gate.cmd_gather(a)
    except __import__('subprocess').CalledProcessError as e:
        # The original runner captures compiler diagnostics; preserve them.
        for name in ('stdout', 'stderr'):
            data = getattr(e, name)
            if data:
                (a.out / ('compiler_' + name + '.log')).write_bytes(
                    data if isinstance(data, bytes) else data.encode())
        raise
    import json, hashlib
    p = a.out / "gather.json"
    record = json.loads(p.read_text())
    record["selection"] = dict(OPT_KC6=1, OPT_KC7=1, OPT_KC8=1, default_enabled=False)
    record["source_sha256"]["tools/dsrom_reindex_kc8_gate.py"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    p.write_text(json.dumps(record, indent=1) + "\n")
    if record["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
