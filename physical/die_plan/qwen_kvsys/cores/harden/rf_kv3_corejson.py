#!/usr/bin/env python3
"""DIE-KV-64/RF-B 11-03 RF-KV3 split: core RTL json for PCC / PCF from the split sources (rf_kv3_split.py) and the PC
RF-KV1 core json (pin classes of kept pins copied; new pins: clk for ck, in/out by direction).

    rf_kv3_corejson.py PC_CORE_JSON SRC_DIR MODULE PINS_FILE OUT_JSON REPO
"""
import json
import re
import sys
from pathlib import Path


def ports(top_text, mod):
    a = top_text.index(f"module {mod} (")
    b = top_text.index(");", a)
    out = {}
    for m in re.finditer(r"(input|output)\s+wire\s+(?:\[(\d+):(\d+)\]\s+)?(\w+)", top_text[a:b]):
        d, hi, lo, n = m.groups()
        out[n] = [d + "put" if d in ("in", "out") else d, int(hi or 0), int(lo or 0)]
    return out


def main(pc_json, src_dir, mod, pins_file, out_json, repo):
    pc = json.load(open(pc_json))
    src_dir, repo = Path(src_dir).resolve(), Path(repo).resolve()
    top = (src_dir / f"{mod}.sv").read_text()
    pd = ports(top, mod)
    pcls = pc["pin_class"]
    cls = {}
    for n, (d, hi, lo) in pd.items():
        for i in range(lo, hi + 1):
            k = f"{n}[{i}]"
            if k in pcls:
                cls[k] = pcls[k]
            elif n in ("ck",) or n.startswith("ft_ck"):
                cls[k] = pcls.get(k, "clk" if n == "ck" else ("in" if d == "input" else "out"))
            else:
                cls[k] = "in" if d == "input" else "out"
    counts = {}
    for v in cls.values():
        counts[v] = counts.get(v, 0) + 1
    files = sorted(str(f.relative_to(repo)) for f in src_dir.iterdir() if f.suffix in (".sv", ".v"))
    # memory black boxes: the repo macro view path of the PC core json (gen needs lef/lib next to it)
    mem = {Path(f).name: f for f in pc["files"] if f.endswith("_bb.v")}
    for i, f in enumerate(files):
        if Path(f).name in mem:
            (repo / f).unlink()
            files[i] = mem[Path(f).name]
    tf = str((src_dir / f"{mod}.sv").relative_to(repo))
    files.remove(tf)
    files.insert(0, tf)
    pins = json.load(open(pins_file))["pins"]
    pn = {p["name"] for p in pins}
    miss = sorted(set(cls) - pn)
    extra = sorted(x for x in pn - set(cls) if not x.startswith("ft_ck_"))  # island ft: gen adds them
    assert not miss and not extra, (miss[:5], extra[:5])
    cj = dict(schema=pc["schema"], module=mod, type=pc["type"], inst=pc["inst"], bound=pc.get("bound"),
              members=pc.get("members"), member_bound=pc.get("member_bound"), ports=len(pd), pin_bits=len(cls),
              classes=counts,
              report=dict(pins_file=str(Path(pins_file).resolve().relative_to(repo)), pins=len(pins), stale=[], added=[],
                          straps=[], note="RF-KV3 split core (rf_kv3_split.py / rf_kv3_plan.py); pins = this table"),
              consistency=dict(note="split of the RF-KV2 PC kit RTL (no bound re-derivation)"),
              lint=pc.get("lint"), files=files, port_decl=pd, pin_class=cls,
              rf_kv3=dict(lane="DIE-KV-64/RF-B 11-03", form="CONSERVATIVE split PCC + PCF", src_core_json=str(pc_json)))
    Path(out_json).write_text(json.dumps(cj, indent=1) + "\n")
    print("RF_KV3_COREJSON", mod, len(pd), len(cls), counts, len(files))


if __name__ == "__main__":
    main(*sys.argv[1:7])
