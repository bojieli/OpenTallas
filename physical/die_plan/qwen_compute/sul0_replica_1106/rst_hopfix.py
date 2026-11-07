"""DQ85-SUL0 vC 11-06: kit-local reset relay re-site (placement only, no RTL / cycle change).

usage: rst_hopfix.py KIT [--check-only]

A synchronous reset relay hop whose two L routes both run over a lane macro (the lanes OBS M1-M6) overflowed GRT
in vA/vB (u_rrl_35, u_rrl_39, u_rrl_26, u_srl_26, 470 gcells each).  This script moves the driver relays of those hops
onto channel / strip points.  It keeps relay order, depth, kind and the lane tap sites unchanged, then proves:
  every hop (q <- d of the reset_tree.tcl hop list) <= 380 um (plan reach, kit limit 405), and
  every hop has one L route outside every grown lane box (CLEAR 4.32 um).
Rewrites reset_tree.tcl (rtr_place x y), and bound_native_reset.json tree / physical_nodes / source_authority xy
(record only; no flow script reads it).  Writes rst_hopfix.json (before/after per hop).
"""
import json, re, sys
from pathlib import Path

K = Path(sys.argv[1]); check_only = "--check-only" in sys.argv
CLEAR, PLAN, LIM = 4.32, 380.0, 405.0
# key (rtr_place first arg; rn_ copies follow) -> new site
MOVE = {
    # lane0 tap u_rrl_35 (397.272, 30.252): its driver u_rrl_34 sat in the lane0/lane1 gap -> the hop crossed lane0
    "rst_rl_33": (609.132, 300.000), "rst_rl_34": (609.132, 30.252),
    # lane1 tap u_rrl_39 (381.528, 349.932): driver u_rrl_38 sat in the lane1/lane2 gap -> crossed lane1
    "rst_rl_37": (609.132, 600.000), "rst_rl_38": (609.132, 349.932),
    # lane3 north relay u_rrl_26 (-> tap u_rrl_27 at 19.0/1322.0): from u_rrl_25 in the lane2/lane3 gap -> crossed lane3
    "rst_rl_25": (185.772, 1041.132), "rst_rl_26": (185.772, 1317.612),
    # lane3 north relay u_rrl_30 (-> tap u_rrl_31 at 128.0/1322.0): from u_rrl_29 at x 565.8 -> crossed lane3
    "rst_rl_28": (609.132, 1100.000), "rst_rl_29": (609.132, 1317.612), "rst_rl_30": (400.000, 1317.612),
}
for k in list(MOVE):
    MOVE["rn_" + k] = MOVE[k]

tcl = (K / "reset_tree.tcl").read_text()
mp = (K / "macro_place.tcl").read_text()
lanes = [(float(x), float(y)) for x, y in re.findall(r"u_bound\.u_lane\d\} -location \{([\d.]+) ([\d.]+)\}", mp)]
W, H = 414.72, 267.84
boxes = [(x - CLEAR, y - CLEAR, x + W + CLEAR, y + H + CLEAR) for x, y in lanes]
site_re = re.compile(r"^(rtr_place(?:_opt)? (\S+) (\{[^}]*\}) )([\d.]+) ([\d.]+)( .*)$", re.M)
sites = {m.group(2): (float(m.group(4)), float(m.group(5))) for m in site_re.finditer(tcl)}
missing = [k for k in MOVE if k not in sites and not k.startswith("rn_rn_")]
assert not [k for k in missing if not k.startswith("rn_") or k[3:] not in MOVE], missing
hl = re.search(r"foreach \{q d\} \{([^}]*)\}", tcl).group(1).split()
hops = list(zip(hl[0::2], hl[1::2]))


def seg_hits(p, q):
    lx, hx, ly, hy = min(p[0], q[0]), max(p[0], q[0]), min(p[1], q[1]), max(p[1], q[1])
    return any(lx < c - 1e-6 and hx > a + 1e-6 and ly < d - 1e-6 and hy > b + 1e-6 for a, b, c, d in boxes)


def lfree(p, q):
    return any(not seg_hits(p, m) and not seg_hits(m, q) for m in ((q[0], p[1]), (p[0], q[1])))


def inside(p):
    return any(a + 1e-6 < p[0] < c - 1e-6 and b + 1e-6 < p[1] < d - 1e-6 for a, b, c, d in boxes)


def report(S):
    rows, bad = [], []
    for q, d in hops:
        if q not in S or d not in S:
            continue
        h = abs(S[q][0] - S[d][0]) + abs(S[q][1] - S[d][1])
        ok = lfree(S[q], S[d])
        rows.append(dict(q=q, d=d, hop_um=round(h, 3), lfree=ok, q_xy=S[q], d_xy=S[d]))
        if not ok or h > PLAN + 1e-6:
            bad.append(rows[-1])
    return rows, bad


before, bad0 = report(sites)
new = dict(sites); new.update({k: v for k, v in MOVE.items() if k in sites})
after, bad1 = report(new)
inb = [k for k, v in new.items() if inside(v)]
print("BEFORE crossing/long hops:", [(b["d"], "->", b["q"], b["hop_um"], b["lfree"]) for b in bad0])
print("AFTER  crossing/long hops:", [(b["d"], "->", b["q"], b["hop_um"], b["lfree"]) for b in bad1])
print("AFTER  max hop %.1f um, sites inside a grown lane box: %s" % (max(r["hop_um"] for r in after), inb))
moved = sorted(k for k in MOVE if k in sites)
print("moved %d sites:" % len(moved), ", ".join(f"{k} {sites[k]}->{new[k]}" for k in moved))
if bad1 or inb:
    sys.exit("FAIL: re-site leaves a crossing / long hop")
if check_only:
    sys.exit(0)
out = site_re.sub(lambda m: m.group(0) if m.group(2) not in MOVE else
                  f"{m.group(1)}{MOVE[m.group(2)][0]:.3f} {MOVE[m.group(2)][1]:.3f}{m.group(6)}  ;# DQ85-SUL0 vC re-site", tcl)
(K / "reset_tree.tcl").write_text(out)
# record the same sites in the bound native contract (tree relays by q label, physical nodes by q label)
J = K / "bound_native_reset.json"
d = json.loads(J.read_text())
def fix(tree):
    for r in tree.get("relays", []):
        if r["q"] in MOVE:
            r["xy"] = list(MOVE[r["q"]])
fix(d["tree"])
if isinstance(d.get("source_authority"), dict) and "tree" in d["source_authority"]:
    fix(d["source_authority"]["tree"])
for n in d.get("physical_nodes", []):
    if n.get("q") in MOVE:
        n["xy"] = list(MOVE[n["q"]])
J.write_text(json.dumps(d, indent=1))
(K / "rst_hopfix.json").write_text(json.dumps(dict(moved={k: [sites[k], new[k]] for k in moved}, before=before,
                                                  after=after), indent=1))
print("WROTE reset_tree.tcl, bound_native_reset.json, rst_hopfix.json")
