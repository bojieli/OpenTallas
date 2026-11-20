#!/usr/bin/env python3
"""svc_h_netlist.py -- S81-SVC-H8W 11-20: the die netlist's service-slice GATHER lanes at the plan's H.

    svc_h_netlist.py --h {8,16} IN_NETLIST.v OUT_NETLIST.v [--report OUT.json]

The adopt178 die netlist (die_b178*.v) carries the 25 gather hops between the 16 service slices u_rsv_NN as
w_sg_<a>_<b>_{src,dst,lnd} [2132:0] = {gather data [2131:0] (H16 lane, 16*132+20), valid}, landed by
dsdv_svc_busland_2133 ld_sg_<a>_<b>, and bound to the slice faces as .g{i,o}_v_<f>(w[0:0]) / .g{i,o}_d_<f>(w[2132:1]).
The gather lane is H*132+20 b (dsdv_svc_rs_c, dsdv_svc_rs_fv): at H 8 it is 1,076 b, so the H8 form needs the H8
lane on the die too (S81-DIE-R3 J3 r7: with the H16 nets the bind truncated / tied 26,540 live gather bits).

Every edit is an exact, counted replacement on the w_sg nets only (refuses on any count other than the expected
25 nets / 25 landings / 50 slice faces in and out, and on any w_sg reference it does not rewrite).  --h 16 on an H16 netlist
is the identity (and is checked as such).  Output is written by unlink + write (never through a link into a shared
tree).  tools/die_plan/svc_width_gate.py --netlist checks the result against the slice / landing masters.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

H16_GW = 16 * 132 + 20


def gw(h):
    return h * 132 + 20


def transform(text, h, expect_nets=None):
    src_gw = None
    m = re.search(r"wire \[(\d+):0\] w_sg_\d+_\d+_src\b", text)
    if not m:
        raise SystemExit("no w_sg gather nets in the netlist")
    src_gw = int(m.group(1))            # = GW (lane) : the net is GW+1 wide
    new = gw(h)
    rep = dict(decl2=0, decl1=0, land=0, face=0)
    def r_decl2(mm):
        rep["decl2"] += 1
        return f"wire [{new}:0] {mm.group(1)}_src, {mm.group(1)}_dst;"
    text = re.sub(rf"wire \[{src_gw}:0\] (w_sg_\d+_\d+)_src, \1_dst;", r_decl2, text)
    def r_decl1(mm):
        rep["decl1"] += 1
        return f"wire [{new}:0] {mm.group(1)}_lnd;"
    text = re.sub(rf"wire \[{src_gw}:0\] (w_sg_\d+_\d+)_lnd;", r_decl1, text)
    def r_land(mm):
        rep["land"] += 1
        return f"dsdv_svc_busland_{new + 1} {mm.group(1)}"
    text = re.sub(rf"dsdv_svc_busland_{src_gw + 1} (ld_sg_\d+_\d+)\b", r_land, text)
    def r_face(mm):
        rep["face"] += 1
        return f".{mm.group(1)}({mm.group(2)}[{new}:1])"
    text = re.sub(rf"\.(g[io]_d_[nesw])\((w_sg_\d+_\d+_(?:src|lnd))\[{src_gw}:1\]\)", r_face, text)
    n = rep["decl2"]
    if not n or rep["decl1"] != n or rep["land"] != n or rep["face"] != 2 * n or (expect_nets and n != expect_nets):
        raise SystemExit(f"unexpected counts {rep} (nets {n})")
    left = [x for x in re.findall(r"w_sg_\d+_\d+_\w+\[(\d+)(?::\d+)?\]", text) if int(x) > new]
    if left:
        raise SystemExit(f"w_sg references above the H{h} lane remain: {len(left)}")
    return text, dict(rep, nets=n, from_lane=src_gw, to_lane=new, h=h)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--h", type=int, required=True, choices=(8, 16))
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("--report")
    ap.add_argument("--nets", type=int, default=25)
    a = ap.parse_args(argv)
    t = Path(a.inp).read_text()
    o, rep = transform(t, a.h, a.nets)
    if a.h == 16 and rep["from_lane"] == H16_GW and o != t:
        raise SystemExit("H16 on an H16 netlist must be the identity")
    out = Path(a.out)
    if out.is_symlink() or out.exists():
        out.unlink()
    out.write_text(o)
    rep.update(inp=a.inp, out=a.out, sha_in=hashlib.sha256(t.encode()).hexdigest()[:12],
               sha_out=hashlib.sha256(o.encode()).hexdigest()[:12])
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print("SVC_H_NETLIST", json.dumps(rep))
    return 0


if __name__ == "__main__":
    sys.exit(main())
