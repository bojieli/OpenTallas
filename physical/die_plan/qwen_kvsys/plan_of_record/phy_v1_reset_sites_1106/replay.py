#!/usr/bin/env python3
"""Place the two EXISTING PHYv1 reset flops; no RTL or reset phase change."""
import argparse,copy,json,sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[5]/"tools/die_plan"))
from form_geometry_cases import phy_reset

SITES={"u_rs_ri_core_rst_n.b[0].r[0]":[842.4,768.96],
       "u_rs_ri_core_rst_n.b[0].r[1]":[701.514,515.16]}


def apply(raw):
    candidate=phy_reset(raw)
    assert candidate["fits"] and candidate["relay_sites_delta"]==SITES,"parent geometry changed; review sites"
    out=copy.deepcopy(raw);t=out["partition_types"]["kv3_phy_v1"]
    pin=next(q for q in t["reset_spine_pins"] if q["name"]=="ri_core_rst_n")
    assert pin["width"]==1 and pin["sites_um"]==[[842.4,768.96]],"input reset contract changed; review event"
    sites=t.setdefault("relay_sites",{})
    for n,p in SITES.items():
        assert n not in sites or sites[n]==p,"existing explicit reset placement changed; review event"
        sites[n]=list(p)
    # An explicit inverse confirms no other type, clock, bus or stage changed.
    restored=copy.deepcopy(out)
    for n in SITES:
        if n not in raw["partition_types"]["kv3_phy_v1"].get("relay_sites",{}):
            del restored["partition_types"]["kv3_phy_v1"]["relay_sites"][n]
    assert restored==raw
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("input");p.add_argument("output")
    a=p.parse_args();out=apply(json.loads(Path(a.input).read_text()))
    Path(a.output).write_text(json.dumps(out,indent=1)+"\n")


if __name__=="__main__":main()
