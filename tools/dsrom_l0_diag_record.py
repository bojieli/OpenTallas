#!/usr/bin/env python3
"""Build the L0 PC24 diagnosis record from a fresh L0DIAG run.

Inputs: the run's diag.log (read-only observer trace from rtl/test/dsrom_sys/l0diag/l0diag_die_rt.cpp built with
-DL0DIAG), its progress.log, and the ORIGINAL r4 run's progress.log (PC-trace identity check).  Output: l0_diag.json.

  python3 tools/dsrom_l0_diag_record.py --run-dir DIR --orig-progress P --meta META.json --out OUT.json
META.json carries provenance (source commit, input hashes, command, host) and is merged verbatim.
"""
import argparse
import json
import re
from pathlib import Path

ST_DECODE = {0: "S_IDLE", 1: "S_DYN", 2: "S_FETCH", 3: "S_WAIT", 4: "S_CAP", 5: "S_DEC", 6: "S_ISSUE",
             7: "S_GO", 8: "S_ACC", 9: "S_RST", 10: "S_COLL_ARM", 11: "S_COLL_WAIT", 12: "S_COLL_HALT",
             13: "S_ROPE_WAIT"}
LIFE_DECODE = {0: "IDLE", 1: "STAGE", 2: "READY", 3: "ARM", 4: "STREAM", 5: "DRAIN", 6: "FAULT"}


def parse_progress(p: Path) -> dict:
    out = {}
    for line in p.read_text().splitlines():
        m = re.match(r"CYC (\d+) wall ([\d.]+) s pc (\d+) (\d+) (\d+) (\d+)", line)
        if m:
            out[int(m.group(1))] = [int(m.group(i)) for i in range(3, 7)]
    return out


def parse_diag(p: Path):
    ch, sn = [], []
    st_names = ct_names = None
    for line in p.read_text().splitlines():
        if line.startswith("# ST"):
            st_names = line.split()[2:]
        elif line.startswith("# CT"):
            ct_names = line.split()[2:]
        elif line.startswith(("CH ", "SN ")):
            t = line.split()
            kv = {}
            for f in t[3:]:
                k, v = f.split("=")
                kv[k] = int(v, 10) if (ct_names and k in ct_names) else int(v, 16)
            (ch if t[0] == "CH" else sn).append((int(t[1]), int(t[2][1:]), kv, line))
    return st_names, ct_names, ch, sn


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--orig-progress", required=True)
    ap.add_argument("--meta", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rd = Path(a.run_dir)
    new = parse_progress(rd / "progress.log")
    orig = parse_progress(Path(a.orig_progress))
    common = sorted(set(new) & set(orig))
    mism = [c for c in common if new[c] != orig[c]]
    st_names, ct_names, ch, sn = parse_diag(rd / "diag.log")

    # full per-die state reconstruction from change lines
    state = [dict() for _ in range(4)]
    first_pc24 = [None] * 4
    last_change = [None] * 4
    last_change_line = [None] * 4
    for cyc, d, kv, line in ch:
        state[d].update(kv)
        last_change[d] = cyc
        last_change_line[d] = line
        if first_pc24[d] is None and state[d].get("pc") == 24:
            first_pc24[d] = cyc
    end_cycle = max(c for c, *_ in sn) if sn else None
    final_sn = {}
    for cyc, d, kv, line in sn:
        if cyc == end_cycle:
            final_sn[d] = kv
    pc24_sn = {}
    for d in range(4):
        if first_pc24[d] is None:
            continue
        cand = [kv for cyc, dd, kv, _ in sn if dd == d and cyc >= first_pc24[d]]
        if cand:
            pc24_sn[d] = cand[0]
    dies = []
    for d in range(4):
        f = final_sn.get(d, {})
        p = pc24_sn.get(d, {})
        ct_delta = {k: f.get(k, 0) - p.get(k, 0) for k in (ct_names or []) if k != "core_cycles"}
        gate = None
        if f:
            gate = {
                "core_state": ST_DECODE.get(f["st"], f["st"]), "pc": f["pc"], "d_unit": f["d_unit"],
                "waited": f["waited"], "idles": f["idles"], "unit_busy": f["unit_busy"],
                "me_ready(att adapter st==A_IDLE)": f["me_ready"], "me_cls": f["me_cls"],
                "kvd_v": f["kvd_v"], "kv_ok(lifecycle READY && !fault)": f["kv_ok"],
                "kv_gate_attention_term": f["kv_gate_cls"], "win_idle(window blocks EMPTY)": f["win_idle"],
                "lifecycle_state": LIFE_DECODE.get(f["life_state"], f["life_state"]),
                "lifecycle_active_gen": f["life_active_gen"], "lifecycle_last_gen": f["life_last_gen"],
                "window_source": {k: f[k] for k in f if k.startswith(("src_", "win_", "sched_", "svc_"))},
                "rope": {k: f[k] for k in f if k.startswith("rope_")},
                "fault": f["fault"], "dbg_fs": f["dbg_fs"],
            }
        dies.append({"die": d, "first_PC24_cycle": first_pc24[d], "last_state_change_cycle": last_change[d],
                     "last_state_change_line": last_change_line[d], "final_gate_state": gate,
                     "counters_at_first_PC24_snapshot": {k: p.get(k) for k in (ct_names or [])},
                     "counters_final": {k: f.get(k) for k in (ct_names or [])},
                     "counter_delta_after_PC24": ct_delta})
    hit = [x for x in first_pc24 if x is not None]
    excerpt_from = (min(hit) - 60) if hit else 0
    rec = json.loads(Path(a.meta).read_text())
    rec.update({
        "schema": "opentallas.rtl.dsrom_l0_pc24_diag.v1",
        "cycles_reached": end_cycle,
        "pc_trace_identity": {"compared_samples": len(common), "mismatches": len(mism),
                              "first_mismatch": mism[0] if mism else None,
                              "range": [common[0], common[-1]] if common else None,
                              "identical": bool(common) and not mism},
        "observer_fields": {"ST": st_names, "CT": ct_names},
        "dies": dies,
        "trace_excerpt": [ln for cy, _d, _kv, ln in ch if cy >= excerpt_from][:80],
    })
    Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({"cycles": end_cycle, "pc_identical": rec["pc_trace_identity"]["identical"],
                      "first_pc24": first_pc24, "last_change": last_change}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
