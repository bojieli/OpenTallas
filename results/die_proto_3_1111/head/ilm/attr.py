import json, csv, sys, collections
I, D = sys.argv[1:3]
sp = json.load(open(I + "/spine_FF.json"))["parts"]
late, early = {}, {}
for l in open(D + "/arr_check_FF.txt"):
    _, n, a, b = l.split()
    inst, port = n[2:].split("__", 1)
    late[(inst, port)] = float(a); early[(inst, port)] = float(b)
br = json.load(open(I + "/run/die_sta.json"))["corners"]["FF"]["seams"]
tr = {r["group"]: r for r in csv.DictReader(open(I + "/ilm_seam_rows_tree.tsv"), delimiter="\t")}
inst = json.load(open(I + "/run_tree/die_sta.json"))["instances"]
real = set(json.load(open(I + "/real_modules.json")))
def rng(d, i):
    v = [x for (a, p), x in d.items() if a == i]
    return (min(v), max(v)) if v else (None, None)
def off(i):
    v = [t["offset_ps"] for t in sp.get(i, {}).get("taps", {}).values()]
    return (min(v), max(v)) if v else (None, None)
for g, r in sorted(tr.items(), key=lambda x: float(x[1]["hold_FF"]) if x[1]["hold_FF"] != "None" else 1e9):
    if r["cls"] != "seam" or r["hold_FF"] == "None" or float(r["hold_FF"]) >= 0: continue
    s, t = g.split("/")[0].split("->")
    b = (br.get(g) or {}).get("min", {}).get("worst")
    print(f"{g}\tL={s}:{inst[s]}{'(real)' if inst[s] in real else '(standin)'}\tC={t}:{inst[t]}{'(real)' if inst[t] in real else '(standin)'}"
          f"\tbranch {b}\ttree {r['hold_FF']}\tbranch_off L {off(s)} C {off(t)}\ttree_late L {rng(late, s)} C {rng(late, t)}\ttree_early L {rng(early, s)} C {rng(early, t)}")
