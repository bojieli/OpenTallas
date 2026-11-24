import json, re, statistics, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
E = Path(__file__).parent
def arcs(path):
    t = Path(path).read_text(errors="replace"); out = {}
    for m in re.finditer(r'\bpin\s*\(\s*"?([^")]+)"?\s*\)\s*\{', t):
        i = j = m.end(); d = 1
        while d and j < len(t):
            d += {'{': 1, '}': -1}.get(t[j], 0); j += 1
        body = t[i:j]
        for tm in re.finditer(r'timing\s*\(\s*\)\s*\{', body):
            k = e = tm.end(); d = 1
            while d and e < len(body):
                d += {'{': 1, '}': -1}.get(body[e], 0); e += 1
            tb = body[k:e]
            rp = re.search(r'related_pin\s*:\s*"?([^";]+)', tb); tt = re.search(r'timing_type\s*:\s*([^;]+);', tb)
            vals = [float(x) for v in re.findall(r'values\s*\(([^)]*)\)', tb) for x in re.findall(r'-?\d+(?:\.\d+)?', v)]
            if vals: out[(m.group(1), rp.group(1).strip() if rp else '', tt.group(1).strip() if tt else '')] = max(vals)
    return out
def med(a, b, kinds):
    v = [b[k] - a[k] for k in a.keys() & b.keys() if k[2] in kinds]
    return (round(statistics.median(v), 2), round(min(v), 2), round(max(v), 2), len(v)) if v else None
C2Q = ("rising_edge", "falling_edge")
rows = []
for d in sorted(E.iterdir()):
    if not (d / "out_ff.lib").is_file() or not (d / "out_tt.lib").is_file():
        if (d / "base").is_dir(): rows.append(dict(module=d.name, status="NO-OUTPUT", log=(d / "regen_FF.log").read_text()[-300:] if (d / "regen_FF.log").is_file() else ""))
        continue
    ot, of, nt, nf = (arcs(d / f) for f in ("old_tt.lib", "old_ff.lib", "out_tt.lib", "out_ff.lib"))
    par = "rcx" if (d / "rcx_tt.spef").exists() else "spef"
    tt_match = med(ot, nt, C2Q); old_d = med(ot, of, C2Q); new_d = med(nt, nf, C2Q); ff_shift = med(of, nf, C2Q)
    hold_shift = med(of, nf, ("hold_rising", "hold_falling")); setup_shift = med(of, nf, ("setup_rising", "setup_falling"))
    ok = tt_match is not None and abs(tt_match[1]) <= 1.0 and abs(tt_match[2]) <= 1.0
    rows.append(dict(module=d.name, status="TT-EXACT" if ok else "TT-MISMATCH", parasitics=par, tt_new_minus_old=tt_match,
                     ff_minus_tt_old=old_d, ff_minus_tt_new=new_d, ff_new_minus_old=ff_shift, hold_arc_shift=hold_shift, setup_arc_shift=setup_shift))
json.dump(rows, open(E / "compare.json", "w"), indent=1)
for r in rows:
    if r["status"] == "NO-OUTPUT": print(f"{r['module']:40s} NO-OUTPUT {r['log'][-150:]!r}"); continue
    print(f"{r['module']:40s} {r['status']:11s} {r['parasitics']:4s} TTd {r['tt_new_minus_old']} | FF-TT old {r['ff_minus_tt_old'][0] if r['ff_minus_tt_old'] else None} new {r['ff_minus_tt_new'][0] if r['ff_minus_tt_new'] else None} | FF c2q new-old {r['ff_new_minus_old']} | hold {r['hold_arc_shift']}")
