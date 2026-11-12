"""DIE-PROTO-3: per-seam-group rows of the HEAD ILM die_sta (TT setup, FF hold), tagged by pair class from
die_sta_related seam rows (same-region seam) vs other (landed / count-aligned: single-cycle ILM timing not the judge),
and by real/stand-in endpoints."""
import json, csv, sys
I, SR, OUT = sys.argv[1:4]
d = json.load(open(I + "/run/die_sta.json"))
real = set(json.load(open(I + "/real_modules.json")))
inst = d["instances"]
seam_pairs = {(r["src"], r["dst"]) for r in csv.DictReader(open(SR), delimiter="\t")}
TT, FF = d["corners"]["TT"]["seams"], d["corners"]["FF"]["seams"]
rows = []
for g in sorted(set(TT) | set(FF)):
    sd, bus = g.split("/", 1); s, t = sd.split("->")
    cls = "seam" if (s, t) in seam_pairs else "landed/other"
    rs, rt = inst.get(s) in real, inst.get(t) in real
    st = (TT.get(g) or {}).get("max") or {}; hf = (FF.get(g) or {}).get("min") or {}
    rows.append(dict(group=g, cls=cls, src_real=rs, dst_real=rt, setup_TT=st.get("worst"), setup_neg=st.get("neg"),
                     hold_FF=hf.get("worst"), hold_neg=hf.get("neg"), hold_start=hf.get("start"), hold_end=hf.get("end")))
cols = list(rows[0])
with open(OUT, "w") as f:
    f.write("\t".join(cols) + "\n")
    for r in rows: f.write("\t".join(str(r[c]) for c in cols) + "\n")
def summ(sel, lab):
    h = [r for r in rows if sel(r) and r["hold_FF"] is not None]; s = [r for r in rows if sel(r) and r["setup_TT"] is not None]
    wh = min(h, key=lambda r: r["hold_FF"]) if h else None; ws = min(s, key=lambda r: r["setup_TT"]) if s else None
    print(f"{lab}: groups {len(h)} hold_FF worst {wh and wh['hold_FF']} ({wh and wh['group']}) neg groups {sum(r['hold_FF'] < 0 for r in h)} "
          f"| setup_TT worst {ws and ws['setup_TT']} ({ws and ws['group']}) neg groups {sum(r['setup_TT'] < 0 for r in s)}")
summ(lambda r: r["cls"] == "seam" and r["src_real"] and r["dst_real"], "SEAM both-real")
summ(lambda r: r["cls"] == "seam", "SEAM all (stand-in ends = contract)")
summ(lambda r: r["cls"] != "seam", "LANDED/other (single-cycle ILM, INFO)")
for r in sorted([r for r in rows if r["cls"] == "seam" and r["hold_FF"] is not None and r["hold_FF"] < 0], key=lambda r: r["hold_FF"])[:15]:
    print("  ", r["group"], r["src_real"], r["dst_real"], r["hold_FF"], r["hold_neg"], r["setup_TT"])
