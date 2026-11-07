#!/usr/bin/env python3
"""DIE-HBM-82-EP6 d44v part 51 (DIE-HBM-82 ruling 11-06 19:1x: SPLIT ot_wbq_root on the natural boundary, outline kept).

ot_wbq_root (432 x 129.6, 16 instances: q_hub_nw / q_hub_ne x q0,q1 x r0..r3, all R0) is wiring-bound at GRT (8 lanes x 288
bits into one central pick column).  It becomes, inside the SAME slot (origin and outline kept), its two lane groups:
  u_g0  ot_wbq_root_g0  216 x 129.6 at root-frame (0, 0)     lanes 0-3, group pick 0
  u_g1  ot_wbq_root_g1  216 x 129.6 at root-frame (216, 0)   lanes 4-7, group pick 1
The groups share no signal (rtl ot_wbq_split.sv: ot_wbq_root_grp, the fill/copy control is replicated), so there is no seam and
no cycle changes; ot_wbq_root_g2 (u_g0 + u_g1) is the plan glue of each slot, proven equal to ot_wbq_root (OT_WBQ_N1M) by
yosys induction (results/die_hbm_1106/wbq_g2/eq_g2.sh) and lock-step (bench_g2.sh).
One pin table for both masters (child frame): the root-table sites of group 0 (S face control + wd0-3 + wd_v[0-3], W face
control + g_d[285:0] + g_v[0] + g_credit[0]); clock pins at the child entry (108, 25.92), S logic band.
Macros in the N part so the 1373 face registers (S wd faces, W g_d face) have a free S band (probe pG: macros on the S edge -> DPL-0033).
Sidecars: core_conns (every core:<root> -> both children; child = root conns, wd4-7 -> wd0-3 for g1, sibling added on the
shared nets, root_ready of g1 is not used), clock taps + entries (one centre entry per child), core_macros (4 x
ot_sram_1r1w_128x256_m1_r0c0_g256 per child, 2 x 2).
    mk_p51.py D44V_DIR      (in place on the gz plan files of the d44v dir)"""
import copy, gzip, json, re, sys
from pathlib import Path
D = Path(sys.argv[1])
ROOT, M0, M1 = "ot_wbq_root", "ot_wbq_root_g0", "ot_wbq_root_g1"
RT = "cores/ot_wbq_root__432x129.6__d44v_split.json"
TB = "cores/ot_wbq_root_g__216x129.6__d44v_p51.json"
W, H = 216.0, 129.6
CK = (108.0, 25.92)          # clock entry in the S logic band (the macros sit in the N 2/3, clear of the S / W face registers)
r3 = lambda v: round(v + 0.0, 3)


def rd(n):
    return json.loads(gzip.decompress((D / (n + ".gz")).read_bytes()))


def wr(n, o, indent=None):
    b = (json.dumps(o, indent=indent) + "\n").encode()
    with open(D / (n + ".gz"), "wb") as f, gzip.GzipFile(fileobj=f, mode="wb", mtime=0, filename="") as g:
        g.write(b)


P, CC, CE = rd("die_plan.json"), rd("core_conns.json"), rd("clock_entries.json")
# ---- pin table
rt = json.loads((D / RT).read_text()) if (D / RT).exists() else rd(RT)
bit = lambda n: (re.sub(r"\[\d+\]$", "", n), int(re.search(r"\[(\d+)\]$", n)[1]) if n.endswith("]") else None)
tab = []
for p in rt:
    b, i = bit(p["name"])
    if b in ("fifo_clk", "hbm_clk"):
        continue
    if b in ("g_credit", "g_v"):
        if i == 0:
            tab.append(dict(p, name=b))
        continue
    if b == "g_d" and i >= 286:
        continue
    if b == "wd_v" and i >= 4:
        continue
    if b in ("wd4", "wd5", "wd6", "wd7"):
        continue
    tab.append(dict(p))
ck = {p["name"]: p for p in rt if p["name"] in ("fifo_clk", "hbm_clk")}
for n, p in ck.items():
    tab.append(dict(p, x=r3(p["x"] - 216.0 + CK[0]), y=r3(p["y"] - 64.8 + CK[1])))
assert all(0 <= p["x"] <= W and 0 <= p["y"] <= H for p in tab), [p for p in tab if not (0 <= p["x"] <= W)][:3]
names = [p["name"] for p in tab]
assert len(names) == len(set(names))
want = 4 + 12 + 30 + 4 * 256 + 4 + 4 + 2 + 2 + 1 + 1 + 1 + 286 + 2   # S ctl, totals, base, wd0-3, wd_v; W ctl, resets, root_id, root_ready, g_credit, g_v, g_d; clocks
assert len(tab) == want, (len(tab), want)
(D / TB).write_text(json.dumps(tab, indent=1) + "\n")
# ---- hard cores, taps, entries, conns
RX = re.compile(r"^core:(u_wbk_Q__q[01]__r[0-3])$")
SHARED = {"copy_bank", "copy_on", "fill_start", "fill_start_bank", "h_stop", "hbm_rst_n", "reserve_bank", "reserve_base",
          "reserve_total", "reserve_v", "s_stop", "stream_rst_n", "wd_v"}
log = []
for tn, T in P["partition_types"].items():
    hc = T.get("hard_cores") or []
    rows = [h for h in hc if h["module"] == ROOT]
    if not rows:
        continue
    roots = {h["inst"] for h in rows}
    C = CC[tn]
    # every peer ref to a root -> both children (root_ready: only g0 drives it)
    for i, ps in C.items():
        if i in roots:
            continue
        for p, v in ps.items():
            if isinstance(v, list) and any(isinstance(x, str) and RX.match(x) and RX.match(x)[1] in roots for x in v):
                nv = []
                for x in v:
                    m = RX.match(x) if isinstance(x, str) else None
                    if m and m[1] in roots:
                        nv += [f"core:{m[1]}__g0"] + ([] if p == "root_ready" else [f"core:{m[1]}__g1"])
                    else:
                        nv.append(x)
                ps[p] = nv
    for old in rows:
        assert old["outline_um"] == [432.0, 129.6] and old.get("orient", "R0") == "R0", (tn, old["inst"])
        I = old["inst"]
        new = []
        for g, mod in ((0, M0), (1, M1)):
            r = copy.deepcopy(old)
            r.update(inst=f"{I}__g{g}", module=mod, origin_um=[r3(old["origin_um"][0] + W * g), old["origin_um"][1]],
                     outline_um=[W, H], pins_file=TB, physical_inst=f"{old['physical_inst']}.u_g{g}", physical_master=mod,
                     note=f"DIE-HBM-82-EP6 d44v part 51: lane group {g} of its {ROOT} slot (slot kept; glue ot_wbq_root_g2 in "
                          f"rtl/hbm_accel/cores_split/reform_1105b/ot_wbq_split.sv) | " + old.get("note", ""))
            new.append(r)
        k = hc.index(old)
        hc[k:k + 1] = new
        taps = T["clock"]["taps"]
        ti = next(j for j, tp in enumerate(taps) if tp.get("name") == I)
        t0 = taps[ti]
        nt = []
        e0 = CE[tn].pop(I)
        assert e0["xy_um"] == [216.0, 64.8], e0
        for g, mod in ((0, M0), (1, M1)):
            t = copy.deepcopy(t0)
            t["name"] = f"{I}__g{g}"
            t["xy"] = [r3(new[g]["origin_um"][0] + new[g]["track_offset_um"][0] + CK[0]), r3(new[g]["origin_um"][1] + new[g]["track_offset_um"][1] + CK[1])]
            t["note"] = f"DIE-HBM-82-EP6 p51: group {g} centre entry tap (same insertion target as the root tap) | " + t0.get("note", "")
            nt.append(t)
            e = copy.deepcopy(e0)
            e.update(xy_um=list(CK), island_um=[r3(CK[0] - 4.32), r3(CK[1] - 4.32), r3(CK[0] + 4.32), r3(CK[1] + 4.32)], tap=f"{I}__g{g}",
                     module=mod, native_module=mod,
                     clock_pin_sites_um={n: [r3(v[0] - 216.0 + CK[0]), r3(v[1] - 64.8 + CK[1])] for n, v in e0["clock_pin_sites_um"].items()},
                     source=f"DIE-HBM-82-EP6 p51: group {g} centre entry (entry in the S logic band below the macros) | " + e0.get("source", ""))
            CE[tn][f"{I}__g{g}"] = e
        taps[ti:ti + 1] = nt
        c0 = C.pop(I)
        for g in (0, 1):
            sib = f"core:{I}__g{1 - g}"
            c = {}
            for p in ("copy_bank", "copy_on", "fill_start", "fill_start_bank", "h_stop", "hbm_rst_n", "reserve_bank", "reserve_base",
                      "reserve_total", "reserve_v", "s_stop", "stream_rst_n", "wd_v", "g_credit", "g_d", "g_v", "root_id", "root_ready",
                      "wd0", "wd1", "wd2", "wd3"):
                src = p if not (g == 1 and re.fullmatch(r"wd[0-3]", p)) else f"wd{int(p[2]) + 4}"
                if p == "root_ready" and g == 1:
                    continue
                v = []
                for x in c0[src]:
                    m = RX.match(x) if isinstance(x, str) else None
                    if m and m[1] in roots:
                        v += [f"core:{m[1]}__g0"] + ([] if p == "root_ready" else [f"core:{m[1]}__g1"])
                    else:
                        v.append(x)
                if p in SHARED or re.fullmatch(r"wd[0-3]", p):
                    v.append(sib)
                c[p] = v
            for p in c0:
                assert p in c or p in ("wd4", "wd5", "wd6", "wd7") or (p == "root_ready"), (tn, I, p)
            C[f"{I}__g{g}"] = c
        log.append((tn, I, [(n["inst"], n["origin_um"]) for n in new]))
    left = [x for x in re.findall(r"u_wbk_Q__q[01]__r[0-3](?![\w])", json.dumps(T) + json.dumps(C) + json.dumps(CE[tn]))]
    assert not left, (tn, left[:5])
wr("die_plan.json", P)
wr("core_conns.json", CC, indent=1)
wr("clock_entries.json", CE)
cm = json.loads((D / "core_macros.json").read_text())
X0, X1, Y0, Y1 = 12.96, 119.88, 51.84, 90.72
for g, mod in ((0, M0), (1, M1)):
    cm["cores"][mod] = {
        "status": "KNOWN", "outline_um": [W, H], "macros": [
            {"name": f"u_fcore.u_grp.g_lane[{k}].u_payload", "master": "ot_sram_1r1w_128x256_m1_r0c0_g256", "orient": "R0",
             "rect_um": [x, y, r3(x + 91.8), r3(y + 27.576)]}
            for k, (x, y) in enumerate(((X0, Y0), (X1, Y0), (X0, Y1), (X1, Y1)))],
        "channel_rule_um": 10.8,
        "basis": "DIE-HBM-82-EP6 d44v part 51: one lane group of ot_wbq_root (2 x 2 in the N part: rows y 51.84 / 90.72 (13.3 channel), columns x 12.96 / 119.88 (15.12 channel, 8.64 W strip for the g_d face); S band 4.32-47.5 for the S/W face registers and the pick; 128x256 one-mask-pin master)"}
(D / "core_macros.json").write_text(json.dumps(cm, indent=1) + "\n")
for item in log:
    print("P51", *item)
