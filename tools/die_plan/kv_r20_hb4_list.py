"""CLOCK-KV-R20 HB4 per-endpoint insertion list (plan-side; DIAGNOSTIC, UNCHECKED).

Inputs: the R20 capture pickle (die_sta_related per-endpoint-path TT/FF records of the gate run, identical args to the
R19 gate), the plan and the clock build (mesh.json taps).  For every seam bit (DC.seam_pairs geometry: the pin point
on the src face, nearest src/dst taps) this resolves the actual launch / capture register owner -- the hard core of
the src / dst partition whose die-frame outline holds the pin (else partition glue) -- and takes k from THAT endpoint
path (launch model x capture model) of the seam class, not the pair's worst path.  Writes:
  hb4_bits.tsv      one row per seam bit receiver (dst part, dst type, receiver core inst/module or GLUE, port, bit,
                    capture tap, k_endpoint, k_gate[pair worst], endpoint models)
  hb4_templates.tsv receiving template (dst type, receiver, type-level bus, bit) -> k_template = max over instances
  hb4_list.json     totals: gate count (pair-worst k x bits, = die_sta_related hb4.seam), per-endpoint count,
                    replicated-template count (every instance of a type carries the template k), by receiver kind."""
import sys, json, math, pickle, argparse
from collections import defaultdict
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("pkl"); ap.add_argument("plan"); ap.add_argument("proof"); ap.add_argument("--out", required=True)
ap.add_argument("--real", default="kv3_head_eighth_e1,kv3_head_eighth_e5")
ap.add_argument("--tol-um", type=float, default=1.0)
a = ap.parse_args()
import schema as S
import die_clock as DC
import die_sta_related as R
HB = R.HB4
real = set(a.real.split(","))
P = S.Plan(S.load(a.plan))
d = pickle.load(open(a.pkl, "rb"))
recs = dict(zip(d["classes"], d["recs"]))
tt, ff = recs["seam"]
kof = lambda h: max(0, math.ceil(-h / HB["ff_early_ps"] - 1e-9)) if h < 0 else 0
pairk = defaultdict(int)
for key, v in ff.items():
    if key in tt:
        pairk[(key[0], key[1])] = max(pairk[(key[0], key[1])], kof(v[1]))
M = json.loads((Path(a.proof) / "mesh.json").read_text())
gtaps = set(x[0] for x in ff) | set(x[1] for x in ff)
tb = defaultdict(list)
for t in M["taps"]:
    if t["port"] in gtaps:
        tb[t["part"]].append(dict(port=t["port"], part=t["part"], xy=t["xy"]))
# die-frame hard-core rects per partition
crect = defaultdict(list)
for n, p in P.parts.items():
    for h in P.types[p["type"]].get("hard_cores", []) or []:
        ox, oy = map(float, h["origin_um"]); w, hh = map(float, h["outline_um"])
        xs, ys = zip(*[P.to_die(n, q) for q in ((ox, oy), (ox + w, oy + hh))])
        crect[n].append((min(xs), min(ys), max(xs), max(ys), h["inst"], h["module"]))
def owner(part, pt):
    for x0, y0, x1, y1, inst, mod in crect.get(part, []):
        if x0 - a.tol_um <= pt[0] <= x1 + a.tol_um and y0 - a.tol_um <= pt[1] <= y1 + a.tol_um:
            return inst, mod
    return "GLUE", None
rows = []
miss = 0
for pid, pr in P.ports.items():
    sa, sb = pr["src"]["part"], pr["dst"]["part"]
    if S.DIE_PART in (sa, sb) or sa not in tb or sb not in tb:
        continue
    ra = P.rect(sa); f = pr["face"]
    for bit, lay, c in P.port_pins(pid):
        pt = ((ra[2] if f == "E" else ra[0]), c) if f in "EW" else (c, (ra[3] if f == "N" else ra[1]))
        ta = min(tb[sa], key=lambda t: abs(t["xy"][0] - pt[0]) + abs(t["xy"][1] - pt[1]))["port"]
        tbp = min(tb[sb], key=lambda t: abs(t["xy"][0] - pt[0]) + abs(t["xy"][1] - pt[1]))["port"]
        si, sm = owner(sa, pt); di, dm = owner(sb, pt)
        ma = f"core:{sm}" if sm in real else "budget"; mb = f"core:{dm}" if dm in real else "budget"
        tag = f"{sa}->{sb}"
        key = (ta, tbp, tag, ma, mb)
        if key not in ff:
            alt = [k for k in ff if k[:3] == (ta, tbp, tag)]
            miss += 1
            key = (ta, tbp, tag, "budget", "budget") if (ta, tbp, tag, "budget", "budget") in ff else (alt[0] if alt else None)
        h = ff[key][1] if key else None
        s = tt[key][0] if key and key in tt else None
        ke = kof(h) if h is not None else None
        rows.append(dict(pid=pid, bit=bit, src_part=sa, src_core=si, src_mod=sm or "", dst_part=sb,
                         dst_type=P.parts[sb]["type"], dst_core=di, dst_mod=dm or "", dst_bus=pr["dst"]["bus"],
                         launch_tap=ta, capture_tap=tbp, model=f"{key[3]}>{key[4]}" if key else "NONE",
                         ff_hold_ps=round(h, 2) if h is not None else "", tt_setup_ps=round(s, 2) if s is not None else "",
                         k_endpoint=ke, k_gate=pairk[(ta, tbp)]))
cols = list(rows[0])
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
with open(out / "hb4_bits.tsv", "w") as g:
    g.write("\t".join(cols) + "\n")
    for r in rows:
        g.write("\t".join(str(r[c]) for c in cols) + "\n")
# templates: (dst type, receiver core inst|GLUE, dst bus, bit-in-bus) -> max k over instances
tk = defaultdict(int); tinst = defaultdict(set)
for r in rows:
    t = (r["dst_type"], r["dst_core"], r["dst_bus"], r["bit"])
    tk[t] = max(tk[t], r["k_endpoint"] or 0); tinst[t].add(r["dst_part"])
with open(out / "hb4_templates.tsv", "w") as g:
    g.write("dst_type\treceiver\tdst_bus\tbit\tk_template\tinstances\n")
    for t in sorted(tk):
        g.write("\t".join(map(str, t)) + f"\t{tk[t]}\t{len(tinst[t])}\n")
tot = lambda f: sum(f(r) for r in rows)
templ_cells = sum(tk[t] * len(tinst[t]) for t in tk)
byk = defaultdict(lambda: [0, 0, 0]); bytype = defaultdict(lambda: [0, 0, 0])
for r in rows:
    kind = "real-core" if r["dst_mod"] in real else ("planned-core" if r["dst_core"] != "GLUE" else "glue")
    byk[kind][0] += 1; byk[kind][1] += r["k_endpoint"] or 0; byk[kind][2] += r["k_gate"]
    b = bytype[r["dst_type"]]; b[0] += 1; b[1] += r["k_endpoint"] or 0; b[2] += r["k_gate"]
res = dict(schema="opentallas.kv_r20.hb4_list.v1", status="UNCHECKED (plan-side list, own script)",
           model=HB, bits=len(rows), records_fallback_to_budget=miss,
           cells_gate_pairworst=tot(lambda r: r["k_gate"]),
           cells_per_endpoint=tot(lambda r: r["k_endpoint"] or 0),
           cells_template_replicated=templ_cells,
           area_mm2=dict(gate=round(tot(lambda r: r["k_gate"]) * HB["area_um2"] / 1e6, 4),
                         per_endpoint=round(tot(lambda r: r["k_endpoint"] or 0) * HB["area_um2"] / 1e6, 4),
                         template=round(templ_cells * HB["area_um2"] / 1e6, 4)),
           bits_needing_hb_per_endpoint=sum(1 for r in rows if r["k_endpoint"]),
           templates=len(tk), templates_needing_hb=sum(1 for v in tk.values() if v),
           by_receiver_kind={k: dict(bits=v[0], cells_endpoint=v[1], cells_gate=v[2]) for k, v in byk.items()},
           by_dst_type={k: dict(bits=v[0], cells_endpoint=v[1], cells_gate=v[2]) for k, v in sorted(bytype.items(), key=lambda x: -x[1][1])},
           k_hist_endpoint={str(k): sum(1 for r in rows if (r["k_endpoint"] or 0) == k) for k in sorted(set(r["k_endpoint"] or 0 for r in rows))})
json.dump(res, open(out / "hb4_list.json", "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k not in ("by_dst_type",)}, indent=0))
