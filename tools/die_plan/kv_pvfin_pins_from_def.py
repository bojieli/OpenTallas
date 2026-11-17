#!/usr/bin/env python3
"""KV-HUBC-SPLIT: core_pins.v1 pins.json of a signed hard core from its routed 6_final.def (read only).
usage: kv_pvfin_pins_from_def.py 6_final.def MODULE OUT.json   (signal pins only; PG pins skipped)"""
import json, re, sys


def parse(text, module):
    u = int(re.search(r"UNITS DISTANCE MICRONS (\d+)", text).group(1))
    w, h = (int(v) / u for v in re.search(r"DIEAREA \( 0 0 \) \( (\d+) (\d+) \)", text).groups())
    sec = text.split("\nPINS ", 1)[1].split("END PINS", 1)[0]
    rows = []
    for blk in re.split(r"\n\s+- ", "\n" + sec.split(";\n", 1)[1] if False else sec):
        m = re.match(r"(\S+) \+ NET", blk.strip())
        if not m or "SPECIAL" in blk or "USE POWER" in blk or "USE GROUND" in blk:
            continue
        name = m.group(1).replace("\\", "")
        d = re.search(r"DIRECTION (\w+)", blk).group(1)
        lay = re.search(r"LAYER (\w+) \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)", blk)
        pl = re.search(r"PLACED \( (-?\d+) (-?\d+) \)", blk) or re.search(r"FIXED \( (-?\d+) (-?\d+) \)", blk)
        x = (int(pl.group(1)) + (int(lay.group(2)) + int(lay.group(4))) / 2) / u
        y = (int(pl.group(2)) + (int(lay.group(3)) + int(lay.group(5))) / 2) / u
        face = min({"W": x, "E": w - x, "S": y, "N": h - y}.items(), key=lambda kv: kv[1])[0]
        rows.append(dict(name=name, face=face, x=round(x, 3), y=round(y, 3), layer=lay.group(1), dir="in" if d == "INPUT" else "out"))
    return dict(schema="opentallas.core_pins.v1", core=module, frame="core R0, origin (0,0)", module=module, outline_um=[w, h],
                source="6_final.def of the signed route (signoff_s8pin2b)", pins=rows)


if __name__ == "__main__":
    j = parse(open(sys.argv[1]).read(), sys.argv[2])
    json.dump(j, open(sys.argv[3], "w"), indent=1)
    print(len(j["pins"]), "pins", j["outline_um"])
