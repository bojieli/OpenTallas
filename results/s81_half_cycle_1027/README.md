# H0 half-cycle input timing API, narrow candidate

Based on main00d9d370a4. This package changes only optional half-cycle DATA input timing, H0 recipe/spec, and focused tests. It excludes the broad9af commit's multi_master and all other core recipes/RTL.

Actual producer chain: dsdv_eng_rr_split.sv E u_lkp uses .ck(ck); dsfd_engram_lkp_ra640_hx.sv wrapper maps .clk(ck) to its core, whose `always @(negedge clk) win_n <= ids` drives `assign hx_w = win_n`; H0 first capture is `always @(posedge ck) w_q <= in_w`. Both use the same declared die clock, so this is FALL→RISE. No RTL change or new cycle. The original H0 capture added10-24 remains unchanged.

The timing API applies max(1-IO_BUDGET)*T and minT/2-tol ONLY to selected real DATA input buses. Explicit guards reject clock/reset/output/unknown/duplicate selections. With T833/tol20, in_w max666.4/min396.5. Default absent selection is byte-identical at SDC emission;7focused controls pass.

The smallest source-excerpt seam vehicle compares old monolithic negedge→posedge capture with separated actual producer/capture statements: PASS1997edge comparisons at833ps. Posedge-producer mutant fails3994data/phase checks. This establishes RTL phase/edge composition, not extracted physical minimum delay. Actual producer output timing and IO-HOLD parent receipt remain required; no signoff or parent waiver is claimed. H0 additional physical build remains held pending root review.
