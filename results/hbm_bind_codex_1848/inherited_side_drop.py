#!/usr/bin/env python3
"""DIE-HBM-24 (HBM-044, COORD 18:36 ruling (A); precedent HBM-040 vmdel_s_drop.py): plan d23a carries 8 SU side
hard cores u_su_Q<q>_side_softplus / u_su_Q<q>_side_rest (types q_su00/01/10/11 and their __physical_v1 twins, one per
type, used by NE/NW su00/01/10/11).  The source builds the side unit only for QID==0 && G==0
(ot_hbm_su_static_pgslice_s.sv:182) and the as-built SUs are QID 3/2, so the side cores have no source cells and
strict bind EMITs `wavefront core reset q_su00/u_su_Q0_side_softplus.rst_n: expected one bound leaf, found 0`.
This delta removes, per type: the side hard core, its clock tap (name == inst.<pin>), and the instance-level sidecar
entries (core_conns.json, clock_entries.json, clock_taps_die.json).  The side cores have no contents, no internal
stations, no buses (core_conns = clk_side tap only); the script fails closed otherwise and on any string left in
die_plan.json naming a removed inst.  Module-level registries (core_macros / entries / pin_windows / recipes /
canonical ports / clock.mesh.core_islands keyed by module) are left as they are (no instance).
usage: side_drop.py PLAN_DIR OUT_DIR"""
import hashlib, json, os, re, shutil, sys
from pathlib import Path

PAT = re.compile(r"^u_su_Q\d+_side_(softplus|rest)($|\.)")
hit = lambda n: isinstance(n, str) and bool(PAT.match(n))


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
    rep = dict(schema="opentallas.hbm.side_drop.v1", source_plan_sha256=hashlib.sha256(raw).hexdigest(), types={})
    removed = set()
    for tn, t in P["partition_types"].items():
        hcs = [h for h in t.get("hard_cores", []) if hit(h["inst"])]
        if not hcs:
            continue
        users = [p["name"] for p in P["partitions"] if p["type"] == tn]
        cts = [c for c in t.get("contents", []) if hit(c.get("inst"))]
        st = [s for s in t.get("internal_stations", []) if hit(s.get("launch")) or hit(s.get("capture"))]
        bus = [b for b in t.get("buses", []) if any(hit(v) for v in strings(b))]
        if cts or st or bus:
            raise SystemExit(f"{tn}: side core has contents {len(cts)} / stations {len(st)} / buses {len(bus)} (expected 0)")
        ck = t.get("clock", {})
        taps = [x for x in ck.get("taps", []) if hit(x.get("name"))]
        assert len(hcs) == 1 and len(taps) == 1, (tn, len(hcs), len(taps))
        t["hard_cores"] = [h for h in t["hard_cores"] if h not in hcs]
        ck["taps"] = [x for x in ck["taps"] if x not in taps]
        removed |= {h["inst"] for h in hcs}
        t["note"] = t.get("note", "") + " | DIE-HBM-24 HBM-044 (A): SU side core removed (source builds side unit only for QID0/G0; no cells)"
        rep["types"][tn] = dict(used_by=users, hard_cores_removed=[dict(inst=h["inst"], module=h.get("module"),
                                origin_um=h.get("origin_um"), outline_um=h.get("outline_um"), note=h.get("note")) for h in hcs],
                                taps_removed=[x.get("name") for x in taps])
    assert len(rep["types"]) == 8, len(rep["types"])
    left = sorted({v for v in strings(P) if any(v == r or v.startswith(r + ".") or v == "tap:" + r for r in removed)
                   or re.search(r"u_su_Q\d+_side_(softplus|rest)", v)})
    if left:
        raise SystemExit(f"removed side cores still referenced: {left[:10]}")
    P["note"] = P.get("note", "") + " | DIE-HBM-24 side_drop (HBM-044 A)"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    side = {}
    for f in os.listdir(plan_dir):
        if f in ("die_plan.json", "side_drop_report.json", "core_conns.json", "clock_entries.json", "clock_taps_die.json"):
            continue
        s = plan_dir / f
        (shutil.copytree(s, out_dir / f, copy_function=os.link) if s.is_dir() else os.link(s, out_dir / f))
    # instance-level sidecars
    cc = json.loads((plan_dir / "core_conns.json").read_text())
    ce = json.loads((plan_dir / "clock_entries.json").read_text())
    td = json.loads((plan_dir / "clock_taps_die.json").read_text())
    n_cc = n_ce = 0
    for tn in rep["types"]:
        for d in (cc, ce):
            for k in [k for k in d.get(tn, {}) if hit(k)]:
                del d[tn][k]
                if d is cc: n_cc += 1
                else: n_ce += 1
    td2 = [x for x in td if not hit(x.get("tap"))]
    side = dict(core_conns_removed=n_cc, clock_entries_removed=n_ce, clock_taps_die_removed=len(td) - len(td2))
    assert n_cc == 8 and n_ce == 8 and len(td) - len(td2) == 8, side
    (out_dir / "core_conns.json").write_text(json.dumps(cc, indent=1))
    (out_dir / "clock_entries.json").write_text(json.dumps(ce, indent=1))
    (out_dir / "clock_taps_die.json").write_text(json.dumps(td2, indent=1))
    for f in ("core_conns.json", "clock_entries.json", "clock_taps_die.json"):
        assert not re.search(r"u_su_Q\d+_side_(softplus|rest)", (out_dir / f).read_text()), f
    rep["sidecars"] = side
    txt = json.dumps(P, indent=1)
    (out_dir / "die_plan.json").write_text(txt)
    rep["plan_sha256"] = hashlib.sha256(txt.encode()).hexdigest()
    (out_dir / "side_drop_report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(dict(plan_sha256=rep["plan_sha256"][:12], types=len(rep["types"]), **side)))


if __name__ == "__main__":
    main(*sys.argv[1:3])
