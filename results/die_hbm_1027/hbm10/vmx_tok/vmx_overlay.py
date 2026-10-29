#!/usr/bin/env python3
"""VMX-TOK-1 2026-10-28: put the DIE-HBM-10 one-owner VM crossing-read link (hfd_vms_xread_link, claude/die-hbm-10-vmx-1028
@85d9228769) into a copy of the r18h5 land-direct SW slice bundle (TOK-HBM vehicle of record: die.v 5b10bf72, slice.v
4ccac9ee, TB 38766c45).

  vmx_overlay.py BUNDLE_COPY --half 0|1 --lx-stream N --link-src hfd_vms_xread_link.sv

What it changes (only in BUNDLE_COPY):
  * rtl/hbm_accel/die_glue/scoped_d4g/pgslice.sv, module ot_hbm_su_static_pgslice_lg: new parameter XREAD_LX (default 0 =
    the record structure: s_rr straight into the slice).  XREAD_LX > 0: the bank-pair response the LG tap delivers to the
    SU slice (local_rr, 2 x 257 b {v, data256}) streams over hfd_vms_xread_link #(LANES 2, LX XREAD_LX) on pg_clk (the
    stream VM-leaf clock), and the slice's own return contract is READ_RETURN + XREAD_LX (its fixed-edge capture
    calendar and rcal check move with it).  The LG tap (bank <-> tap round trip, lg_read/lg_write calendar, SFU far
    path) keeps READ_RETURN: only the SU client's read crosses.
  * slice/slice.v: the two SU port-group slices of the FAR half get .XREAD_LX(N): half 0 -> su_SW2, su_SW3 (VM ports 4-7),
    half 1 -> su_SW0, su_SW1 (ports 0-3)  (Placement.far(p) = p // 4 != half; slice G owns banks 2G, 2G+1).
  * master_files.json: the link source joins ot_hbm_su_static_pgslice_lg's file list (flatten_masters namespace).
"""
import argparse, json, re, shutil
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("bundle", type=Path)
ap.add_argument("--half", type=int, choices=(0, 1), required=True)
ap.add_argument("--lx-stream", type=int, required=True)
ap.add_argument("--link-src", type=Path, required=True)
a = ap.parse_args()
B = a.bundle
# 1. pgslice_lg
p = B / "rtl/hbm_accel/die_glue/scoped_d4g/pgslice.sv"
s = p.read_text()
i0 = s.index("module ot_hbm_su_static_pgslice_lg #(")
i1 = s.index("endmodule", i0)
m = s[i0:i1]
old_par = " parameter integer PRETREE=0\n)("
assert m.count(old_par) == 1
m = m.replace(old_par, " parameter integer PRETREE=0,\n parameter integer XREAD_LX=0   // VMX-TOK-1: one-owner VM crossing-read link depth (stream edges) on the SU read return; 0 = none\n)(")
old_w = " wire [33:0] s_rq; wire [561:0] s_wq; wire [513:0] s_rr; wire [1:0] s_done;\n"
assert m.count(old_w) == 1
m = m.replace(old_w, old_w +
    " wire [513:0] s_rr_slice;   // VMX-TOK-1: what the SU slice sees of its bank pair's read return\n"
    " if (XREAD_LX > 0) begin : g_xread\n"
    "  hfd_vms_xread_link #(.LANES(2), .LX(XREAD_LX)) u_xread(.clk_stage({XREAD_LX{pg_clk}}), .rst_n(rst_n), .rr_owner(s_rr), .rr_far(s_rr_slice));\n"
    " end else begin : g_noxread\n"
    "  assign s_rr_slice = s_rr;\n"
    " end\n")
old_rr = ".READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.FETCH_EXTRA_EDGES(FETCH_EXTRA_EDGES)"
assert m.count(old_rr) == 1
m = m.replace(old_rr, ".READ_RETURN(READ_RETURN+XREAD_LX),.WRITE_RETURN(WRITE_RETURN),.FETCH_EXTRA_EDGES(FETCH_EXTRA_EDGES)")
assert m.count("  .lg_rr(s_rr),\n") == 1
m = m.replace("  .lg_rr(s_rr),\n", "  .lg_rr(s_rr_slice),\n")
p.write_text(s[:i0] + m + s[i1:])
# 2. link source
dst = B / "rtl/hbm_accel/generic/vm/static/xread/hfd_vms_xread_link.sv"
dst.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(a.link_src, dst)
mf = json.loads((B / "master_files.json").read_text())
fl = mf["ot_hbm_su_static_pgslice_lg"]
rel = str(dst.relative_to(B))
if rel not in fl:
    fl.append(rel)
(B / "master_files.json").write_text(json.dumps(mf, indent=1) + "\n")
# 3. slice.v far-half SU port-group slices
far = (2, 3) if a.half == 0 else (0, 1)
v = (B / "slice/slice.v").read_text()
for g in far:
    pat = re.compile(r"(ot_hbm_su_static_pgslice_lg #\([^\n]*\.PRETREE\(1\))(\) su_SW%d \()" % g)
    v, n = pat.subn(r"\1, .XREAD_LX(%d)\2" % a.lx_stream, v)
    assert n == 1, (g, n)
(B / "slice/slice.v").write_text(v)
print(f"VMX_OVERLAY half={a.half} far_slices={['su_SW%d' % g for g in far]} XREAD_LX={a.lx_stream} stream edges")
