# QC-SUC-FTSITE handoff (owner lane from QC-ALLFIX, started 11-24 15:04 PST)
Job: slw_su_c x2 (cl92142dac, cl19bb38ef) gen fail "FT bit sites cws1,0,117 and cws1,0,118 snap to one site" on C1i/C1j/C1k.
CAUSE: SU2R row su2r.py (epyc7 QC-ALLFIX-SU/rows/su2r) fy() maps y 880..1100 into 1031.2..1100 (x0.313) on every point incl.
ft_slots bit_sites_um -> cws1/cws2 stage-0 columns at 0.084 um pitch. slw_su_c x2 also have x_su_l1_ctl per-bit rows stepping
0.054 um in x in one row. Census C1k (footprint 1.404x0.27): gen-fatal sle_su_c (522 bits), slw_su_c x2 (3845 bits each).
Footprint-only, gen OK, NOT changed: sle_sc_v1 cl7479a5ec / v2 / v3 (x_su_l1_ctl s5, 188 at 1.08 pitch), slw_fe_v2 clf110fab2 (130 ft vs ist).
FIX: main b2003c8a083 ft_bit_sites.footprint_conflicts/legalize_slots + tools/die_plan/ft_site_legalize.py (census / rewrite; test).
OVERLAY for C1l: epyc2 + epyc11 /srv/opentallas-scratch2/claude/QC-SUC-FTSITE/rows/plan_c1k_ftsite.json 23a0e06ca00c = C1k 7fbc73d3f7cf
  + 3 su_c types ft_slots bit_sites_um + note only (ledger ftsite_ledger.json a35baeed87a5; max move 5.13 um). Re-run tool on C1l:
  ft_site_legalize.py PLAN OUT LEDGER --types sle_su_c slw_su_c__cl19bb38ef slw_su_c__cl92142dac
PILOT: epyc11 /srv/opentallas-scratch2/claude/QC-SUC-FTSITE/forkbind.sh (fork cK -> cKf, overlay, G0, PRE, scoped strict bind 3 su_c, LATCHECK).
