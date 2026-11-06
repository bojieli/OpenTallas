#!/usr/bin/env python3
"""Small real consumers of form_geometry; reports/candidates only, no plan edits."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import form_geometry as F


def coll(raw):
    rows=[]
    for tn,t in raw["partition_types"].items():
        for c in t.get("hard_cores",[]):
            if c.get("module") not in ("dsfd_coll_lane_w_safe8_ntf","dsfd_coll_lane_e_safe8_ntf"):
                continue
            rows.append(dict(type=tn,module=c["module"],
                tall=F.fit_core(t,c["inst"],[295.92,660.96],obs_max="M6"),
                compact=F.fit_core(t,c["inst"],obs_max="M6")))
    return {"case":"s81_coll_parent_fit","occurrences":rows,
            "tall_fits":sum(r["tall"]["fits"] for r in rows),
            "compact_fits":sum(r["compact"]["fits"] for r in rows),
            "note":"M6 OBS needs actual PG/interface reservation; bbox fit is not a physical signoff"}


def phy_reset(raw):
    t=raw["partition_types"]["kv3_phy_v1"]
    # Exact ot_dp_rsync W=1,S=2 names verified by a native-source Yosys
    # flatten/rename-wire probe. Only placement changes; source/phase unchanged.
    cells=[f"u_rs_ri_core_rst_n.b[0].r[{i}]" for i in range(2)]
    pin=next(q for q in t["reset_spine_pins"] if q["name"]=="ri_core_rst_n")
    assert pin["width"]==1 and len(pin["sites_um"])==1
    start=list(pin["sites_um"][0]);sink=[306.72,515.064]
    reserves=F.placement_reservations(t,exclude=cells)
    result=F.prepare_chain(start,sink,t["outline_um"],list(F.parent_obstacles(t).values()),1,
                           site_boxes=list(reserves.values()))
    result.update(case="kv_phy_v1_existing_two_reset_flops",source_module="ot_dp_rsync",
                  parameters={"W":1,"S":2},first_stage_um=start,sink_um=sink,
                  reservation_count=len(reserves),existing_reset_flops=2,added_flops=0,added_cycles=0,
                  contract="same existing asynchronous-assert/two-edge-release chain; no new flop/stage")
    result["first_stage_conflicts"]=[n for n,b in reserves.items() if F._inside(start,F.grow(b,2.16))]
    if result["first_stage_conflicts"]:
        result.update(fits=False,reason="existing first-stage anchor conflicts with a reserved site")
    if result["fits"]:
        result["relay_sites_delta"]={cells[0]:start,cells[1]:result["points_um"][0]}
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("case",choices=("coll","phy-reset"));p.add_argument("plan");p.add_argument("report")
    a=p.parse_args(argv);raw=json.loads(Path(a.plan).read_text())
    out=coll(raw) if a.case=="coll" else phy_reset(raw)
    Path(a.report).write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps({k:v for k,v in out.items() if k not in ("occurrences","hop_paths_um")},default=str))


if __name__=="__main__":main()
