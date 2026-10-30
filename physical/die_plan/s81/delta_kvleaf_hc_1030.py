#!/usr/bin/env python3
"""DIE-S81-36 (post-freeze one-block fix, OWNER 12.20 / COORD 11:14): KV leaf t1/t3/t4/t5 natural hard_cores.

The four KV leaf types carry the full soft leaf band (measured 1.89-1.94M mapped cells, G0C hard_cores ERROR).  Codex
55f98afef5b measured the natural 23-cut (ve_m, ve_s, vn_a, vsw, vs, rxsb, rxsf + 16 hcpost lanes hard; vn_b and vq
soft) at 288060/330365/315654/280220 mapped cells (< 400k).  The 23 children are the same modules at the same
parameters as the 74 ordinary leaf types (ve_m/ve_s LA4 LM5 MUT0, vn_a LA6 LM5, vsw LA4 LM5 LR1, vs XL6 MUT0, hcpl AL6
ML7 MUTANT0 = RTL defaults), so their plan views (lef/pins_file/obs) are reused unchanged.

Per KV type this script copies ONE existing final leaf arrangement (same bus face; best on the generator's leaf
ranking key in the KV type's own buses/ft slots: cores/leaf/search.py faces-away / lanes-behind / reach / station
cycles), keeps only the 23 natural cores under the SAME names as the ordinary leaf types (u_lf.<path>: the KV partition's
mapped source root is u_slice.lf[k].u_lf exactly like a leaf, so bind resolves them by the same rule), carries
their early clock taps and internal_stations (core<->core only), and moves the KV type's remaining 4 soft-child SRAM
sites (vp b0/b1 onto the template's store sites; vn_b h1 / vq xm inside the template's soft vn_b / vq boxes).  The 3
SRAM contents now inside hard views (vn_a h0, vsw la/lb) are dropped.  Outline, buses, ft slots, edge clocks,
landing contract and every other type / partition are unchanged (exact JSON equality asserted).  Step 2: the ft station
centres that now fall inside a new core are slid along their route by the shared minimal-move tool
tools/die_plan/ft_nudge.py (station counts / windows / pins unchanged; only these 4 types' ft_slots regs_um change).
Step 3 (G0C face-rule sidecar): core_conns.json gets the 4 KV types' entries = the template type's entries for the 23
kept cores, renamed, with targets on the soft vn_b / vq dropped (only additions; every existing key unchanged).
Step 2b: landing_contract.collector_tree of the 4 types = their recomputed reset tree (depth unchanged).
Step 2c: the same tree in the clock landing table h2_2249/landed_sidecar_h2.json (collector.types[tn].tree).
usage (repo root): delta_kvleaf_hc_1030.py PLAN_IN PLAN_OUT [REPORT.json [CONNS_IN CONNS_OUT [SIDECAR_IN SIDECAR_OUT]]]"""
import copy
import json
import math
import os
import re
import subprocess
import sys
import tempfile

TEMPLATE = {1: "ot_s81sl_leaf__t21", 3: "ot_s81sl_leaf__t9", 4: "ot_s81sl_leaf__t34", 5: "ot_s81sl_leaf__t35"}
SOFT = ("u_lf.u_vn.u_b", "u_lf.u_vq", "u_lf.u_vp.u_b0", "u_lf.u_vp.u_b1")
DROP_SRAM = ("u_bound.u_u_vn_u_a.u_h0", "u_bound.u_u_vsw.u_l.u_la.g_m[0].u_m", "u_bound.u_u_vsw.u_l.u_lb.g_m[0].u_m")
SRAM_HOME = {"u_bound.u_u_vp_u_b0": "u_lf.u_vp.u_b0", "u_bound.u_u_vp_u_b1": "u_lf.u_vp.u_b1",
             "u_bound.u_u_vn_u_b.u_h1": "u_lf.u_vn.u_b", "u_bound.u_u_vq.g_xr.u_xm": "u_lf.u_vq"}
LAT = 8.64


def flat(inst):
    """core instance name in the KV type = the leaf name unchanged (u_lf.u_vp.g_ln[3].u_l).  A first cut renamed to the
    kit-rtl bound name u_bound.u_u_vp_g_ln_3_u_l: strict bind could not resolve the 16 same-module lanes (wavefront
    core reset, 'expected one bound leaf, found 16'), while the leaf form u_lf.<path> resolves exactly."""
    assert inst.startswith("u_lf."), inst
    return inst


def ren(s, names):
    for a in sorted(names, key=len, reverse=True):
        s = s.replace(a + ".", names[a] + ".").replace(a + "|", names[a] + "|")
        if s == a:
            s = names[a]
        elif s.endswith(":" + a):
            s = s[: -len(a)] + names[a]
    return s


def box(c):
    (x, y), (w, h) = c["origin_um"], c["outline_um"]
    dx, dy = c.get("track_offset_um", [0.0, 0.0])
    return [x + dx, y + dy, x + dx + w, y + dy + h]


def apply_type(K, L, rep):
    K = copy.deepcopy(K)
    keep = [c for c in L["hard_cores"] if c["inst"] not in SOFT]
    assert len(keep) == 23, len(keep)
    names = {c["inst"]: flat(c["inst"]) for c in keep}
    hc = []
    for c in keep:
        e = copy.deepcopy(c)
        e["inst"] = names[c["inst"]]
        e["note"] = ("DIE-S81-36 natural KV-leaf cut: arrangement of %s %s" % (rep["template"], c["inst"])) + \
            ("; " + c["note"] if c.get("note") else "")
        hc.append(e)
    K["hard_cores"] = hc
    # internal stations between hard cores / type face buses only (the soft vn_b / vq ends are placed by GPL)
    soft_pfx = tuple(s + "." for s in SOFT) + SOFT
    ist = []
    for s in L.get("internal_stations", []):
        ends = [s.get("launch", ""), s.get("capture", "")]
        core_ends = [e.split(":", 1)[1] if e.startswith("core:") else e for e in ends]
        if any(e.startswith(soft_pfx) for e in core_ends) or \
                any(not (e.startswith("u_lf.") or e.startswith("face bus ")) for e in core_ends):
            rep.setdefault("istations_dropped", 0)
            rep["istations_dropped"] += 1
            continue
        e = copy.deepcopy(s)
        for k in ("conn", "launch", "capture"):
            if k in e:
                e[k] = "|".join(ren(p, names) for p in e[k].split("|"))
        ist.append(e)
    K["internal_stations"] = ist
    rep["istations"] = len(ist)
    # early core clock taps of the kept cores
    taps = [copy.deepcopy(t) for t in L["clock"].get("taps", []) if t["name"].rsplit(".", 1)[0] in names]
    for t in taps:
        t["name"] = ren(t["name"], names)
    assert len(taps) == len([t for t in L["clock"].get("taps", [])
                             if t["name"].rsplit(".", 1)[0] in names]) and taps, "no core taps"
    ck = dict(K["clock"])
    # keep key order: tap_um, layer, taps, core_taps, then the KV type's own keys
    new_ck = {}
    for k_, v_ in ck.items():
        new_ck[k_] = v_
        if k_ == "layer":
            new_ck["taps"] = taps
            new_ck["core_taps"] = L["clock"]["core_taps"]
    K["clock"] = new_ck
    rep["core_taps"] = len(taps)
    # SRAM contents
    lbox = {c["inst"]: c for c in L["hard_cores"]}
    cont = []
    moved = {}
    for c in K["contents"]:
        if c["inst"] in DROP_SRAM:
            rep.setdefault("sram_dropped_into_views", []).append(c["inst"])
            continue
        if c["inst"] in SRAM_HOME:
            h = lbox[SRAM_HOME[c["inst"]]]
            c = copy.deepcopy(c)
            bx = box(h)
            cw, ch_ = c["outline_um"]
            if h["module"] == c["module"]:          # store SRAM: the template's hard store site (lattice origin)
                x, y = h["origin_um"][0], h["origin_um"][1] + 0.012
            else:                                   # inside the soft child's reserved box, centred, lattice + 0.012
                x = math.floor(round(((bx[0] + bx[2]) / 2 - cw / 2) / LAT, 6)) * LAT
                y = math.floor(round(((bx[1] + bx[3]) / 2 - ch_ / 2) / LAT, 6)) * LAT + 0.012
            c["origin_um"] = [round(x, 4), round(y, 4)]
            c["note"] = "DIE-S81-36 KV-leaf cut: site in %s %s of %s; was %s" % (
                "store" if h["module"] == c["module"] else "soft box", SRAM_HOME[c["inst"]], rep["template"],
                [round(v, 4) for v in K_orig_origin(K, c["inst"])])
            moved[c["inst"]] = c["origin_um"]
        cont.append(c)
    K["contents"] = cont
    rep["sram_moved"] = moved
    return K


_ORIG = {}


def K_orig_origin(K, inst):
    return _ORIG[(K["module"], inst)]


def splice(text, name, obj):
    m = re.search(r'^  "' + re.escape(name) + r'": ', text, re.M)
    assert m, name
    i = m.end()
    _, j = json.JSONDecoder().raw_decode(text, i)
    body = json.dumps(obj, indent=1).replace("\n", "\n  ")
    return text[:i] + body + text[j:]


def main():
    src, dst = sys.argv[1], sys.argv[2]
    text = open(src).read()
    plan = json.loads(text)
    pt = plan["partition_types"]
    expected = copy.deepcopy(plan)
    report = {}
    for k, ln in TEMPLATE.items():
        tn = "ot_s81sl_kv_leaf__t%d" % k
        K, L = pt[tn], pt[ln]
        assert K["outline_um"] == L["outline_um"]
        assert {b["face"] for b in K["buses"]} == {b["face"] for b in L["buses"]}
        assert not K.get("hard_cores") and not K.get("internal_stations")
        for c in K["contents"]:
            if "origin_um" in c:
                _ORIG[(K["module"], c["inst"])] = c["origin_um"]
        rep = dict(template=ln)
        new = apply_type(K, L, rep)
        expected["partition_types"][tn] = new
        text = splice(text, tn, new)
        report[tn] = rep
    # step 2: ft_nudge (shared tool) on the cored plan; take ONLY the 4 types' ft_slots back
    with tempfile.TemporaryDirectory() as td:
        a, b, led = (os.path.join(td, n) for n in ("a.json", "b.json", "ledger.json"))
        open(a, "w").write(text)
        subprocess.run([sys.executable, "tools/die_plan/ft_nudge.py", a, b, led], check=True)
        nudged = json.load(open(b))
        ledger = json.load(open(led))
    for tn in report:
        nt = nudged["partition_types"][tn]
        new = expected["partition_types"][tn]
        assert {k: v for k, v in nt.items() if k != "ft_slots"} == {k: v for k, v in new.items() if k != "ft_slots"}
        new["ft_slots"] = nt["ft_slots"]
        text = splice(text, tn, new)
        report[tn]["ft_nudge"] = [{k: v for k, v in r.items() if k != "regs_um"} for r in ledger if r["type"] == tn]
    assert {tn for tn in nudged["partition_types"] if nudged["partition_types"][tn] != json.loads(
        text)["partition_types"][tn]} == set(), "ft_nudge touched another type"
    # step 2b: the landing collector walks the type's own reset tree, which now routes around the 23 cores (bind
    # 'collector rst_rl_34: raw reset parent rst_rl_27 absent' with the stale copy).  Store the recomputed tree
    # (reset_tree.for_type, as clock_landing_plan does); depth, and the taps the collector sources / children use,
    # must be unchanged.
    sys.path.insert(0, os.path.join("tools", "die_plan"))
    import reset_tree as RT
    import schema as S
    fd, tp = tempfile.mkstemp(suffix=".json", dir=os.path.dirname(os.path.abspath(src)))
    try:
        os.write(fd, text.encode())
        os.close(fd)
        PN = S.Plan(S.load(tp), tp)
        for tn in report:
            new = expected["partition_types"][tn]
            lc = new["clock"]["landing_contract"]
            old_t = lc["collector_tree"]
            T = json.loads(json.dumps(RT.for_type(PN, tn)))
            assert T["depth"] == old_t["depth"] and T["own_depth"] == old_t["own_depth"], tn
            used = {int(c["node"].rsplit("_t", 1)[1]) for c in lc["collector_children"]}
            used |= {s_["tap"] for s_ in lc["collector_local_sources"] if "tap" in s_}
            for i in used:
                assert T["taps"][i] == old_t["taps"][i], (tn, i)
            lc["collector_tree"] = T
            report[tn]["collector_tree"] = dict(relays=[len(old_t["relays"]), len(T["relays"])], depth=T["depth"],
                                                taps=[len(old_t["taps"]), len(T["taps"])], used_taps=sorted(used))
            text = splice(text, tn, new)
    finally:
        os.path.exists(tp) and os.unlink(tp)
    out = json.loads(text)
    assert out == expected, "unexpected plan edit"
    for tn in out["partition_types"]:
        if not tn.startswith("ot_s81sl_kv_leaf__t") or tn.endswith("t2"):
            assert out["partition_types"][tn] == plan["partition_types"][tn], tn
    for k in plan:
        if k != "partition_types":
            assert out[k] == plan[k], k
    open(dst, "w").write(text)
    if len(sys.argv) > 5:
        cin = open(sys.argv[4]).read()
        conns = json.loads(cin)
        soft_pfx = tuple("core:" + x for x in SOFT)
        for k, ln in TEMPLATE.items():
            tn = "ot_s81sl_kv_leaf__t%d" % k
            assert tn not in conns
            names = {c["inst"]: flat(c["inst"]) for c in plan["partition_types"][ln]["hard_cores"]
                     if c["inst"] not in SOFT}
            e = {}
            for core, ports in conns[ln].items():
                if core not in names:
                    continue
                e[names[core]] = {pn: [ren(t_, names) for t_ in tg if not (t_.startswith(soft_pfx))]
                                  for pn, tg in ports.items()}
                e[names[core]] = {pn: tg for pn, tg in e[names[core]].items() if tg}
            conns[tn] = e
            report[tn]["core_conns_cores"] = len(e)
        cout = json.dumps(conns, indent=0)
        assert json.loads(cout) == dict(json.loads(cin), **{t_: conns[t_] for t_ in conns if t_ not in json.loads(cin)})
        open(sys.argv[5], "w").write(cout)
    if len(sys.argv) > 7:
        # step 2c: the bind reads the collector from the clock landing table (manifest clock_landing_table =
        # h2_2249/landed_sidecar_h2.json), not from the plan copy: same recomputed tree there, nothing else changed
        sin = json.loads(open(sys.argv[6]).read())
        sout = copy.deepcopy(sin)
        for tn in report:
            ct = sout["collector"]["types"][tn]
            assert json.loads(json.dumps(ct["tree"])) == plan["partition_types"][tn]["clock"]["landing_contract"][
                "collector_tree"], tn
            ct["tree"] = out["partition_types"][tn]["clock"]["landing_contract"]["collector_tree"]
        open(sys.argv[7], "w").write(json.dumps(sout, separators=(",", ":")) + "\n")
    if len(sys.argv) > 3:
        json.dump(report, open(sys.argv[3], "w"), indent=1)
    print(json.dumps(report, indent=1)[:3000])


if __name__ == "__main__":
    main()
