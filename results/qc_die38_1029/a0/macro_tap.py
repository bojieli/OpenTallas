"""DIE-QC-38 A0: per-macro clock pin arrival (measured, FF/TT) vs the hold-neutral tap = median register arrival
minus the macro's own late insertion (Liberty max_clock_tree_path, FF), and the reg->macro hold fails per macro."""
import csv, sys, re, statistics as st, collections
D = sys.argv[1]
INS_FF_MAX = {"ot_qwen_tile_lsl_rawfault_m3": 210.59, "ot_qwen_tile_romleaf": 243.27}   # kit macros/*_ff.lib
w = open(f"{D}/macro_tap.tsv", "w")
w.write("tile\tmacro\tmaster\tchain_r\tgate_ff\tpin_ff\tpin_tt\tideal_pin_ff\tlate_by_ff\tfails\tworst_ps\n")
for t in ("nl", "nk"):
    T = {r["inst"]: r for r in csv.DictReader(open(f"{D}/{t}_tree_ff.tsv"), delimiter="\t")}
    Tt = {r["inst"]: r for r in csv.DictReader(open(f"{D}/{t}_tree_tt.tsv"), delimiter="\t")}
    regs = sorted(float(r["in_min_r"]) for r in T.values() if r["kind"] == "sink" and not r["master"].startswith("ot_"))
    med = regs[len(regs) // 2]
    f = collections.defaultdict(list)
    for h in csv.DictReader(open(f"{D}/{t}_hold_fail.tsv"), delimiter="\t"):
        ei = h["endpoint"].rsplit("/", 1)[0]
        if ei in T and T[ei]["master"].startswith("ot_"): f[ei].append(float(h["slack_ps"]))
    for n, r in sorted(T.items()):
        if r["kind"] != "sink" or not r["master"].startswith("ot_"): continue
        p, m = [], r["parent"]
        while m != "port:ck": p.append(T[m]); m = T[m]["parent"]
        g = next((q for q in p if q["master"].startswith("ICG")), None)
        ins = INS_FF_MAX.get(r["master"])
        ideal = med - ins if ins else float("nan")
        pin = float(r["in_min_r"])
        w.write(f"{t}\t{re.sub(r'^u_g.u_tile.u_tile.u_logic.', '', n)}\t{r['master']}\t{sum(q['inst'].startswith('mp_a0_m') for q in p)}\t"
                f"{float(g['out_min_r']) if g else float('nan'):.1f}\t{pin:.1f}\t{float(Tt[n]['in_min_r']):.1f}\t{ideal:.1f}\t{pin - ideal:.1f}\t"
                f"{len(f[n])}\t{min(f[n]) if f[n] else 0:.2f}\n")
w.close()
print(open(f"{D}/macro_tap.tsv").read())
