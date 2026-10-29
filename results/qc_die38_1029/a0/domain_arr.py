"""DIE-QC-38 A0: per clock domain (root / each hop ICG) register arrival at FF (min/median/max) with gate depth + gate
output arrival, from the FF clock dump of the kept V2 cts_prehold.odb."""
import csv, collections, statistics as st, sys
D = sys.argv[1]
w = open(f"{D}/domain_ff.tsv", "w"); w.write("tile\tdomain\tn_regs\tgate_depth\tgate_out_ff\treg_min_ff\treg_med_ff\treg_max_ff\n")
for t in ("nl", "nk"):
    T = {r["inst"]: r for r in csv.DictReader(open(f"{D}/{t}_tree_ff.tsv"), delimiter="\t")}
    dom, info = collections.defaultdict(list), {}
    for n, r in T.items():
        if r["kind"] != "sink" or r["master"].startswith("ot_"): continue
        m, g = r["parent"], "root"
        while m != "port:ck":
            if T[m]["master"].startswith("ICG"):
                g = m.split("u_hop_")[-1].split("/")[0]; info[g] = (T[m]["depth"], T[m]["out_min_r"]); break
            m = T[m]["parent"]
        dom[g].append(float(r["in_min_r"]))
    for g, v in sorted(dom.items(), key=lambda kv: st.median(kv[1])):
        d, o = info.get(g, ("-", "-"))
        w.write(f"{t}\t{g}\t{len(v)}\t{d}\t{o}\t{min(v):.1f}\t{st.median(v):.1f}\t{max(v):.1f}\n")
w.close()
