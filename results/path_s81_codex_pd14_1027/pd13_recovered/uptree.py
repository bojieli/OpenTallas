"""PATH-S81-PD13 (2): upper-tree delay model per level (model only, UNCHECKED).
Stage = buffer (k x BUFx<sz> in parallel, NLDM at slew_in, load/k) + Elmore wire (r,c per um of NDR w, PD10 global
calibration kr 1.0 / kc 1.4) to the next stage input; slew at far end = sqrt(s_out^2 + (2.2 Elmore)^2).
Per level: median leg of the routed me1v H-tree (len_um, n_seg) -> per-stage split (cell / wire) + RCX delay check.
usage: uptree.py BUILD_DIR CORNER LEGS_JSON"""
import json, sys, math, statistics as st, collections
import die_clock as DC, die_clock_128 as C128, die_clock_mesh as DM
B, C, LJ = sys.argv[1:4]
KR, KC = 1.0, 1.4
SZ = ("BUFx24_ASAP7_75t_R", "BUFx16f_ASAP7_75t_R", "BUFx12f_ASAP7_75t_R")
libs = C128.lib_cells(C, DM.Path("~/.cache/opentallas/asap7_nldm").expanduser(), SZ)
def rc(w):
    if w in DM.NDR: r, c = C128.wire_rc(DM.NDR[w], DC.LAYER_RC)
    else:   # extrapolated wide NDR (same per-width scaling as 16w: rf 1/(w/4)*0.25, cf from the RC_R6 strap fit 0.9+0.0875w)
        n = int(w.rstrip("w")); r16, c16 = C128.wire_rc(DM.NDR["16w"], DC.LAYER_RC)
        r, c = r16 * 16 / n, c16 * (0.9 + 0.0875 * n) / (0.9 + 0.0875 * 16)
    return r * KR, c * KC
def stage(w, l, s_in, k=1, buf=SZ[0], cnext=None):
    r, c = rc(w); L = libs[buf]; cin = L["cap"] * k
    cn = cin if cnext is None else cnext
    cl = c * l + cn
    d = C128._bilin(L["delay"], s_in, cl / k); so = C128._bilin(L["trans"], s_in, cl / k)
    el = r * l * (c * l / 2 + cn)
    return d, el, math.sqrt(so ** 2 + (2.2 * el) ** 2)
def leg(w, length, nseg, s_in, k=1, buf=SZ[0], fan=2):
    """leg = nseg equal segments; last segment drives the child node (fan-out 2 branches of the next level are lumped
    into the child node's own stage, so the child node input = 1 buffer cin)."""
    l = length / nseg; dc = dw = 0.0; s = s_in
    for i in range(nseg):
        d, e, s = stage(w, l, s, k, buf); dc += d; dw += e
    return dc, dw, s
rows = json.load(open(LJ))
by = collections.defaultdict(list)
for x in rows:
    if x["dly"] is not None: by[x["level"]].append(x)
med = {L: dict(len=st.median(x["len_um"] for x in v), nseg=collections.Counter(x["n_seg"] for x in v).most_common(1)[0][0],
               rcx=st.median(x["dly"] for x in v), n=len(v)) for L, v in sorted(by.items())}
def path(cfg, cap=None):
    """cfg(level) -> (w, k, buf); cap = max segment um (re-segment legs to ceil(len/cap)); returns per-level rows"""
    s = 40.0; out = []
    for L, m in med.items():
        w, k, buf = cfg(L)
        ns = m["nseg"] if cap is None else max(m["nseg"], math.ceil(m["len"] / cap))
        dc, dw, s2 = leg(w, m["len"], ns, s, k, buf)
        out.append(dict(L=L, len=round(m["len"]), nseg=ns, seg_um=round(m["len"] / ns), w=w, k=k, cell=round(dc, 1), wire=round(dw, 1),
                        tot=round(dc + dw, 1), rcx=round(m["rcx"], 1), slew=round(s2, 1)))
        s = s2
    return out
def summ(name, P):
    tot = sum(r["tot"] for r in P); st_ = sum(r["nseg"] for r in P)
    return dict(name=name, insertion_ps=round(tot), stages=st_, cell_ps=round(sum(r["cell"] for r in P)), wire_ps=round(sum(r["wire"] for r in P)),
                max_slew=max(r["slew"] for r in P), path_um=round(sum(r["len"] for r in P)))
res = {}
base = path(lambda L: ("4w", 1, SZ[0]))
res["base_4w_x24"] = dict(summary=summ("base", base), levels=base, rcx_sum=round(sum(m["rcx"] for m in med.values())))
up = lambda w, k, Lmax=9: (lambda L: (w, k, SZ[0]) if L <= Lmax else ("4w", 1, SZ[0]))
for name, cfg, cap in [("base_cap405", lambda L: ("4w", 1, SZ[0]), 405),
                       ("8w_L1-9", up("8w", 1), 405), ("16w_L1-9", up("16w", 1), 405),
                       ("8w_L1-9_x2", up("8w", 2), 405), ("16w_L1-9_x2", up("16w", 2), 405), ("32w_L1-9_x2", up("32w", 2), 405),
                       ("16w_L1-9_x3", up("16w", 3), 405), ("16w_all_x2", up("16w", 2, 12), 405),
                       ("8w_all_x2", up("8w", 2, 12), 405)]:
    P = path(cfg, cap); res[name] = dict(summary=summ(name, P), levels=P)
for k, v in res.items(): print(json.dumps(v["summary"]))
print("base levels"); [print(json.dumps(r)) for r in base]
print("16w_L1-9_x2 levels"); [print(json.dumps(r)) for r in res["16w_L1-9_x2"]["levels"]]
json.dump(res, open(f"uptree_{C}.json", "w"), indent=1)
# --- inverter repeaters (ASAP7 INVx11/INVx13): per stage the WORSE of cell_rise/cell_fall and of the transitions
import gzip, re
txt = gzip.open(DM.Path("~/.cache/opentallas/asap7_nldm").expanduser() / f"asap7sc7p5t_INVBUF_RVT_{C}_nldm_220122.lib.gz", "rt").read()
def inv(n):
    i = txt.index(f"cell ({n})"); j = txt.find("cell (", i + 10); blk = txt[i:j]
    r, f = C128._table(blk, "cell_rise"), C128._table(blk, "cell_fall")
    tr, tf = C128._table(blk, "rise_transition"), C128._table(blk, "fall_transition")
    mx = lambda a, b: (a[0], a[1], [[max(x, y) for x, y in zip(ra, rb)] for ra, rb in zip(a[2], b[2])])
    return dict(delay=mx(r, f), trans=mx(tr, tf), cap=float(re.search(r"rise_capacitance : ([\d.]+)", blk).group(1)))
for n in ("INVx13_ASAP7_75t_R", "INVx11_ASAP7_75t_R"):
    libs[n] = inv(n)
print("cin", {k: v["cap"] for k, v in libs.items()})
for name, w, k, buf in [("16w_L1-9_INVx13", "16w", 1, "INVx13_ASAP7_75t_R"), ("16w_L1-9_INVx13_x2", "16w", 2, "INVx13_ASAP7_75t_R"),
                        ("8w_L1-9_INVx13_x2", "8w", 2, "INVx13_ASAP7_75t_R"), ("16w_L1-9_INVx13_x3", "16w", 3, "INVx13_ASAP7_75t_R"),
                        ("32w_L1-9_INVx13_x3", "32w", 3, "INVx13_ASAP7_75t_R")]:
    P = path(lambda L, w=w, k=k, buf=buf: (w, k, buf) if L <= 9 else ("4w", 1, SZ[0]), 405)
    res[name] = dict(summary=summ(name, P), levels=P); print(json.dumps(res[name]["summary"]))
json.dump(res, open(f"uptree_{C}.json", "w"), indent=1)
