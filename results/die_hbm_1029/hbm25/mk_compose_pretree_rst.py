#!/usr/bin/env python3
"""DIE-HBM-25 HBM-046 (A): the 8 SU pretree compose cuts expose their one reset terminal as `rst_n` (kit/plan pin name).

The Codex native compose named every SU pretree cut port with the member prefix (pretree_rst_n); its only terminal is
su_*.u_slice.g_pretree.u_pt.rst_n (the source pretree reset), i.e. the plan hard core u_su_Q<q>_pretree pin rst_n.
Rename that one port (nothing tied, no terminal moved; module renamed because the cut interface changes).  Fail-closed.
usage: mk_compose_pretree_rst.py COMPOSE_IN COMPOSE_OUT REPORT"""
import json, sys
src, dst, repf = sys.argv[1:4]
C = json.load(open(src))
OLD = "ot_hnx_su_pretree__40a88add71d7"; NEW = "ot_hnx_su_pretree__rst"
rep = dict(changed=[], rename={OLD: NEW}, port="pretree_rst_n -> rst_n")
for core in C["cores"]:
    if core["module"] != OLD:
        assert not core["inst"].endswith(".__cut_pretree"), core["inst"]
        continue
    P = core["ports"]
    assert "rst_n" not in P and [n for n in P if "rst" in n] == ["pretree_rst_n"], core["inst"]
    p = P["pretree_rst_n"]
    assert p["dir"] == "input" and len(p["bits"]) == 1 and len(p["bits"][0]) == 1, core["inst"]
    a = p["bits"][0][0]
    assert a["member"] == core["inst"].rsplit(".", 1)[0] + ".u_slice.g_pretree.u_pt" and a["port"] == "rst_n" and a["bit"] == 0, a
    core["ports"] = {("rst_n" if k == "pretree_rst_n" else k): v for k, v in P.items()}
    core["module"] = NEW
    rep["changed"].append(dict(inst=core["inst"], terminal=a))
assert len(rep["changed"]) == 8, len(rep["changed"])
json.dump(C, open(dst, "w"))
rep["n_changed"] = len(rep["changed"])
json.dump(rep, open(repf, "w"), indent=1)
print("changed", rep["n_changed"])
