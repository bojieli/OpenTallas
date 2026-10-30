#!/usr/bin/env python3
"""HBM-BIND-9 (HBM-037, precedent HBM-034/035 'plan follows source'): the as-built source has ONE hub quantiser,
hb_quant_NW (top cells hb_quant_NW__*: u_dec ot_hgi_qw_dec + 4 lg + xp ctl/slices + program leaf + split and/or),
and NO hb_quant_NE: no cell of the as-built top (hbm_current_native_top, 469 cells) is a quant cell outside
hb_quant_NW__*, and the source u_dec talks only to hb_quant_NW xp_ctl / xp rslice / xp wslice (local to NW).
The plan type q_hub_ne nevertheless carries a copy of the NW quantiser: hard cores u_hb_quant_Q__u_dec__q0/__q1
(PATH-HBM-R9 service-quadrant copies) + 17 soft contents u_hb_quant_Q__* whose notes say 'as-built hb_quant_NW__*'.
These have no source leaf (strict-bind EMIT 'wavefront core reset q_hub_ne/u_hb_quant_Q__u_dec__q0.rst_n: expected one
bound leaf, found 0').  This delta removes them from q_hub_ne only:
  * hard cores u_hb_quant_Q__u_dec__q0/__q1, their clock taps (name == inst or inst.<pin>);
  * contents u_hb_quant_Q__* (type.cells reduced by their summed cells);
  * internal stations whose launch/capture names one of them (fails closed if any bus/pin/station still refers).
q_hub_nw (the real quantiser, dec q0/q1 = HBM-036 single-source duplicate, ruling pending) is untouched.
usage: quant_ne_drop.py PLAN_DIR OUT_DIR"""
import hashlib, json, os, shutil, sys
from pathlib import Path

HUB, PFX = "q_hub_ne", "u_hb_quant_Q__"


def strings(x):
    if isinstance(x, dict):
        for k, v in x.items():
            if k != "note":
                yield from strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from strings(v)
    elif isinstance(x, str):
        yield x


def main(plan_dir, out_dir):
    plan_dir, out_dir = Path(plan_dir), Path(out_dir)
    raw = (plan_dir / "die_plan.json").read_bytes()
    P = json.loads(raw)
    t = P["partition_types"][HUB]
    hit = lambda n: isinstance(n, str) and n.startswith(PFX)
    hcs = [h for h in t["hard_cores"] if hit(h["inst"])]
    cts = [c for c in t["contents"] if hit(c["inst"])]
    st = [s for s in t.get("internal_stations", []) if hit(s.get("launch")) or hit(s.get("capture"))]
    ck = t.get("clock", {})
    taps = [x for x in ck.get("taps", []) if hit(x.get("name"))]
    t["hard_cores"] = [h for h in t["hard_cores"] if h not in hcs]
    t["contents"] = [c for c in t["contents"] if c not in cts]
    t["internal_stations"] = [s for s in t.get("internal_stations", []) if s not in st]
    ck["taps"] = [x for x in ck.get("taps", []) if x not in taps]
    dcells = sum(int(c.get("cells", 0)) for c in cts)
    cells_old = t.get("cells")
    if cells_old is not None:
        t["cells"] = int(cells_old) - dcells
    left = sorted({v for v in strings(t) if PFX in v})
    if left:
        raise SystemExit(f"{HUB}: removed quant still referenced: {left[:10]}")
    # the real (NW) quantiser must still be there
    nw = P["partition_types"]["q_hub_nw"]
    assert any(h["inst"].startswith(PFX + "u_dec") for h in nw["hard_cores"])
    t["note"] = t.get("note", "") + " | HBM-BIND-9 plan follows source (HBM-037): no hb_quant_NE in source -> NE quant copy removed"
    P["note"] = P.get("note", "") + " | HBM-BIND-9 quant_ne_drop (HBM-037)"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    for f in os.listdir(plan_dir):
        if f in ("die_plan.json", "quant_ne_drop_report.json"):
            continue
        s = plan_dir / f
        (shutil.copytree(s, out_dir / f, copy_function=os.link) if s.is_dir() else os.link(s, out_dir / f))
    txt = json.dumps(P, indent=1)
    (out_dir / "die_plan.json").write_text(txt)
    rep = dict(schema="opentallas.hbm.quant_ne_drop.v1", source_plan_sha256=hashlib.sha256(raw).hexdigest(),
               plan_sha256=hashlib.sha256(txt.encode()).hexdigest(), hub=HUB,
               hard_cores_removed=[dict(inst=h["inst"], module=h["module"], origin_um=h["origin_um"],
                                        outline_um=h["outline_um"]) for h in hcs],
               contents_removed=[dict(inst=c["inst"], module=c.get("module"), cells=c.get("cells"), note=c.get("note"))
                                 for c in cts],
               stations_removed=[dict(conn=s.get("conn"), launch=s.get("launch"), capture=s.get("capture"),
                                      bits=s.get("bits"), regs=len(s.get("regs_um", []))) for s in st],
               taps_removed=[x.get("name") for x in taps], cells_old=cells_old, cells_new=t.get("cells"),
               cells_removed=dcells)
    (out_dir / "quant_ne_drop_report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(dict(hard_cores=len(hcs), contents=len(cts), stations=len(st), taps=len(taps),
                          cells_removed=dcells, plan_sha256=rep["plan_sha256"][:12])))


if __name__ == "__main__":
    main(*sys.argv[1:3])
