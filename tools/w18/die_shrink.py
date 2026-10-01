#!/usr/bin/env python3
"""W18: shrink the V4.1 ROM layer die to the product's pair need plus a margin (root, 2026-09-30).

The product owner file (results/arch/v41_stage_owner_product.json: 37 stages / 188 dies) needs at most
``--pairs`` pair slots per layer die, ``--bf16-pairs`` of them BF16 column pairs.  The die keeps its aspect
ratio and every fixed block (hub, HBM PHYs and service bands, SerDes, UCIe); only the ROM field shrinks.
Scale s is bisected so that the real-element floorplan (tools/w18/die_floorplan.py) closes at
need x (1 + margin) for BOTH kinds, with the pack legal (no overlaps) and the HBM PHY edge bound kept
(two PHYs per N/S edge: die width >= 2 PHY widths + keep-outs; SerDes / UCIe columns fit the height).

    python3 tools/w18/die_shrink.py --pair-lef Q.lef [--bf16-lef B.lef] --pairs 5289 --bf16-pairs 1024 \
        --work W --output R.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE_W, BASE_H = 31799.952, 25628.4
QP = "results/physical_abi3/asap7/chip/v41_w10_elem/pair_final_physical_p5.json"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def trial(s: float, a, work: Path) -> dict:
    tag = f"{s:.4f}"
    pk, fp = work / f"pack_{tag}.json", work / f"floorplan_{tag}.json"
    need = math.ceil(a.pairs * (1 + a.margin))
    nbf = math.ceil(a.bf16_pairs * (1 + a.margin))
    r = subprocess.run([sys.executable, str(ROOT / "tools/w18/pack.py"), "--hbm-phy", a.hbm_phy,
                        "--die-w-um", f"{BASE_W * s:.3f}", "--die-h-um", f"{BASE_H * s:.3f}",
                        "--q-pair", a.q_pair, "--bf-pair", a.q_pair, "--output", str(pk), "--svg-dir", str(work),
                        *(["--hub", str(a.hub)] if a.hub else []), *(["--vm-in-su"] if a.vm_in_su else []),
                        *(["--c-rotate-strip-mm2", str(a.c_rotate_strip_mm2)] if a.c_rotate_strip_mm2 else []),
                        *(["--c-rotate-centre"] if a.c_rotate_centre else []),
                        *(["--c-rotate-shape", a.c_rotate_shape] if a.c_rotate_strip_mm2 else [])],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode or not pk.exists():
        return dict(s=s, ok=False, why="pack failed: " + r.stderr[-300:])
    p = json.loads(pk.read_text())
    lg = p["legality"]
    cmd = [sys.executable, str(ROOT / "tools/w18/die_floorplan.py"), "--pack", str(pk), "--pair-lef", str(a.pair_lef),
           "--pairs-needed", str(need), "--output", str(fp)]
    if a.bf16_lef:
        cmd += ["--bf16-lef", str(a.bf16_lef), "--bf16-pairs", str(nbf)]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        return dict(s=s, ok=False, why="floorplan failed: " + r.stderr[-300:])
    f = json.loads(fp.read_text())
    g = p["geometry"]
    ok = lg["legal"] and lg["overlaps"] == 0 and f["capacity"]["closes"]
    return dict(s=s, ok=ok, die_um=[g["die_w_um"], g["die_h_um"]], die_mm2=g["die_mm2"], legal=lg["legal"],
                overlaps=lg["overlaps"], errors=lg["errors"][:3], slots=f["capacity"]["pair_slots"],
                short_by_kind=f["capacity"]["short_by_kind"], bf16_slots=(f.get("bf16") or {}).get("slots"),
                need=need, bf16_need=nbf if a.bf16_lef else 0,
                vm_to_farthest_cluster=f["crossings"]["vm_to_farthest_cluster"], pack=str(pk), floorplan=str(fp))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pair-lef", type=Path, required=True)
    ap.add_argument("--bf16-lef", type=Path)
    ap.add_argument("--pairs", type=int, required=True)
    ap.add_argument("--bf16-pairs", type=int, default=0)
    ap.add_argument("--margin", type=float, default=0.10)
    ap.add_argument("--hbm-phy", default="ot_hbm3e_phy_v41x_aw30_e8p5")
    ap.add_argument("--q-pair", default=QP, help="pack re-fit strip source (the MAC strip width)")
    ap.add_argument("--hub", type=Path, help="dedicated-units record for the hub (default: the pack's)")
    ap.add_argument("--vm-in-su", action="store_true", help="VM-H: VM banks inside the SU block (no VM SRAMs in HUB_VM)")
    ap.add_argument("--c-rotate-strip-mm2", type=float, default=0.0, help="C_rotate VM strip area (mm2)")
    ap.add_argument("--c-rotate-centre", action="store_true")
    ap.add_argument("--c-rotate-shape", default="strip", choices=["strip", "square", "plus"])
    ap.add_argument("--lo", type=float, default=0.6)
    ap.add_argument("--hi", type=float, default=1.0)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args(argv)
    a.work.mkdir(parents=True, exist_ok=True)
    trials = []
    hi = trial(a.hi, a, a.work)
    trials.append(hi)
    if not hi["ok"]:
        raise SystemExit(f"does not close at s={a.hi}: {hi}")
    lo, best = a.lo, hi
    for _ in range(9):
        mid = round((lo + best["s"]) / 2, 4)
        t = trial(mid, a, a.work)
        trials.append(t)
        print(json.dumps({k: t.get(k) for k in ("s", "ok", "die_mm2", "slots", "short_by_kind", "why")}), flush=True)
        if t["ok"]:
            best = t
        else:
            lo = mid
        if best["s"] - lo < 0.004:
            break
    rec = dict(schema="opentallas.v41.w18_die_shrink.v1",
               ruling="root 2026-09-30: shrink the layer die to the pair need + ~10% (q pairs and BF16 columns); keep the "
                      "HBM PHY edge constraint (4 stacks on 8.5 mm edges) as the lower bound",
               need=dict(pairs=a.pairs, bf16_pairs=a.bf16_pairs, margin=a.margin),
               chosen=best, base_die_um=[BASE_W, BASE_H], area_ratio=round(best["die_mm2"] / (BASE_W * BASE_H / 1e6), 4),
               trials=sorted(trials, key=lambda t: t["s"]),
               inputs=dict(pair_lef=str(a.pair_lef), pair_lef_sha256=sha(a.pair_lef),
                           bf16_lef=str(a.bf16_lef) if a.bf16_lef else None,
                           bf16_lef_sha256=sha(a.bf16_lef) if a.bf16_lef else None,
                           hub=str(a.hub) if a.hub else None, hub_sha256=sha(a.hub) if a.hub else None, vm_in_su=a.vm_in_su, c_rotate_strip_mm2=a.c_rotate_strip_mm2 or None, c_rotate_centre=a.c_rotate_centre, c_rotate_shape=a.c_rotate_shape,
                           tool_sha256=sha(Path(__file__)), pack_sha256=sha(ROOT / "tools/w18/pack.py"),
                           floorplan_tool_sha256=sha(ROOT / "tools/w18/die_floorplan.py")))
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(chosen={k: best[k] for k in ("s", "die_um", "die_mm2", "slots", "bf16_slots")},
                          area_ratio=rec["area_ratio"]), indent=1))


if __name__ == "__main__":
    main()
