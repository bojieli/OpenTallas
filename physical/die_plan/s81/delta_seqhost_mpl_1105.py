#!/usr/bin/env python3
"""S81 seqhost__t1 MPL-0020 fix (DIE-S81-66/PLAN 11-05, COORD 19:37 (f) plan holes): place_macro stopped with
'[ERROR MPL-0020] Couldn't find a macro named ...' because one plan macro path is not the netlist name.  In
ot_dsdv_host_afifo_sram (OT_S81_SH_RSZ) the 16x289 master sits in 'end else if (W==289) begin:g_rsz1'; the kit's
Yosys (openroad/orfs:asap7lock read_verilog) scopes that else-if branch as an unnamed block genblk2, so the flattened
instance is u_ox.genblk2.g_rsz1.u_mem, not u_ox.g_rsz1.u_mem.  Measured: yosys elaboration of the seqhost__t1 kit RTL
(bind die-s81-59/ev/bind, kit_rtl_s81p.sh, kit defines) lists 10 ot_sram_* cells; 9 match the plan paths, this one
does not.  Same convention as the svc_lo types (u_iq.genblk2...u_mem); kit_contract._resolve accepts genblkN.
Inst rename only: no site, outline, pin, clock, reset or define change.
usage: delta_seqhost_mpl_1105.py PLAN_IN PLAN_OUT"""
import json, sys

TYPE = "seqhost__t1"
OLD = "u_bound.u_u_seqhost.u.u_u.u_l0.u_h.host.u_hi.g_ox_sram.u_ox.g_rsz1.u_mem"
NEW = "u_bound.u_u_seqhost.u.u_u.u_l0.u_h.host.u_hi.g_ox_sram.u_ox.genblk2.g_rsz1.u_mem"
MODULE = "ot_sram_1r1w2c_16x289_m1_p192"
NOTE = "; inst ...u_ox.genblk2.g_rsz1.u_mem = Yosys name of the else-if branch (DIE-S81-66 11-05 MPL-0020 fix)"


def main():
    src, dst = sys.argv[1:3]
    p = json.load(open(src))
    t = p["partition_types"][TYPE]
    hit = [c for c in t["contents"] if c["inst"] == OLD]
    assert len(hit) == 1 and hit[0]["module"] == MODULE, [c["inst"] for c in t["contents"]]
    assert not any(c["inst"] == NEW for c in t["contents"]), "second run?"
    hit[0]["inst"] = NEW
    hit[0]["note"] = hit[0].get("note", "") + NOTE
    left = [n for n, q in p["partition_types"].items() for c in q.get("contents", []) + q.get("hard_cores", [])
            if c["inst"] == OLD]
    assert not left, left
    text = open(src).read()                 # one row, spliced in place (compact single-line row form)
    row_old = '"inst":"%s","module":"%s"' % (OLD, MODULE)
    assert text.count(row_old) == 1, text.count(row_old)
    i = text.index(row_old)
    k = text.index('"note":"', i) + len('"note":"')
    e = text.index('"}', k)
    assert text[k:e] == hit[0]["note"][:-len(NOTE)], text[k:e]
    text = text[:i] + row_old.replace(OLD, NEW) + text[i + len(row_old):k] + text[k:e] + NOTE + text[e:]
    assert json.loads(text) == p
    open(dst, "w").write(text)
    print(json.dumps({"type": TYPE, "from": OLD, "to": NEW}))


if __name__ == "__main__":
    main()
