"""QC-KITS-R1: per type, ft slots without plan station sites (generator-placed) and plan station sites inside hard cores."""
import json, sys
def rect(h):
    x, y = h["origin_um"]; w, hh = h["outline_um"]
    if h.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"): w, hh = hh, w
    return (x, y, x + w, y + hh)
d = json.load(open(sys.argv[1])); only = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else None
for tn, t in sorted(d["partition_types"].items()):
    if only and tn not in only: continue
    cores = [rect(h) for h in t.get("hard_cores") or []]
    nosite, incore = [], {}
    for s in t.get("ft_slots") or []:
        if not s.get("bit_sites_um"): nosite.append(f"{s['name']}({s['in_face']}->{s['out_face']} w{s['width']} st{s['stations']})")
        for st in s.get("bit_sites_um") or []:
            for p in st:
                if any(r[0] < p[0] < r[2] and r[1] < p[1] < r[3] for r in cores):
                    incore[s["name"]] = incore.get(s["name"], 0) + 1
    print(f"{tn}: slots {len(t.get('ft_slots') or [])} no-site {len(nosite)} {' '.join(nosite)[:400]} | sites-in-core {incore}")
