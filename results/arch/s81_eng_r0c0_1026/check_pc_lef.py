"""Compare an r0c0_pc LEF against its r2c2 reference: SIZE, every common PIN block (geometry), OBS; list pins only in r2c2."""
import re, sys, json
from pathlib import Path
root = Path(sys.argv[1]); out = {}
for shape in sys.argv[2:]:
    ref = f"ot_sram_1r1w_{shape}_r2c2"; new = f"ot_sram_1r1w_{shape}_r0c0_pc"
    def parse(n):
        t = (root / f"physical/asap7_memory_macros_v2/{n}/{n}.lef").read_text()
        size = re.search(r"SIZE\s+(\S+)\s+BY\s+(\S+)", t).groups()
        pins = {m.group(1): m.group(2) for m in re.finditer(r"\n  PIN (\S+)\n(.*?)\n  END \1", t, re.S)}
        obs = re.search(r"\n  OBS\n(.*?)\n  END", t, re.S)
        return size, pins, obs.group(1) if obs else ""
    sr, pr, orf = parse(ref); sn, pn, onw = parse(new)
    common = sorted(set(pr) & set(pn))
    diff = [p for p in common if pr[p] != pn[p]]
    only_ref = sorted(set(pr) - set(pn)); only_new = sorted(set(pn) - set(pr))
    out[shape] = dict(size_ref=sr, size_new=sn, size_equal=sr == sn, pins_ref=len(pr), pins_new=len(pn),
                      common=len(common), geometry_differs=diff[:10], n_geometry_differs=len(diff),
                      only_ref=only_ref, only_new=only_new, obs_equal=orf == onw)
print(json.dumps(out, indent=1))
