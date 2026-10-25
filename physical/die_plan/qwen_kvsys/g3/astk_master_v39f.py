#!/usr/bin/env python3
"""KV-PLAN3F 10-25 (owner option B, ID straps; KV-CORE-RTL 07:09): ASTK 4 -> 1 strap master in the plan.

The four corner cores kv3_astk_{EN,ES,WN,WS} (kv3_hub_Eo / kv3_hub_Wo) become instances of ONE master module kv3_astk
(kit kv3_astk__190.08x181.44, 1692 pins = corner pins + ck, rst_n, strap_corner[1:0]).  Each instance:
  module kv3_astk, pins_file cores/kv3_astk_pins.json (the master kit table in plan convention: a pin also in the
  kv3_astk_EN plan table keeps that plan coordinate, the master's own layout = EN; a pin new in the kit (ck, rst_n,
  straps) keeps its kit coordinate), orient = the whole-instance orient (R0/MX/MY/R180) with the smallest mean pin
  displacement vs the old corner table, straps [strap_corner, 2 b, value EN 2'b11 | ES 2'b10 | WN 2'b01 | WS 2'b00]
  (bit1 = E side, bit0 = N half; the hub ties TIEHI/TIELO next to the pin).
Pins of the old corner tables missing from the master (am g drop qo[571]) are reported, not invented.
    astk_master_v39f.py PLAN_IN PLAN_OUT --kit-pins KIT/pins.json --cores DIR --report R.json
"""
import argparse
import json
from pathlib import Path

W, H = 190.08, 181.44
VAL = dict(EN="2'b11", ES="2'b10", WN="2'b01", WS="2'b00")
OR = {"R0": lambda x, y: (x, y), "MX": lambda x, y: (x, H - y), "MY": lambda x, y: (W - x, y),
      "R180": lambda x, y: (W - x, H - y)}


def load(f):
    j = json.loads(Path(f).read_text())
    return j, (j.get("pins", j) if isinstance(j, dict) else j)


def key(q):
    return q.get("name") or f"{q['bus']}[{q.get('bit', 0)}]"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--kit-pins", required=True)
    ap.add_argument("--cores", required=True)
    ap.add_argument("--report", required=True)
    a = ap.parse_args()
    cores = Path(a.cores)
    _, kit = load(a.kit_pins)
    en_js, en = load(cores / "kv3_astk_EN_pins.json")
    enk = {key(q): q for q in en}
    master = []
    for q in kit:
        k = key(q)
        if k in enk:
            master.append(dict(enk[k]))
        else:
            r = dict(name=k, layer=q["layer"], x=q["x"], y=q["y"])
            if q.get("face"):
                r["face"] = q["face"]
            master.append(r)
    mk = {key(q): (q["x"], q["y"]) for q in master}
    out_js = dict(schema=en_js.get("schema", "opentallas.die_plan.core_pins.v1") if isinstance(en_js, dict) else
                  "opentallas.die_plan.core_pins.v1", core="kv3_astk",
                  frame="core R0, origin (0,0), outline 190.08 x 181.44",
                  source=f"KV-PLAN3F 10-25: ASTK strap master kit table ({a.kit_pins}); pins also in kv3_astk_EN keep "
                         "the EN plan coordinate", pins=master)
    (cores / "kv3_astk_pins.json").write_text(json.dumps(out_js, indent=1) + "\n")
    raw = json.loads(Path(a.plan).read_text())
    rep = dict(master_pins=len(master), instances=[])
    for tn, t in raw["partition_types"].items():
        for hc in t.get("hard_cores") or []:
            m = hc.get("module", "")
            if not m.startswith("kv3_astk_"):
                continue
            c = m.rsplit("_", 1)[1]
            _, old = load(cores / f"kv3_astk_{c}_pins.json")
            ok = {key(q): (q["x"], q["y"]) for q in old}
            disp = {}
            for o, f in OR.items():
                d = [abs(f(*mk[k])[0] - x) + abs(f(*mk[k])[1] - y) for k, (x, y) in ok.items() if k in mk]
                disp[o] = sum(d) / max(1, len(d))
            o = min(disp, key=lambda z: (disp[z], z != "R0"))
            missing = sorted(k for k in ok if k not in mk)
            hc.update(module="kv3_astk", pins_file="cores/kv3_astk_pins.json", orient=o,
                      straps=[dict(port="strap_corner", width=2, value=VAL[c],
                                   note="{E/W, N/S}: bit1 = E side, bit0 = N half (KV-CORE-RTL 10-25 07:09)")])
            hc["note"] = (hc.get("note", "") + f" | v3.9f ASTK strap master kv3_astk ({c}, {o}, strap_corner={VAL[c]})"
                          ).lstrip(" |")
            rep["instances"].append(dict(type=tn, inst=hc["inst"], corner=c, orient=o,
                                         mean_disp_um={k: round(v, 1) for k, v in disp.items()},
                                         pins_missing_in_master=missing,
                                         pins_moved=sum(1 for k in ok if k in mk and
                                                        OR[o](*mk[k]) != ok[k])))
    Path(a.out).write_text(json.dumps(raw, indent=1) + "\n")
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    for i in rep["instances"]:
        print(f"astk_master: {i['type']}.{i['inst']} {i['corner']} -> kv3_astk {i['orient']} mean disp "
              f"{i['mean_disp_um'][i['orient']]} um, moved {i['pins_moved']}, missing {i['pins_missing_in_master']}")


if __name__ == "__main__":
    main()
