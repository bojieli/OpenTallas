#!/usr/bin/env python3
"""Assemble results/rtl/dsrom_system_rtl_20261003/levers/phase_merge.json (lever item 1, same-x phase merge).

  python3 tools/dsrom_lever_record_phase_merge.py --emitter EMIT.json --images-off DIR... --images-on DIR...
      --flat FLAT_r0.json ... --model MODEL.json --ab AB.json --meta META.json --out OUT.json

Inputs are the outputs of tools/dsrom_lever_phase_merge.py (emitter, images, model, ab) and
tools/dsrom_lever_phase_merge_flat.py (score); META carries provenance (hosts, UTC times, commands) verbatim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ["tools/dsrom_lever_phase_merge.py", "tools/dsrom_lever_phase_merge_flat.py",
         "tools/dsrom_lever_record_phase_merge.py", "rtl/test/dsrom_sys/levers/phase_merge_flat_bench.cpp",
         "tools/hdc_replay_v41.py", "tools/hdc_isa_v41.py", "tools/hdc_timing_v41x.py",
         "tools/v41_die_images_w17w10.py", "tools/w17_runtime_v41_die_images.py", "tools/hdc_golden_v41.py"]


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pc_changes(run_log: Path) -> dict:
    """Exact cycle at which each die first shows each PC (PCCHG lines of rtl/test/dsrom_sys/levers/pm_die_rt.cpp)."""
    out = {}
    for ln in run_log.read_text().splitlines():
        t = ln.split()
        if len(t) == 4 and t[0] == "PCCHG":
            out.setdefault(int(t[2][1:]), {}).setdefault(int(t[3]), int(t[1]))
    return out


def pclog_ab(off_dir: Path, on_dir: Path, merged_new_pcs: list[int]) -> dict:
    """Per original PC: the cycle every die entered it, OFF vs ON (ON pcs mapped back to the original numbering)."""
    to_orig = lambda n: n + sum(1 for x in merged_new_pcs if x < n)  # noqa: E731
    off, on = pc_changes(off_dir / "run.log"), pc_changes(on_dir / "run.log")
    per = {}
    for d in sorted(off):
        o = off[d]
        n = {to_orig(k): v for k, v in on.get(d, {}).items()}
        for pc in sorted(set(o) | set(n)):
            per.setdefault(str(pc), {})[f"d{d}"] = dict(off=o.get(pc), on=n.get(pc),
                                                        saved=(o[pc] - n[pc]) if pc in o and pc in n else None)
    tail = {}
    for f in ("run.log",):
        for k, dd in (("off", off_dir), ("on", on_dir)):
            tail[k] = [ln for ln in (dd / f).read_text().splitlines() if not ln.startswith(("CYC ", "PCCHG", "\t"))][-12:]
    return dict(per_pc_entry_cycle=per, run_log_tail=tail,
                vm_sha256={k: {p.name: sha(p) for p in sorted(dd.glob("vm*.hex"))} for k, dd in
                           (("off", off_dir), ("on", on_dir))})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emitter", type=Path, required=True)
    ap.add_argument("--images-off", type=Path, nargs="+", required=True)
    ap.add_argument("--images-on", type=Path, nargs="+", required=True)
    ap.add_argument("--program-off", type=Path, nargs="+", required=True, help="program subcommand outputs")
    ap.add_argument("--flat", type=Path, nargs="+", required=True)
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--ab", action="append", default=[], help="NAME=PATH of a dsrom_lever_phase_merge ab record")
    ap.add_argument("--pclog", action="append", default=[], help="NAME=OFFDIR,ONDIR of PM_PCLOG die runs")
    ap.add_argument("--meta", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    emit = json.loads(a.emitter.read_text())
    imgs = {}
    for arm, dirs in (("off", a.images_off), ("on", a.images_on)):
        for d in dirs:
            j = json.loads((d / "lever_images.json").read_text())
            for r, v in j["ranks"].items():
                imgs.setdefault(arm, {})[r] = dict(ops=v["ops"], ops_out=v["ops_out"], phases=v["phases"],
                                                   merges=len(v["merges"]),
                                                   field_prog_weights_byte_identical_to_source=v[
                                                       "field_files_identical_to_source"],
                                                   nonidentical=v["nonidentical"],
                                                   merged_phase_model=[p for p in v["phase_model"]
                                                                       if any(p["pc"] == m["pc_first"] for m in v["merges"])])
    progs = [json.loads(p.read_text()) for p in a.program_off]
    flat = [json.loads(p.read_text()) for p in a.flat]
    model = json.loads(a.model.read_text())
    abs_ = {n: json.loads(Path(p).read_text()) for n, p in (x.split("=", 1) for x in a.ab)}
    meta = json.loads(a.meta.read_text())
    lev0 = json.loads((a.images_on[0] / "lever_images.json").read_text())
    new_pcs = [m["new_pc"] for m in next(iter(lev0["ranks"].values()))["merges"]]
    pcl = {n: pclog_ab(*map(Path, v.split(",")), new_pcs) for n, v in (x.split("=", 1) for x in a.pclog)}
    off_ok = (all(v["off_identical"] for v in emit.values()) and all(p["byte_identical"] for p in progs)
              and all(v["field_prog_weights_byte_identical_to_source"] for v in imgs["off"].values()))
    flat_ok = all(f["status"] == "pass" and f["source_stable"] for f in flat)
    ab_ok = {}
    for n, ab in abs_.items():
        rows = ab.get("merged_rows_vs_expect_vm", {})
        ab_ok[n] = (all(ab["vm_bit_identical_off_vs_on"].values()) and
                    all(v["mismatches_vs_expect"] == 0 for r in rows.values() for v in r.values()) and bool(rows))
        for k in ("off", "on"):
            ab[k].pop("progress", None)
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    f0 = flat[0]
    rec = dict(
        schema="opentallas.dsrom_sys.lever.phase_merge.v1",
        lever="same-x phase merge (free-levers audit 2026-10-03 item 1): w1+w3 of the shared and each routed expert, "
              "wq_a+wkv, issued as ONE ROM-field phase instead of two",
        class_="A (bit-exact; same weights, same x, same per-row reduction order; only the phase grouping changes)",
        default="off",
        worktree_head=head,
        source_sha256={t: sha(ROOT / t) for t in TOOLS},
        a_default_off=dict(
            pass_=off_ok,
            emitter={k: dict(ops=v["ops"], off_identical=v["off_identical"], ops_merged=v["ops_merged"],
                             merges=[dict(pc=[m["pc_first"], m["pc_second"]], rows=m["rows"], tag=m["tag"])
                                     for m in v["merges"]]) for k, v in emit.items()},
            program_off_byte_identical=[p["byte_identical"] for p in progs],
            images=imgs),
        b_flat_field_rtl=dict(
            pass_=flat_ok,
            rtl="rtl/w17_runtime/v41die/ot_v41_fieldtop (flat W17-runtime ROM field, the runtime gate's reference)",
            params=f0["params"], rows_per_matrix=dict(fp4=f0["rows"], fp8=f0.get("rows_fp8")),
            per_rank={str(f["rank"]): dict(status=f["status"], golden_rows=f["arms"]["off"]["golden_rows"],
                                           golden_mismatch_off=f["arms"]["off"]["golden_mismatch"],
                                           golden_mismatch_on=f["arms"]["on"]["golden_mismatch"],
                                           unexpected_writes=[f["arms"]["off"]["unexpected_writes"],
                                                              f["arms"]["on"]["unexpected_writes"]],
                                           total_saved_cycles=f["total_saved_cycles"],
                                           pairs=[{k: p[k] for k in ("pc", "tag", "fmt", "rows", "K", "split_wall_cycles",
                                                                     "merged_wall_cycles", "saved_cycles",
                                                                     "golden_mismatch_split", "golden_mismatch_merged",
                                                                     "rows_bit_identical_split_vs_merged")}
                                                  for p in f["pairs"]],
                                           host=f["host"], steps=f["steps"], simulator=f["simulator"])
                      for f in flat}),
        c_model_attribution=model,
        c_die_runtime_ab=abs_, c_die_runtime_ab_pass=ab_ok, c_die_runtime_pc_trace=pcl,
        meta=meta)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=str).replace('"pass_"', '"pass"').replace('"class_"', '"class"')
                     + "\n")
    print(dict(a=off_ok, b=flat_ok, ab=ab_ok))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
