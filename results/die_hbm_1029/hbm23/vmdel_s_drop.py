#!/usr/bin/env python3
"""DIE-HBM-23 (HBM-040, COORD 17:44 ruling (A); precedent HBM-034/035/037 plan follows source, 8-SM release):
the hub types q_hub_ne/q_hub_nw carry 8 S-role copies each, u_vmdel_Q0..7__q0 (hard core + soft content + clock tap,
note "C25c existing native S-role producer vmdel_SE/SWk; independent q0 copy"), left over from the 16-SM d4g die.
The as-built source has no vmdel_SE*/SW* (HBM-BIND-10 srole_census.json), so strict bind EMITs
wavefront core reset q_hub_ne/u_vmdel_Q0__q0.rst_n: expected one bound leaf, found 8.
This delta removes, from both hubs only: the 16 hard cores u_vmdel_Q<k>__q0, their 16 contents (type.cells reduced
by their cells) and their clock taps (name == inst or inst.<pin>); fails closed if any station/bus/pin/other string
in the WHOLE plan still names one.  The N-role u_vmdel_Q<k> stay.  South VM bank dq stay open native_required
(never tied) - nothing here touches them.
usage: vmdel_s_drop.py PLAN_DIR OUT_DIR"""
import hashlib, json, os, re, shutil, sys
from pathlib import Path

HUBS = ("q_hub_ne", "q_hub_nw")
PAT = re.compile(r"^u_vmdel_Q\d+__q0($|\.)")


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
    hit = lambda n: isinstance(n, str) and bool(PAT.match(n))
    rep = dict(schema="opentallas.hbm.vmdel_s_drop.v1", source_plan_sha256=hashlib.sha256(raw).hexdigest(), hubs={})
    for hub in HUBS:
        t = P["partition_types"][hub]
        hcs = [h for h in t["hard_cores"] if hit(h["inst"])]
        cts = [c for c in t["contents"] if hit(c["inst"])]
        st = [s for s in t.get("internal_stations", []) if hit(s.get("launch")) or hit(s.get("capture"))]
        if st:
            raise SystemExit(f"{hub}: {len(st)} internal stations name an S-role vmdel copy (expected 0)")
        ck = t.get("clock", {})
        taps = [x for x in ck.get("taps", []) if hit(x.get("name"))]
        assert len(hcs) == 8 and len(cts) == 8 and len(taps) == 8, (hub, len(hcs), len(cts), len(taps))
        t["hard_cores"] = [h for h in t["hard_cores"] if h not in hcs]
        t["contents"] = [c for c in t["contents"] if c not in cts]
        ck["taps"] = [x for x in ck.get("taps", []) if x not in taps]
        dcells = sum(int(c.get("cells", 0)) for c in cts)
        cells_old = t.get("cells")
        if cells_old is not None:
            t["cells"] = int(cells_old) - dcells
        # N-role producers stay
        assert sum(1 for h in t["hard_cores"] if re.match(r"^u_vmdel_Q\d+$", h["inst"])) == 8, hub
        t["note"] = t.get("note", "") + " | DIE-HBM-23 HBM-040 (A): S-role u_vmdel_Q*__q0 copies removed (no source producer, 8-SM)"
        rep["hubs"][hub] = dict(
            hard_cores_removed=[dict(inst=h["inst"], module=h.get("module"), origin_um=h.get("origin_um"),
                                     outline_um=h.get("outline_um")) for h in hcs],
            contents_removed=[dict(inst=c["inst"], module=c.get("module"), cells=c.get("cells")) for c in cts],
            taps_removed=[x.get("name") for x in taps], cells_old=cells_old, cells_new=t.get("cells"), cells_removed=dcells)
    left = sorted({v for v in strings(P) if re.search(r"u_vmdel_Q\d+__q0", v)})
    if left:
        raise SystemExit(f"removed S-role vmdel still referenced: {left[:10]}")
    P["note"] = P.get("note", "") + " | DIE-HBM-23 vmdel_s_drop (HBM-040 A)"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    for f in os.listdir(plan_dir):
        if f in ("die_plan.json", "vmdel_s_drop_report.json"):
            continue
        s = plan_dir / f
        (shutil.copytree(s, out_dir / f, copy_function=os.link) if s.is_dir() else os.link(s, out_dir / f))
    txt = json.dumps(P, indent=1)
    (out_dir / "die_plan.json").write_text(txt)
    rep["plan_sha256"] = hashlib.sha256(txt.encode()).hexdigest()
    (out_dir / "vmdel_s_drop_report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(dict(plan_sha256=rep["plan_sha256"][:12], **{h: dict(hc=len(v["hard_cores_removed"]),
          taps=len(v["taps_removed"]), cells=v["cells_removed"]) for h, v in rep["hubs"].items()})))


if __name__ == "__main__":
    main(*sys.argv[1:3])
