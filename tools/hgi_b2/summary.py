#!/usr/bin/env python3
"""Collect B2 export verdicts into results/rtl/hbm_b2_1012/ (summary.json + per-vehicle placement / verdict copies).

    python3 tools/hgi_b2/summary.py --host ot-epyc4 --root /srv/opentallas-scratch2/claude/b2c/vec VEC_DIR [VEC_DIR ...]
(VEC_DIR = a local copy of an export dir; --root / --host name where the full vectors live.)"""
import argparse
import json
import shutil
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "results/rtl/hbm_b2_1012"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vec", nargs="+", type=Path)
    ap.add_argument("--host", required=True)
    ap.add_argument("--root", required=True)
    ap.add_argument("--exposed", type=Path, help="json {vehicle dir name: harness_b2 traffic result line / numbers}")
    a = ap.parse_args()
    exposed = json.loads(a.exposed.read_text()) if a.exposed else {}
    rows = []
    for d in a.vec:
        v = json.loads((d / "b2/verdict.json").read_text())
        p1 = json.loads((d / "b2/pass1.json").read_text())
        meta = json.loads((d / "meta.json").read_text())
        recs = json.loads((d / "b2/records_b2.json").read_text())
        moe = [r for r in recs if r["unit"] == "SM" and "expert" in r["tag"]]
        rows.append(dict(vehicle=d.name, model=meta.get("model"), exact=v["exact"], violations=v["violations"],
                         mutant=v.get("mutant"), golden=meta.get("layer_out_exact_vs_qwen_r25",
                                                                 meta.get("layer_verdict_sim_vs_golden")),
                         ranks=meta.get("group"), dispatched=len(meta["records"]), capacity=v["capacity"],
                         modes=v["modes"], stats=v["stats"], ring_words=v["ring_words"], ring_cycles=v.get("ring_cycles"),
                         work_per_cluster=v["work_per_cluster"], promoted_to_mirror=v.get("promoted_to_mirror"),
                         moe_expert_records=len(moe), moe_rows_per_cluster=[sum(r["work"][str(q)] for r in moe)
                                                                            for q in range(4)] if moe else None,
                         wall_s=[p1["wall_s"], v.get("pass2_wall_s")],
                         location=f"{a.host}:{a.root}/{d.name}",
                         first_violations=v["first_violations"][:5]))
        if a.exposed and d.name in exposed:
            rows[-1]["exposed"] = exposed[d.name]
        if not v.get("mutant"):
            dst = OUT / d.name
            dst.mkdir(parents=True, exist_ok=True)
            # placement.json = rank 0's segment table in SPEC.md 2a addresses (pass 2 writes it from the per-die
            # liveness placement; the per-die classes stay at location: b2/cls_per_die.npz)
            for f in ("verdict.json", "pass1.json", "slice.npy", "placement.json"):
                shutil.copy(d / "b2" / f, dst / f)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(dict(
        schema="opentallas.hgi_b2.summary.v1",
        files=("per vehicle at location: flat layout (meta.json, image.bin, vm0.bin, vm_final.bin, hbm.bin, vmw.bin, "
               "hbmw.bin, coll_*.bin: the fallback, unchanged) + b2/ (placement.json = the address->slice segment map, "
               "vm0_s{q}.bin / vm_final_s{q}.bin = slice q physical images [65,536 local | 32,768 mirror], "
               "records_b2.json = per executed record: mode, chain, per-cluster work and physical sub-descriptors, "
               "verdict.json, cls_per_die.npz = word classes per die)"),
        vehicles=rows), indent=1) + "\n")
    for r in rows:
        rc = r["ring_cycles"] or {}
        print(r["vehicle"], "exact", r["exact"], "viol", r["violations"], "mutant", r["mutant"], "fits", r["capacity"]["fits"],
              "serial ring/layer", rc.get("max_layer_cycles"), "EXPOSED", (r.get("exposed") or {}).get("exposed"),
              "budget", rc.get("budget_cycles_per_layer"))


if __name__ == "__main__":
    main()
