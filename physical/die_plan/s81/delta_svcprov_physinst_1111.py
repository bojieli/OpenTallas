#!/usr/bin/env python3
"""S81 SVCPROV-PHYSINST-1111 (DIE-S81-85 FINDING 11-10 23:46, COORD 11-11 00:3x): the svc_prov v5 event gave the 4 TRX
provider boxes of every svc_rs type (u_rsv.u_att.u_eng.g_tr[k].g_x.u_tr, XOFF 0/8/16/24) a physical_master
(ot_hdc_v41x_attn_tr_x_xoff<k>) but no physical_inst.  gen_phys.content_physical_identity requires the two together,
so gen_phys / die_trial.clock_taps cannot load the plan and no svc_rs kit can be generated.

The box is placed at its own logical instance (a provider box on an existing module boundary), so the physical
instance IS the logical one: this delta adds physical_inst = inst to every hard_cores / contents entry that has a
physical_master and no physical_inst.  Nothing else changes (checked: the output equals the input with exactly those
keys added; the input's json.dumps style is detected and reproduced byte for byte).

usage: delta_svcprov_physinst_1111.py IN.json OUT.json REPORT.json   (IN / OUT plain json; commit gzip -n -9)
"""
import hashlib
import json
import sys
from pathlib import Path

KEYS = ("hard_cores", "contents")


def fix(plan):
    added = []
    for tn, t in sorted(plan["partition_types"].items()):
        for k in KEYS:
            for e in t.get(k) or []:
                if "physical_master" in e and "physical_inst" not in e:
                    e["physical_inst"] = e["inst"]
                    added.append(dict(type=tn, list=k, inst=e["inst"], physical_master=e["physical_master"]))
                elif ("physical_inst" in e) != ("physical_master" in e):
                    raise SystemExit(f"{tn} {k} {e.get('inst')}: physical_inst without physical_master")
    return added


def strip(plan, added):
    for a in added:
        for e in plan["partition_types"][a["type"]][a["list"]]:
            if e["inst"] == a["inst"]:
                e.pop("physical_inst")
    return plan


def main():
    src, out, rep = map(Path, sys.argv[1:4])
    raw = src.read_bytes()
    plan = json.loads(raw)
    # the input's own dump style (compact one-line json.dumps or indent=1, each + newline), reproduced byte for byte
    styles = [lambda p: json.dumps(p) + "\n", lambda p: json.dumps(p, indent=1) + "\n"]
    dump = next((d for d in styles if d(plan).encode() == raw), None)
    if dump is None:
        raise SystemExit("input is not in a json.dumps form; refuse (the edit must not restyle the plan)")
    added = fix(plan)
    txt = dump(plan)
    # the only change: the added keys (remove them again -> the input, byte for byte)
    if dump(strip(json.loads(txt), added)).encode() != raw:
        raise SystemExit("output differs from the input beyond the added physical_inst keys")
    out.write_text(txt)
    r = dict(schema="s81.svcprov_physinst_1111.v1", event="SVCPROV-PHYSINST-1111",
             input=str(src), input_sha256=hashlib.sha256(raw).hexdigest(),
             output_sha256=hashlib.sha256(txt.encode()).hexdigest(), n_added=len(added),
             types=sorted({a["type"] for a in added}), added=added)
    rep.write_text(json.dumps(r, indent=1) + "\n")
    print(json.dumps(dict(n_added=len(added), types=len(r["types"]), out=r["output_sha256"][:16])))


if __name__ == "__main__":
    main()
