# S81-RTLGAP/RG-IDX (10-21): TOK.DS.BENCH.4.4 L2 index reader transport on the 72-frame die

Base: G3 die RTL claude/s81-die72-g3-1021@4ee613834 (die.v of the G3 run, ep7
/srv/opentallas-scratch/claude/claude-s81-die72-g3-1021/die72-g3/bind/bind/die.v).
Branch claude/s81-rtlgap-idx-1021.

## What the G3 die already binds (transport inventory, plan_routed_g3.json)
| lane | bits (RTL) | stations | length |
|---|---|---|---|
| iq_src_l0/l1  s_3S iq -> iqf qs | 276 + 237 | 45 / 45 | 16.1 mm |
| iq_qf_l0/l1   iqf qr -> irg_00 qi | 276 + 237 | 35 / 36 | 12.5 mm |
| iq/is chain irg_p -> irg_p+1 | 513 + 276 | 0 (iq_03_04 0/1, is_03_04 1) | 86-453 um |
| is_tail       irg_07 so -> bk_sel vi_idx | 276 | 41 | 14.5 mm |
| hrrq_k        irg_{k/2} rqo -> ctrl_k rrq | 92 | 70-74 | 24.6-26.1 mm |
| hrrd_k        ctrl_k rrd -> irg_{k/2} rri | 544 | 71-74 | 25.0-26.1 mm |
| hrq/hrd_k     rsv_k <-> ctrl_k (svc, unchanged) | 682 / 562 | 4 | 1.6 mm |
Every lane: forwarded-clock relay stations + fixed-latency landing (ot_s81_land D 4) at the receiver, no
credit/ready; bk_sel ingress = dsdv_bk_sel_vm (dsdv_idx_vmux OR-merge, 2 edges).  Reader RTL bound: the native-fixed
dsdv_idx_rg3 (S81-IDXRD 21cb18cad, same ports, 0 added cycles) -- commit dfcd6fd21.  No CLOSED reader / qf / ctrl_rg3
view exists yet, so the die binds RTL (ctrl_rg3 routes s81ctrl_rg3/rg3s pending).

## Defect A (functional, die binding): reader + qf reset polarity inverted
recovery_idx4_1021/overlay.json binds dsdv_idx_rg3 (+ chain-end dsdv_idx_rg3_nq) and dsdv_idx_qf with rst
["rst","high"]; dv_bind therefore inserts INVx2 rinv_irg_00..07 / rinv_iqf between the active-LOW reset-station net
rs_* and `.rst`.  The RTL rst of both is active-LOW (`negedge rst ... if (!rst)`).  In G3 die.v the 8 readers and the qf
node are held in reset whenever the die runs.  Fix (G4): tools/s81_dv/rtlgap_idx_1021/apply_rst_fix.py after
apply_overlay.py (rst -> ["rst","low"]: the 9 inverters disappear).  Bench: variant asis_tt (die.v verbatim) vs
rstfix_tt (the 9 INVx2 -> BUF, = the fixed bind).

## Defect B (structural): readers 25 mm from their HBM controllers
G3 places irg_00..07 on the north edge (y 23490) while ctrl_00..15 sit on the south PHY row (y 1393): 32 lanes of
24.6-26.1 mm, 70-74 stations each = ~10.2 kb x 25.8 mm ~ 262 kbit-mm and ~0.74 M relay flops, for a function the DIE11
spec placed beside the PHY (s = 3..18).  Static costs (all fixed, compiler-scheduled):
- HBM round trip per reader read +2s+5 = ~151 edges (spec 11..41); the reader run-ahead T0 floor rises by the same.
- reader budget loop (issue -> pop seen) 2s+7 = ~155 edges: DQR 24 sustains 24/155 = 0.155 requests/edge/PC (spec
  0.56 at s 18) -- below the pcr take (0.5/edge), so the scan / gather rate may become lane-bound.
The bench below measures it (record cases at the record T0 / P, plus T0 sweeps).
Transport design options for G4 (LEAD-S81-G3 owns the plan; G3 vertical stack is full: PHY+ctrl 1717 + 2 svc rows
7690 + 2 slice rows 13565 + top row 1469 = 25200; +1296 for a reader row exceeds the 26 mm reticle):
1. Pocket placement (recommended first step): the two south pockets beside the PHY (W x 8826-11901, E x 20401-23476,
   y 86-1717) hold 2 readers each: pairs 0,1 (ctrl_00-03) W and pairs 6,7 (ctrl_12-15) E -> s ~3-8 for half the lanes,
   ~131 kbit-mm and ~0.37 M relay flops removed.  Pairs 2-5 stay north (or take the freed link_0_4/1_4 reserve columns
   if the owner drops the 5th lane pair: W/E pocket 3594 wide = 3 readers each).
2. For readers that stay far: raise the reader budget to cover the loop: DQR = ctrl RFD >= 0.5 x (2s+7) + margin = 80
   (ctrl landing FIFO 80 x 44 b = 3.5 kb a PC -> SRAM macro, rule 5; re-kit dsfd_ctrl_rg3).  Only if the bench shows
   the record rates lane-bound.
3. Query side unchanged: iq_src (16 mm) + iq_qf (12.5 mm) are one 513-b lane once per job (+~85 edges, static, hidden
   by T0); placing iqf beside s_3S would cut ~12 mm x 513 b if the readers stay north.
Schedule: every offset above is fixed latency; S81-CAL / lower_bk prices the T0 floor (+2s_max+5) and the svc calendar
rule (no svc request on a pair's PCs inside its reader window) at the G4 station counts.

## Bench (existing reader bench on the die netlist)
mk_tb72.py generates tb_idx72.sv from the record tb_dsdv_idx_rg3.sv (same HBM model, reference engine, V-ingress decode,
slice traffic, slot-hit check, plusargs); the DUT is idx72_top = dv_slice_cut.py cut of G3 die.v (u_iqf, u_irg_00..07,
u_ctrl_00..15 + 6,397 relay/landing/clock/reset instances, 1,183 ports).  Lane flight: synthetic land plan inside each
landing window (tt = window top K-1, ff = bottom; output must not depend on it).  run_idx72.sh = idxrd3_campaign rules.
Variants: rstfix_tt (record b3 cases + T0 sweep), rstfix_ff (subset), asis_tt (die.v verbatim; expected FAIL = defect
A witness), m1_tt (reader MUT 1 on all 8 readers; expected FAIL).  Results: receipts/ (fleet ep7
/srv/opentallas-scratch/claude/s81-rtlgap-idx-1021/out).
