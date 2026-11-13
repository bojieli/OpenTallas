#!/usr/bin/env python3
"""Recover provider boundaries into current S81 plans without repeating historical die growth.
Private form constructor; outputs diagnostics, never claims a gated plan. SVC 1113.
"""
import argparse,copy,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import svc_prov_event_1109 as E

def recover(P,M):
    P=copy.deepcopy(P); E.LO_PACK="b"; rows={}
    for side,names in (("hi",E.HI_TYPES),("lo",E.LO_TYPES)):
        for n in names:
            t=P["partition_types"][n]; old_shape=list(t["outline_um"])
            # ready12b-A retained the die/outline growth while reverting provider contents.
            # Its core bands remain the original positions; shift internally exactly once.
            original_bands=sorted({h["origin_um"][1] for h in t["hard_cores"]
                if h["module"]=="ot_s81c_attn_hcore" and int(h["inst"].split("g_h[")[1].split("]")[0])>=8})
            if original_bands!=E.V1.BAND_Y:
                raise ValueError((n,"unexpected retained hcore bands",original_bands))
            expected=2747.52 if side=="hi" else 2851.2
            if abs(old_shape[1]-expected)>1e-6:
                raise ValueError((n,"unrecognized outline",old_shape))
            if side=="lo": t["outline_um"][1]-=E.V1.G_TOTAL
            boxes,soft,moved,fy,macros=E.split_type(t,side,side=="lo",M)
            assert t["outline_um"]==old_shape
            failures=E.validate(t,boxes,M,side,macros)
            # Do not silently shift the parent reset root: reset_contract must resolve the new type form.
            root=P.get("reset",{}).get("in_sites",{}).get(n)
            rows[n]=dict(boxes=len(boxes),soft_cells=M["parent_soft"][side]["cells"],
                outline_um=old_shape,points_shifted=moved,legacy_checks=failures,
                reset_root_preserved=root,reset_contract="REQUIRED",provider_views="REQUIRED",
                split="REQUIRED",new_memory_macros=len(macros),pin_cycles=E.pin_cycles(boxes,soft,fy))
    return P,rows

def main():
    a=argparse.ArgumentParser();a.add_argument("base");a.add_argument("out");a.add_argument("report");x=a.parse_args()
    p,r=recover(json.load(open(x.base)),json.load(open(HERE/"svc_prov_meas_1109.json")))
    Path(x.out).write_text(json.dumps(p,indent=1)+"\n")
    Path(x.report).write_text(json.dumps(dict(status="PRIVATE_UNGATED",die_geometry_changed=False,
        pvso_entry="OPEN: template requires +57.24um row offset and new landing placement",types=r),indent=1)+"\n")
    print(json.dumps({n:dict(boxes=z["boxes"],legacy_failures=len(z["legacy_checks"])) for n,z in r.items()}))
if __name__=="__main__":main()
