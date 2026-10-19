#!/usr/bin/env python3
"""HBM-NEXT-VEH (10-19): the next-die AR layer path must reproduce the d4g AR layer.

Single-user AR on the P = 4 die issues P = 1 records (STUDY: DS AR 1,905.4 at every P with L = 4), so its RTL path is
the d4g path: the forked vehicle (tools/hbm_next/vehicle = 3-way merge of claude/lb2-hbm-cds-1018 @63ef9558e and
codex/hbm-vehicle-recovery-1018 @1da79c281 over 128031c2a) must emit BYTE-IDENTICAL slice payloads for the d4g DS L0
fixture replay.  This tool re-runs the forked compiler (layer_images) + TB generator (gen_slice_tb) on the committed
released-checkpoint fixtures and compares every payload file against the d4g receipt
results/rtl/hbm_ds_layer_tput_1018/vehicle_recovery_1018/ds_l0_fixture_replay.json (payload_sha256), fail-closed.
The RTL cycles of this replay come from the d4g SW-slice binary (sw5 / sw5e) -- the same binary serves both dies, so
no second 240 GB build is launched (AGENTS.md: reuse live pinned jobs; simulate the minimum component).

    PYTHONPATH=tools python3 tools/hbm_next/vehicle/ar_repro.py --work DIR --out results/arch/hbm_next_1019/veh/ar_repro.json
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REC = ROOT / "results/rtl/hbm_ds_layer_tput_1018"
# copy of codex/hbm-vehicle-recovery-1018@1da79c281:results/rtl/hbm_ds_layer_tput_1018/vehicle_recovery_1018/ (not in base)
RECEIPT = ROOT / "results/arch/hbm_next_1019/veh/d4g_receipt/ds_l0_fixture_replay.json"
PAYLOAD = ("val.mem", "hdr.mem", "vm_pre.txt", "msk.mem")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    rc = json.loads(RECEIPT.read_text())
    bnd = REC / "slice_sw/boundary.json"
    env = {"PYTHONPATH": str(ROOT / "tools"), "PATH": "/usr/bin:/bin"}
    a.work.mkdir(parents=True, exist_ok=True)
    img = subprocess.run([sys.executable, "-m", "hbm_next.vehicle.layer_images", "--design", "ds", "--layer", "0",
                          "--boundary", str(bnd), "--fixtures", str(REC / "fixtures/L00"), "--out", str(a.work / "img")],
                         env=env, cwd=ROOT, capture_output=True, text=True, check=True)
    summary = json.loads(img.stdout.strip().splitlines()[-1])
    subprocess.run([sys.executable, str(ROOT / "tools/hbm_next/vehicle/gen_slice_tb.py"), "--boundary", str(bnd),
                    "--replay", str(a.work / "img/replay.json"), "--out", str(a.work / "tb")], env=env, cwd=ROOT,
                   capture_output=True, text=True, check=True)
    rd = next((a.work / "tb/replay").iterdir())
    idx = json.loads((rd / "index.json").read_text())
    files = {f: dict(fork=sha(rd / f), d4g=rc["payload_sha256"][f]) for f in PAYLOAD}
    for v in files.values():
        v["identical"] = v["fork"] == v["d4g"]
    counts_eq = summary["counts"] == rc["all_record_counts"]
    idx_eq = all(idx[k] == rc["index"][k] for k in ("events", "drives", "checks", "vm_preload_words", "records"))
    ok = all(v["identical"] for v in files.values()) and counts_eq and idx_eq and sha(bnd) == rc["boundary_sha256"]
    out = dict(schema="opentallas.hbm_next_1019.veh.ar_repro.v1", lane="HBM-NEXT-VEH", rule=__doc__,
               verdict="PASS" if ok else "FAIL",
               scope="compiler/TB side of the AR layer path (DS L0, 8 SU.VOP records on released-checkpoint fixtures); "
                     "RTL cycles = the d4g SW-slice run (pending), not claimed here",
               receipt=str(RECEIPT.relative_to(ROOT)), receipt_sha256=sha(RECEIPT),
               boundary_sha256=sha(bnd), payload=files, record_counts=summary["counts"], record_counts_equal=counts_eq,
               index={k: idx[k] for k in ("events", "drives", "checks", "vm_preload_words", "records")},
               index_equal=idx_eq, index_json_note="index.json differs from the receipt only by the scope fields "
               "(qualifies_native_* = false, state_seed_provenance) added after the receipt (codex 1da79c281)",
               forked_from=dict(cds="claude/lb2-hbm-cds-1018@63ef9558e", codex="codex/hbm-vehicle-recovery-1018@1da79c281",
                                merge_base="128031c2a"),
               fork_sha256={p.name: sha(p) for p in sorted((ROOT / "tools/hbm_next/vehicle").glob("*"))
                            if p.is_file()})
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(out["verdict"], {f: v["identical"] for f, v in files.items()}, counts_eq, idx_eq)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
