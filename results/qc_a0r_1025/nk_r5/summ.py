#!/usr/bin/env python3
"""classify OpenSTA 'report_checks -format summary' FF hold violators using the sinks/cores dumps; writes PREFIX.tsv"""
import csv, sys, collections, re
P = sys.argv[1]
HARD = {"ot_qwen_tile_romleaf", "ot_qwen_tile_lsl_fp1", "ot_qwen_tile_node"}
sink = {}
for r in csv.reader(open(P + ".sinks.tsv"), delimiter="\t"):
    if len(r) >= 4 and r[0] != "inst": r = r[:3] + r[3].split(); sink[r[0].replace("\\", "")] = r
core = {r["inst"].replace("\\", ""): r for r in csv.DictReader(open(P + ".cores.tsv"), delimiter="\t")}
rows = []
for l in open(P + ".sum"):
    t = l.split()
    if len(t) < 5 or t[0] == "Startpoint" or not re.match(r"^-?[\d.]+$", t[-1]): continue
    if not (t[1].startswith("(") and t[3].startswith("(")): continue
    sp, ep, sl = t[0].replace("\\", ""), t[2].replace("\\", ""), float(t[-1])
    if sl >= 0: continue
    si = sp.rsplit("/", 1)[0] if "/" in sp else ""
    ei = ep.rsplit("/", 1)[0] if "/" in ep else ""
    epin = ep.rsplit("/", 1)[1] if "/" in ep else ep
    def kind(i):
        if not i: return "PORT"
        return core[i]["master"] if i in core else "REG"
    sk, ek = kind(si), kind(ei)
    lt = sink[si][1] if si in sink else "-"; ct = sink[ei][1] if ei in sink else "-"
    if sk == "PORT" and ek == "PORT": c = "FEEDTHRU"
    elif sk == "PORT": c = "IN->" + ("CORE:" + ek.split("_")[-1] if ek in HARD else "REG")
    elif ek == "PORT": c = ("CORE:" + sk.split("_")[-1] if sk in HARD else "REG") + "->OUT"
    elif ek in HARD: c = ("CORE:" + sk.split("_")[-1] if sk in HARD else "REG") + "->CORE:" + ek.split("_")[-1] + ("/rst" if epin.startswith("rst") else "/data") + f"@{ct}"
    elif sk in HARD: c = "CORE:" + sk.split("_")[-1] + f"@{lt}->REG"
    else: c = "R2R_SAMETAP" if lt == ct else "R2R_XTAP"
    xy = lambda i: (sink[i][3], sink[i][4]) if i in sink else ((core[i]["x"], core[i]["y"]) if i in core else ("-", "-"))
    (sx, sy), (ex, ey) = xy(si), xy(ei)
    rows.append(dict(slack=sl, cls=c, start=sp, end=ep, ltap=lt, ctap=ct,
                     lclk=sink[si][2] if si in sink else "-", cclk=sink[ei][2] if ei in sink else "-", sx=sx, sy=sy, ex=ex, ey=ey))
with open(P + ".tsv", "w") as f:
    f.write("slack\tclass\tstart\tend\tltap\tctap\tlclk\tcclk\tsx\tsy\tex\tey\n")
    for r in rows: f.write("\t".join(str(r[k]) for k in ("slack","cls","start","end","ltap","ctap","lclk","cclk","sx","sy","ex","ey")) + "\n")
print(f"== {P}: {len(rows)} FF hold-violating endpoints, wns {min((r['slack'] for r in rows), default=0):.2f}")
c = collections.defaultdict(list)
for r in rows: c[r["cls"]].append(r["slack"])
for k, v in sorted(c.items(), key=lambda kv: min(kv[1])): print(f"  {k:45s} n={len(v):5d} wns={min(v):8.2f}")
x = collections.Counter((r["ltap"], r["ctap"]) for r in rows if r["cls"].startswith("R2R"))
print("  top R2R (launch tap, capture tap):", x.most_common(8))
y = collections.Counter(r["ctap"] for r in rows if r["cls"].startswith("IN->"))
print("  IN-> capture taps:", y.most_common(8))
