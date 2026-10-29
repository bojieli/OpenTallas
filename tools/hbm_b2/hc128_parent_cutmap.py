#!/usr/bin/env python3
"""HBM-BIND-3 (a): native128 parent cut map for the as-built hcb_* banks (W128).

For each bank (16) and pair k (8): members = lane leaves u_st.g_lg.g_grp[2k],[2k+1].u_lg, weight macros
g_w[2k],[2k+1], x macro g_x[k], and the exact wdat/xdat capture bits read from those macros (primitive split of the
wide capture $dff, as tools/hbm_b2/hc128_split_capture.py).  Ports = the boundary nets, labelled with the native128
pin ABI names (physical/die_plan/hbm_arch_cores/native128/*_pins.json); every member terminal on a port net is
anchored.  tools/die_plan/bind_compose.py then proves terminal equality; no logic, cycle or constant changes.
Output: compose JSON = base compose (HBM-BIND-1 b1 SU/SFU cores) + 128 hcb pair cores + capture splits.
usage: hc128_parent_cutmap.py FLAT.pkl BASE_COMPOSE.json OUT.json
"""
import collections
import json
import pickle
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "die_plan"))
flat, base_compose, out = sys.argv[1:4]
F = pickle.load(open(flat, "rb"))
byp = {c.path: c for c in F.cells}
banks = sorted({c.path.split(".")[0] for c in F.cells if re.match(r"hcb_[NS][EW]\d+\.", c.path)})
spec = json.loads(Path(base_compose).read_text())
topnets = {b for _, bs in F.top_ports.values() for b in bs if isinstance(b, int)}
# net -> set(cell paths) over the whole die, once
net_cells = collections.defaultdict(set)
for c in F.cells:
    for bs in c.ports.values():
        for b in bs:
            if isinstance(b, int):
                net_cells[b].add(c.path)
cores, splits, report = [], [], []

LANE = {"rst_n": "rst_n", "fst": "first", "gov_i": "go", "lf": "fault"}


def label(role, j, p, i):
    if p in ("clk", "CLK"):
        return ("clk", 0)
    if role == "lane":
        if p in LANE:
            return (LANE[p], j if p == "lf" else 0)
        return {"lv_i": ("lane_valid", 8 * j + i), "ss_i": ("square", 8 * j + i), "s_i": ("sum_in", 256 * j + i),
                "y": ("sum_out", 256 * j + i)}.get(p, ("?lane_" + p, i))
    if role == "w":
        return {"r_ce_in": ("weight_read", 0), "r_addr_in": ("weight_addr", i), "w_ce_in": (f"weight_we{j}", 0),
                "w_addr_in": ("write_addr", i), "wd_in": ("write_data", 256 * j + i)}.get(p, ("?w_" + p, i))
    if role == "x":
        return {"r_ce_in": ("x_read", 0), "r_addr_in": ("x_addr", i), "w_ce_in": ("x_write", 0),
                "w_addr_in": ("write_addr", i)}.get(p, ("?x_" + p, i))
    return ("?cap_" + p, i)


for bank in banks:
    first = byp[bank + ".u_c.u_b.u_st.g_lg.g_grp[0].u_lg"].ports["fst"] == ["1"]
    mod = "ot_hbm_hc_bank128_pair_first_core" if first else "ot_hbm_hc_bank128_pair_core"
    frag = collections.defaultdict(lambda: collections.defaultdict(list))
    pairmem = {}
    bank_dffs = [c for c in F.cells if c.path.startswith(bank + ".") and c.ytype in ("$dff", "$adff")]
    for k in range(8):
        lanes = [f"{bank}.u_c.u_b.u_st.g_lg.g_grp[{g}].u_lg" for g in (2 * k, 2 * k + 1)]
        ws = [f"{bank}.u_c.u_b.g_w[{g}].u_m" for g in (2 * k, 2 * k + 1)]
        xs = [f"{bank}.u_c.u_b.g_x[{k}].u_m"]
        for p in lanes + ws + xs:
            assert p in byp, p
        rd = {b for s in ws + xs for b in byp[s].ports["rd_out"]}
        for c in bank_dffs:
            for i, b in enumerate(c.ports["D"]):
                if b in rd:
                    frag[c.path][k].append(i)
        pairmem[k] = (lanes, ws, xs)
    for dp, byk in frag.items():
        c = byp[dp]
        w = len(c.ports["Q"])
        got = sorted(i for v in byk.values() for i in v)
        assert len(got) == len(set(got)), dp
        fr = [dict(path=f"{dp}.__hc128_{k}", bits=sorted(v)) for k, v in sorted(byk.items())]
        rest = sorted(set(range(w)) - set(got))
        if rest:
            fr.append(dict(path=f"{dp}.__hc128_rest", bits=rest))
        splits.append(dict(member=dp, fragments=fr))
    for k in range(8):
        lanes, ws, xs = pairmem[k]
        caps = [f"{dp}.__hc128_{k}" for dp, byk in sorted(frag.items()) if k in byk]
        members = lanes + ws + xs + caps
        role = {}
        for j, m in enumerate(lanes):
            role[m] = ("lane", j)
        for j, m in enumerate(ws):
            role[m] = ("w", j)
        role[xs[0]] = ("x", 0)
        for m in caps:
            role[m] = ("cap", 0)

        def ports_of(m):
            if m in byp:
                c = byp[m]
                return c.ports, c.dirs
            dp, _, kk = m.rpartition(".__hc128_")
            c = byp[dp]
            bits = frag[dp][int(kk)]
            return {p: ([bs[i] for i in bits] if p in ("D", "Q") else bs) for p, bs in c.ports.items()}, c.dirs

        net_terms = collections.defaultdict(list)
        for m in members:
            ps, ds = ports_of(m)
            for p, bs in ps.items():
                for i, b in enumerate(bs):
                    if isinstance(b, int):
                        net_terms[b].append((m, p, i, ds[p]))
        orig_members = {m for m in members if m in byp}
        cap_parents = {m.rpartition(".__hc128_")[0] for m in caps}
        boundary = []
        for b in net_terms:
            others = net_cells[b] - orig_members
            # a split capture parent appears in net_cells; it is outside only through bits/controls not in this pair
            ext = False
            for o in others:
                if o in cap_parents:
                    c = byp[o]
                    mine = set(frag[o][k])
                    for p, bs in c.ports.items():
                        for i, bb in enumerate(bs):
                            if bb == b and (p not in ("D", "Q") or i not in mine):
                                ext = True
                else:
                    ext = True
            if ext or b in topnets:
                boundary.append(b)
        prio = {"lane": 0, "w": 1, "x": 2, "cap": 3}
        lab = {}
        for b in boundary:
            ts = sorted(net_terms[b], key=lambda t: (prio[role[t[0]][0]], t[0], t[1], t[2]))
            cand = [label(role[t[0]][0], role[t[0]][1], t[1], t[2]) for t in ts]
            lab[b] = cand[0]
            # x wd_in alone (never expected): labelled by its first owner, flagged below
        ports = collections.defaultdict(dict)
        for b, (n, i) in lab.items():
            if i in ports[n]:
                raise SystemExit(f"{bank} pair{k}: duplicate {n}[{i}]")
            ports[n][i] = b
        bad = [n for n in ports if n.startswith("?")]
        if bad:
            raise SystemExit(f"{bank} pair{k}: unlabelled boundary terminals {bad}")
        pj = {}
        noncontig = {}
        for n, d in sorted(ports.items()):
            idx = sorted(d)
            if idx != list(range(len(idx))):
                noncontig[n] = idx
            bits, dirs = [], set()
            for i in idx:
                b = d[i]
                anchors = [dict(member=t[0], port=t[1], bit=t[2]) for t in net_terms[b]]
                dirs.add("output" if any(t[3] == "output" for t in net_terms[b]) else "input")
                bits.append(anchors)
            assert len(dirs) == 1, (bank, k, n, dirs)
            pj[n] = dict(dir=dirs.pop(), bits=bits)
        cores.append(dict(inst=f"{bank}.ot_hbm_hc_bank128_pair{k}", module=mod, members=members, ports=pj))
        report.append(dict(inst=f"{bank}.ot_hbm_hc_bank128_pair{k}", module=mod, members=len(members),
                           ports={n: [v["dir"], len(v["bits"])] for n, v in pj.items()},
                           pins=sum(len(v["bits"]) for v in pj.values()), noncontiguous=noncontig))
spec["cores"] = spec["cores"] + cores
spec["primitive_splits"] = spec.get("primitive_splits", []) + splits
Path(out).write_text(json.dumps(spec))
Path(out).with_suffix(".report.json").write_text(json.dumps(dict(
    banks=banks, pair_cores=report,
    splits=[dict(member=s["member"], fragments=[(f["path"], len(f["bits"])) for f in s["fragments"]]) for s in splits]),
    indent=1))
print(len(banks), "banks", len(cores), "pair cores", len(splits), "capture splits")
for (m, p), n in collections.Counter((r["module"], json.dumps(r["ports"], sort_keys=True)) for r in report).most_common():
    print(n, m, sum(v[1] for v in json.loads(p).values()), p)
