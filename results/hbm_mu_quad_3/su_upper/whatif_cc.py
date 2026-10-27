#!/usr/bin/env python3
"""cc_price.py clone with what-if overrides (model only).  mode:
  asis      = cc_price.py exactly (check: must reproduce U2_cc.json ops)
  partners  = coloc restricted to VM-service replica <-> non-bank partner legs and vmks<->ctl_p0x legs
  re:<rx>   = coloc restricted to conns matching regex rx
  coloc     = conns whose route grew > GROW um vs baseline get base regs + (serial_k-1)  (partners co-located with their
              segment service copy; cut serialisation kept)
  noserial  = drop the serial_k-1 term (cut serialisation share)
Usage: whatif_cc.py W base_plan cand_plan mode out.json [GROW]"""
import json, sys, re, os, collections, importlib.util
NOSER = os.environ.get("NOSER")
W, base, cand, mode, out = sys.argv[1:6]; GROW = float(sys.argv[6]) if len(sys.argv) > 6 else 1000.0
spec = importlib.util.spec_from_file_location("T", W + "/tools/hbm_b2/b1_lane_traversal.py"); T = importlib.util.module_from_spec(spec)
sys.argv = ["x"]; spec.loader.exec_module(T)
def L(s): return sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip([s["from_um"]]+s["regs_um"], s["regs_um"]+[s["to_um"]]))
def load(p, ser=True):
    P = json.load(open(p + "/die_plan.json")); r = {}
    for tn in ("q_hub_nw", "q_hub_ne"):
        d = {}
        for s in P["partition_types"][tn]["internal_stations"]:
            if "bus:" in str(s.get("conn")): continue
            k = max(int(s.get("serial_k") or 1) - 1, 0)
            if NOSER and re.search(NOSER, str(s.get("conn"))): k = 0   # env NOSER=<regex>: those legs get the tracks (k=1)
            c = (len(s["regs_um"]) + (k if ser else 0), L(s), k)
            if c[0] >= d.get(s["conn"], (-1,))[0]: d[s["conn"]] = c
        r[tn] = d
    return r
B, C = load(base), load(cand, ser=(mode != "noserial"))
inst = lambda x: x.split(".")[0]
fam = lambda x: T.family(re.sub(r"__q\d+$", "", inst(x)))
edges = collections.defaultdict(dict); nover = 0; over = []
for tn in B:
    for conn, c in C[tn].items():
        if conn not in B[tn]: continue
        cc = c[0]
        l0, c0 = (inst(x) for x in conn.split("|"))
        svc = lambda i: re.match(r"u_(hb_vms|xl_Q_ctl|hb_dbk|smw|calendar|vmdel)", i)
        bank = lambda i: re.match(r"u_(vmb_|mu_fused|hcb)", i)
        part = (svc(l0) and not bank(c0) and not svc(c0)) or (svc(c0) and not bank(l0) and not svc(l0)) or                (re.match(r"u_(vmks|ctl_Q_p0)", l0) and re.match(r"u_(vmks|ctl_Q_p0)", c0))
        if (mode == "coloc" or (mode == "partners" and part) or (mode.startswith("re:") and re.search(mode[3:], conn))) and c[1] - B[tn][conn][1] > GROW:
            cc = B[tn][conn][0] + c[2]; nover += 1; over.append((tn, conn, c[0], cc, round(c[1]), round(B[tn][conn][1])))
        d = cc - B[tn][conn][0]; l, cap = conn.split("|")
        a = re.sub(r"(_Q\d*|__q\d+)$", "", inst(l)); b = re.sub(r"(_Q\d*|__q\d+)$", "", inst(cap))
        for f in {fam(l), fam(cap)}: edges[f][(a, b)] = max(edges[f].get((a, b), -99), d)
def longest(E):
    g = collections.defaultdict(list)
    for (a, b), d in E.items():
        if a != b and d > 0: g[a].append((b, d))
    def go(n, seen):
        return max([d + go(m, seen | {m}) for m, d in g.get(n, ()) if m not in seen] + [0])
    return max([go(n, {n}) for n in list(g)] or [0])
res = dict(mode=mode, grow_um=GROW, overridden=nover, overridden_sample=sorted(over, key=lambda x: x[2]-x[3], reverse=True)[:25], ops={})
for op, fs in T.OP_FAMILIES:
    res["ops"][op] = dict(families=fs, lower=max([max(list(edges[f].values()) or [0]) for f in fs] + [0]),
                          upper=max([longest(edges[f]) for f in fs] + [0]))
json.dump(res, open(out, "w"), indent=1); print(mode, nover, {k: (v["lower"], v["upper"]) for k, v in res["ops"].items()})
