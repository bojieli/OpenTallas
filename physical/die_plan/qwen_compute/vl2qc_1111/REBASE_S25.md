# VISLAYOUT2-QC rebase onto s25 (plan_qc99_s25 e4820bd9d97c), 2026-11-12

make_colln.py (c 95.04 112.32 112.32 328.32) then make_stm.py (stm_blocks.json) applied to s25 give
plan_vl2_s25_d sha256 13c8363feb3f. The edits are identical to the s22 deltas (delta_colln_c / delta_stm_d,
only base/plan sha differ): s25 did not change coll_n or any stm type.

Gates on s25 tools (src_qc_s25_4e2764d237 copy): schema PASS; G0 errors 265 -> 265 (same set), warnings
305 -> 314 (+9 advisory core_faces: stm m1 rd_out faces E/W, the 2x2 MX block; the placed build had GRT 0
overflow); station_lint 3 NONMONOTONE advisory on both.
route_supply p99 (--grt-halving edge_outline, s25 tools): stm family 1.02-1.34 -> 0.62-0.84; coll_n 0.40 -> 0.51.

sl_hc2 (delta_hc2_e) is NOT carried here: s26 carries the DIE-QC-97/98 hc1/hc2 strip-rows form on the same
b_hw_i band. The private slw_hc2__cl6bcaba89 build (band to 103.68) is its comparison arm.

posguard.py: after kit gen, proves plan hard-core origin+orient, count-strap sites, GRT mode/image and flow tag
in the kit (COORD 23:26 R1 guard).
