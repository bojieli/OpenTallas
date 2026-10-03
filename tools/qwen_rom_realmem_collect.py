#!/usr/bin/env python3
"""Collect the REAL_MEM runtime records into results/rtl/qwen_rom_real_memory_20261003/.

Reads the driver records (tools/qwen_rom_rt_token_w12_rm.py --result) of the runs, the
position-oracle records, and writes:
  runs/<name>.json             the driver record (unchanged) and runs/<name>_token.log (stage/memstat lines)
  oracle/<name>/               oracle.json and the per-layer golden X hex of the recorded position
  summary.json                 per run and layer: cycles, memory stalls by cause, the A/B delta against the
                               KV_IDEAL reference run at the same position, bit-exact verdicts
Failed verdicts are recorded as they are (never overwritten into a pass).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/rtl/qwen_rom_real_memory_20261003"


def preserve(path, data):
    """Run evidence is immutable, including failed verdicts."""
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"refusing to overwrite evidence: {path}")
    else:
        path.write_bytes(data)


def comparable(real, ideal):
    return (real.get("status") == ideal.get("status") == "pass"
            and real.get("source_stable") is True and ideal.get("source_stable") is True
            and real.get("configuration") == "REAL_MEM"
            and ideal.get("configuration", "").startswith("KV_IDEAL")
            and all(real.get(k) is not None and real.get(k) == ideal.get(k)
                    for k in ("position", "token", "source_sha256", "binary_sha256",
                              "generated_core_sha256", "stage_image_sha256", "kv_history_sha256",
                              "oracle_json_sha256", "design_point", "stages_run")))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", action="append", default=[], help="name=driver_result.json[:token.log]")
    ap.add_argument("--oracle", action="append", default=[], help="name=oracle_root:P")
    ap.add_argument("--ideal-baseline", type=int, default=4668, help="retained ideal-memory layer cycles (L1..L35)")
    ap.add_argument("--out", type=Path, default=OUT, help="collection directory (use a separate directory for historical attempts)")
    a = ap.parse_args()
    out = a.out
    (out / "runs").mkdir(parents=True, exist_ok=True)
    (out / "oracle").mkdir(parents=True, exist_ok=True)
    runs = {}
    for spec in a.run:
        name, rest = spec.split("=", 1)
        res, _, log = rest.partition(":")
        rec = json.loads(Path(res).read_text())
        preserve(out / "runs" / f"{name}.json", Path(res).read_bytes())
        if log:
            keep = [ln for ln in Path(log).read_text().splitlines()
                    if re.match(r"(STAGE|MEMSTAT|stage |QWEN_ROM_REALMEM|MEMORY FAULT|TOKEN FAULT|models|images|FATAL|timeout)", ln)]
            preserve(out / "runs" / f"{name}_token.log", ("\n".join(keep) + "\n").encode())
        runs[name] = rec
    for spec in a.oracle:
        name, rest = spec.split("=", 1)
        root, p = rest.rsplit(":", 1)
        d = out / "oracle" / name
        d.mkdir(parents=True, exist_ok=True)
        preserve(d / "oracle.json", (Path(root) / "oracle.json").read_bytes())
        for f in sorted((Path(root) / f"P{p}").glob("L*_die*_x.hex")) + [Path(root) / f"P{p}" / "x_preload.hex",
                                                                         Path(root) / f"P{p}" / "embedding_row.json"]:
            preserve(d / f.name, f.read_bytes())
        kd = d / "kv_at_P"
        kd.mkdir(exist_ok=True)
        for f in sorted((Path(root) / f"P{p}" / "kv_at_P").glob("*.json")):
            preserve(kd / f.name, f.read_bytes())
    summary = {"schema": "opentallas.qwen-rom-realmem-summary.v1", "ideal_memory_baseline_cycles_per_layer": a.ideal_baseline,
               "runs": {}}
    for name, rec in runs.items():
        st = rec.get("stages", {})
        rows = {}
        for sname, s in st.items():
            mem = s.get("memory", {})
            worst = {}
            for k in ("stall_kv", "stall_drain", "stall_bridge", "stall_retire", "stall_mem", "kvok_low_with_desc", "drain_low",
                      "fill_cycles", "fill_sectors", "wr_sectors", "wr_lat_max", "rsp_tile_stall"):
                vals = [m.get(k) for m in mem.values() if m.get(k) is not None]
                if vals:
                    worst[k] = max(vals)
            rows[sname] = {"cycles": s.get("cycles"), "memory_max_over_dies": worst}
        summary["runs"][name] = {"status": rec.get("status"), "configuration": rec.get("configuration"),
                                 "source_stable": rec.get("source_stable"), "binary_sha256": rec.get("binary_sha256"),
                                 "returncode": rec.get("returncode"), "total_cycles": rec.get("total_cycles"),
                                 "position": rec.get("position"), "token": rec.get("token"),
                                 "layer_x_exact": {k: v["mismatches"] == 0 for k, v in rec.get("layer_x_checks", {}).items()},
                                 "token_kv_writeback_exact": {k: v["k_mismatches"] == 0 and v["v_mismatches"] == 0
                                                              for k, v in rec.get("token_kv_writeback_checks", {}).items()},
                                 "first_mismatches": {k: v["first_mismatch"] for k, v in rec.get("layer_x_checks", {}).items()
                                                      if v.get("first_mismatch")},
                                 "stages": rows}
    # A/B: REAL_MEM minus KV_IDEAL at the same position
    ab = {}
    for name, r in summary["runs"].items():
        if r["configuration"] != "REAL_MEM":
            continue
        for other, o in summary["runs"].items():
            if comparable(runs[name], runs[other]):
                if name in ab:
                    raise ValueError(f"multiple qualified KV_IDEAL references for {name}")
                ab[name] = {s: (r["stages"][s]["cycles"] - o["stages"][s]["cycles"])
                            for s in r["stages"] if s in o["stages"] and r["stages"][s]["cycles"] is not None
                            and o["stages"][s]["cycles"] is not None}
    summary["real_minus_ideal_cycles"] = ab
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: {s: v["cycles"] for s, v in r["stages"].items()} for k, r in summary["runs"].items()}, indent=1))
    print(json.dumps(ab, indent=1))


if __name__ == "__main__":
    main()
