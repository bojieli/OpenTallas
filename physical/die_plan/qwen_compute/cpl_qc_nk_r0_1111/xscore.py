"""CPL-QC-NK-R0: channel-crossing score of the NK data links per type under each R0/MY orient set.
Channels: W (x < left column), M (between columns), E (x > right column).  A link from channel a to channel b
must cross |a-b| NK macro widths (458 um each, over the macro or around it).  Data pins (n_a/n_b/n_y/t_out) sit on
the core W edge in R0 and the E edge in MY; tap/ck/rst/tile_id on the other edge."""
import json, sys, itertools, re, subprocess
plan, rtldir, rtl_links = sys.argv[1:4]
p = json.load(open(plan))
ALIAS = {"cbf_q11": "qfd_qc_cb_f_q11", "cbf_q01": "qfd_qc_cb_f_q01__cbf_q01", "cbf_q01_s2": "qfd_qc_cb_f_q01__cbf_q01_s2",
         "cbf_q00_s2": None}
def chan_of_core(h, orient, data=True):
    left = h["origin_um"][0] < 400
    west_edge = (orient in ("R0", "MX")) == data
    return (0 if west_edge else 1) if left else (1 if west_edge else 2)
def chan_of_x(x, T):
    xs = sorted(h["origin_um"][0] for h in T["hard_cores"] if h["module"].startswith("qfd_tile_n"))
    return 0 if x < xs[0] else (1 if x < xs[-1] else 2)
out = {}
for t, T in sorted(p["partition_types"].items()):
    hc = {h["inst"]: h for h in T.get("hard_cores", []) if h["module"].startswith("qfd_tile_n")}
    if not any(h["module"] == "qfd_tile_nk_a0c" for h in hc.values()):
        continue
    sv = ALIAS.get(t, t)
    try:
        J = json.loads(subprocess.check_output(["python3", "-I", rtl_links, f"{rtldir}/{sv}.sv"], stderr=subprocess.DEVNULL))
        links = [l for l in J["links"] if not l["dst"].endswith(".tap") and "." in l["src"] and l["src"].split(".")[0] in hc]
    except Exception:
        links = None
    buses = [b for b in T["buses"] if b["leaf"].split(".")[0] in hc]
    def score(orients):
        rows = []
        for l in links or []:
            a, b = l["src"].split(".")[0], l["dst"].split(".")[0]
            d = abs(chan_of_core(hc[a], orients[a]) - chan_of_core(hc[b], orients[b]))
            rows.append((f"{l['src']}->{l['dst']} D{l['depth']}{l['cnt']}", d))
        for bu in buses:
            i = bu["leaf"].split(".")[0]
            c = chan_of_core(hc[i], orients[i])
            f = bu["face"]
            fc = 0 if f == "W" else 2 if f == "E" else chan_of_x(sum(bu["window_um"]) / 2, T)
            # an S/N window under a macro reaches either neighbour channel through the face strip: count the nearer
            if f in "SN":
                xs = sorted(h["origin_um"][0] for h in hc.values()); w = 457.92; xm = sum(bu["window_um"]) / 2
                under = [k for k, x0 in enumerate(xs) if x0 <= xm <= x0 + w]
                cands = [k + q for k in under for q in (0, 1)] or [fc]
                d = min(abs(c - q) for q in cands)
            else:
                d = abs(c - fc)
            rows.append((f"bus {bu['name']} {bu['dir']} {bu['leaf']} face {f}", d))
        return rows
    cur = {i: h["orient"] for i, h in hc.items()}
    res = []
    for combo in itertools.product(("R0", "MY"), repeat=len(hc)):
        o = dict(zip(hc, combo)); r = score(o)
        res.append((sum(1 for _, d in r if d >= 2), sum(d for _, d in r), o, r))
    res.sort(key=lambda z: (z[0], z[1], sum(z[2][i] != cur[i] for i in hc)))
    rc = score(cur)
    # S2 rule: only right-column MY tiles that carry no type face bus are eligible; pick the eligible subset with the
    # fewest double crossings, then the fewest crossings, then the fewest flips; keep it only if it strictly improves
    xr = max(h["origin_um"][0] for h in hc.values())
    busleaf = {b["leaf"].split(".")[0] for b in T["buses"]}
    elig = [i for i, h in hc.items() if h["origin_um"][0] == xr and h["orient"] == "MY" and i not in busleaf]
    best = None
    for k in range(len(elig) + 1):
        for sub in itertools.combinations(elig, k):
            o = dict(cur); o.update({i: "R0" for i in sub}); r = score(o)
            key = (sum(1 for _, d in r if d >= 2), sum(d for _, d in r), len(sub))
            if best is None or key < best[0]:
                best = (key, sub, r)
    c0 = (sum(1 for _, d in rc if d >= 2), sum(d for _, d in rc))
    pick = list(best[1]) if links is not None and best[0][:2] < c0 else []
    out[t] = dict(eligible=elig, pick=pick, pick_doubles=best[0][0], pick_total=best[0][1], pick_rows=best[2],
                  cur=cur, cur_rows=rc, cur_doubles=sum(1 for _, d in rc if d >= 2), cur_total=sum(d for _, d in rc),
                  best=[dict(orients=o, doubles=a, total=b) for a, b, o, _ in res[:4]], links_found=links is not None)
    print(f"== {t} ELIGIBLE {elig} PICK {pick} -> doubles {best[0][0]} total {best[0][1]}")
    print(f"== {t}  links={'rtl' if links is not None else 'NONE'}  cur {cur} doubles {out[t]['cur_doubles']} total {out[t]['cur_total']}")
    for n, d in rc:
        print(f"     {d}  {n}")
    for a, b, o, r in res[:3]:
        print(f"   best doubles {a} total {b} {o}")
json.dump(out, open(sys.argv[4], "w"), indent=1)
