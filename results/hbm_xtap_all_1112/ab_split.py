#!/usr/bin/env python3
"""HBM-VSN-XTAP-2 11-12 A/B split (DIE-HBM-100 ruling): per type cells now, latch cells added, total; A when total
<= LINE (type-level latch on every hop), else B (per-hop list = the cross-port hops whose FLOP form fails the paper
check, i.e. real-skew bound + W breaks setup or hold without the latch).
ab_split.py PLAN PAPER_TSV CELLS_TSV OUT_TSV OUT_HOPS_JSON [--line 350000]"""
import argparse, csv, json
from collections import defaultdict

ap = argparse.ArgumentParser()
ap.add_argument("plan"); ap.add_argument("paper"); ap.add_argument("cells"); ap.add_argument("out"); ap.add_argument("hops")
ap.add_argument("--line", type=int, default=350000)
a = ap.parse_args()
P = json.load(open(a.plan))
T = P["partition_types"]
lk_types = set(P["clock"]["ft_hop_lockup"].get("types") or [])
kit = {}
for r in csv.reader(open(a.cells), delimiter="\t"):
    tn, n, st, m, path = r
    if tn not in kit or int(m) > kit[tn][2]:
        kit[tn] = (int(n), st, int(m), path)
paper = defaultdict(list)
for r in csv.DictReader(open(a.paper), delimiter="\t"):
    paper[r["type"]].append(r)
rows, hops = [], {}
for tn in sorted(paper):
    slots = {s["name"]: s for s in T[tn].get("ft_slots", []) if int(s.get("stations", 1)) >= 2}
    w = {n: int(s.get("width", 1)) + 1 for n, s in slots.items()}           # latch bits per hop (data + epoch)
    allbits = sum((int(s.get("stations", 1)) - 1) * w[n] for n, s in slots.items())
    need = [r for r in paper[tn] if r["flopS"] == "" or min(float(r["flopS"]), float(r["flopH"])) < 0]
    xbits = sum(w[r["slot"]] for r in paper[tn])
    nbits = sum(w[r["slot"]] for r in need)
    compact = sum(1 for r in paper[tn] if 0 <= float(r["Lmax_um"]) <= 60)
    sib = tn[:-len("__physical_v1")] if tn.endswith("__physical_v1") else tn + "__physical_v1"
    if tn in kit:
        now, basis = kit[tn][0], f"kit {kit[tn][1]}"
    elif sib in kit:
        now, basis = kit[sib][0], f"sibling {sib} kit {kit[sib][1]}"
    else:
        now, basis = None, f"UNMEASURED (no kit census; plan cells {T[tn].get('cells')})"
    tot_a = (now or 0) + allbits
    # existing lockup types already carry the type-level latch in their kit census (nothing added)
    if tn in lk_types:
        form, add, tot = "A (already lockup)", 0, now
    elif now is not None and tot_a <= a.line:
        form, add, tot = "A", allbits, tot_a
    else:
        form, add, tot = "B", nbits, (None if now is None else now + nbits)
        hops[tn] = {}
        for r in need:
            hops[tn].setdefault(r["slot"], []).append(int(r["k"]))
    rows.append(dict(type=tn, form=form, cells_now=now, basis=basis, latch_all=allbits, latch_xhop=xbits,
                     latch_B=nbits, added=add, total=tot, over_line=("?" if tot is None else int(tot > a.line)), xhops=len(paper[tn]),
                     need_hops=len(need), compact_le60um=compact))
with open(a.out, "w") as f:
    wr = csv.DictWriter(f, list(rows[0]), delimiter="\t"); wr.writeheader(); wr.writerows(rows)
json.dump({t: {s: sorted(set(k)) for s, k in m.items()} for t, m in hops.items()}, open(a.hops, "w"), indent=1, sort_keys=True)
A = [r for r in rows if r["form"] == "A"]; B = [r for r in rows if r["form"] == "B"]
print("A", len(A), "added", sum(r["added"] for r in A), "| B", len(B), "added", sum(r["added"] for r in B),
      "(type-level would add", sum(r["latch_all"] for r in B), ") | over line after B:", [r["type"] for r in B if r["over_line"] == 1])
for r in rows:
    print(f'{r["type"]}\t{r["form"]}\t{r["cells_now"]}\t{r["added"]}\t{r["total"]}\t{r["basis"]}')
