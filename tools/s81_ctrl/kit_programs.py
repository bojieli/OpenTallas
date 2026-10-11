#!/usr/bin/env python3
"""Program-memory images of the S81 stage controller under option A (mtp-lead/kitseq, 2026-10-11).

MAIN DECISION 10-10 22:02 (option A): the WFC kit is the single stage controller; ot_s81_hop_tx (the hop port's
framer) is RETIRED -- the hand-off is the kit's own outbound path, which starts at the kit's k_done.  The hop entry of a
stage program stays in the program as the KIT HAND-OFF POINT: engine port 7 is served inside the controller slab
(rtl/dsrom_sys/s81_ctrl/ot_s81_kit_seq.sv) -- when the hop job's predecessor has completed it raises the kit DONE
(t_kd) and returns the hop's completion to ot_s81_stage_seq.  So the kit's DONE fires at the golden hop start (the
composition's hand-off point, not at the end of every op: S029's L20.attn.cand.* run past the hop) and the jobs that
follow the hop in the program keep running while the kit sends.

pw_d = {eng[3:0], arg[23:0]}; for engine jobs arg is the compiler-owned native descriptor (tools/s81_ctrl/
native_descriptors.py; here the op index is used as a placeholder tag, as tb_s81_stage_seq does); for the hop entry
arg = {16'b0, has_pred, pred_op[6:0]} (every published hop has <= 1 in-stage predecessor: checked).  Engine port 11
(spare) must carry no job (checked).

    python3 tools/s81_ctrl/kit_programs.py [--out results/rtl/s81_kitseq_20261011/programs]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import stage_programs as SP

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "results/rtl/s81_ctrl_20261008/programs"
HOP, SPARE = SP.ENG["hop"], SP.ENG["spare"]


def hop_arg(o):
    assert len(o["preds"]) <= 1, o["id"]
    return (0x80 | o["preds"][0]) if o["preds"] else 0


def image(prog):
    words = []
    for o in prog["ops"]:
        assert o["port"] != SPARE, (prog["stage"], o["id"])
        arg = hop_arg(o) if o["port"] == HOP else (o["op"] ^ 0x5A0000)
        words.append((o["port"] << 24) | arg)
    return words


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "results/rtl/s81_kitseq_20261011/programs")
    a = ap.parse_args()
    (a.out / "pmem").mkdir(parents=True, exist_ok=True)
    idx = []
    for f in sorted(SRC.glob("S*.json")):
        p = json.loads(f.read_text())
        w = image(p)
        (a.out / "pmem" / f"{p['stage']}.hex").write_text("".join(f"{x:07x}\n" for x in w))
        hops = [o for o in p["ops"] if o["port"] == HOP]
        assert len(hops) == 1, p["stage"]
        h = hops[0]
        idx.append(dict(stage=p["stage"], kind=p["kind"], n_jobs=len(w), makespan=p["makespan"], handoff_at=h["start"],
                        after_handoff=sum(1 for o in p["ops"] if o["end"] > h["start"] and o["port"] != HOP),
                        hop_pred=h["preds"]))
    rec = dict(schema="opentallas.s81-kitseq.pmem.v1", tool="tools/s81_ctrl/kit_programs.py",
               source=str(SRC.relative_to(ROOT)),
               source_index_sha256=hashlib.sha256((SRC / "index.json").read_bytes()).hexdigest(),
               rule="hop entry = kit hand-off point (arg {has_pred, pred_op}); spare port unused; one hop per program",
               n_programs=len(idx), max_jobs=max(x["n_jobs"] for x in idx), programs=idx)
    (a.out / "index.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(f"{len(idx)} pmem images, max jobs {rec['max_jobs']}, "
          f"{sum(1 for x in idx if x['after_handoff'])} programs with jobs running past the hand-off")


if __name__ == "__main__":
    main()
