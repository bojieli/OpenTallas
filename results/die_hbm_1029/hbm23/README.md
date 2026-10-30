# DIE-HBM-23 (HBM die owner, 2026-10-29 17:47- PDT)

## HBM-040 (A) -- COORD 17:44 ruling: plan follows source, 8-SM release
`vmdel_s_drop.py` on d22b (c564e8942374, intel1 hbm-bind-9-1029/plan/d22b) -> **d23a die_plan 4133ce1e4e0d**
(intel1:/srv/opentallas-scratch2/claude/die-hbm-23/plan/d23a). Removed from q_hub_ne and q_hub_nw each: 8 hard cores
u_vmdel_Q0..7__q0 (S-role copies from the 16-SM d4g die), 8 contents (79,928 cells per hub), 8 clock taps; 0 stations /
buses / pins referred to them (script fails closed otherwise; whole-plan string check). N-role u_vmdel_Q0..7 stay. South VM
bank dq stay open native_required inputs (nothing tied). Report hbm040/vmdel_s_drop_report.json.

| check | result (CHECKED) |
|---|---|
| G0 d23a | PASS, 0 errors |
| G0C d23a | FAIL 8 = the 8 inherited d22b errors, 0 new, 0 gone |
| strict bind b2 (HBM-BIND-7 c1 manifest/netlist unchanged, tools = hub main 92f899057c3, 2:49 min, 7.2 GB) | 93 errors = the same 92 UNPLANNED (82,285 b) + 1 EMIT; **HBM-040 cleared** (no u_vmdel_Q*__q0 EMIT) |
| next masked EMIT (HBM-041) | `glue cell hc_NE.u_cen.$div$ot_hbm_hc_qcen_static.sv:85$54922 type $div (in a dissolved parent) is not supported: map that parent whole` |

Reproduce: `vmdel_s_drop.py hbm-bind-9-1029/plan/d22b die-hbm-23/plan/d23a`; `tools/die_plan/check.py plan/d23a/die_plan.json [--completeness]`;
`hbm040/run_bind.sh b2 plan/d23a/die_plan.json` (b2/asbuilt.json + b2/out/asbuilt.json = copies of hbm-bind-9-1029/b1).

## xcal / bdring face-flop clock arrival (sub-lane HBM-XCLK-23, read-only probes; brief item 3) -> recipe for HBM-CORES-KITS-22
Probes on epyc2 hbm-cores-kits-21/xcal/xcal_k21m5 4_cts.odb (TT/FF, placement RC) and bdring_k20vb 4_cts + signoff.json;
data/scripts epyc2:/srv/opentallas-scratch2/claude/hbm-xclk-23 (copies of scripts + renders in xclk/; xcal_clk.png VIEWED).
- xcal: NOT an entry-siting problem (CHECKED): clk entry (125.30,125.28) M5 = core_infra_plan clock_entry, central in the
  241.9x224.6 core; tree to level 6 lands 142-176 ps TT (34 ps spread, 6 BUFx24 stages). The spread is the LAST stage:
  leaf arrival ~ 202 + 0.64 ps/um x distance from its level-6 driver (r 0.75; vs entry distance r 0.54). Macro program_lo
  (y 142-213, x 34-208) leaves no level-6 driver above y~140, so NW/NE channel-end flops hang off drivers at (48,134) and
  (208,133) with leaf nets up to 131 um, fanout 10-19, slew to 199 ps; E side + repair buffer wire3843 (fo 12) = 7th stage
  for 63 E-face flops. Face TT insertion W p50 259/max 293, E 275/302, S 235/270; rst_q single N-face flop (120,220).
- Hold relation (CHECKED from KITS-21 probe numbers): input-face hold slack ~ 150.9 - FF insertion; rst_q removal ~
  138.5 - FF insertion -> even a balanced tree at 202.5 FF leaves ~-52 ps = IO contract (min input delay -40, hold unc 12.5),
  i.e. OT_IO_HOLD_PAD territory; the tree adds ~-47 (W faces) / -68 (rst_q) on top.
- bdring_k20vb: different class (CHECKED): 4_cts tree balanced 241-266 ps, slope vs entry 0.04 ps/um; tap_balance added
  2 BUFx4 delay cells (placement RC) lifting mean 196->253; routed mean 288 / max 318 (+35) -> offset FAIL; routed-basis
  balance (or no delay cells) -> ~231 routed (UNCHECKED).
- Recipe (estimate UNCHECKED: TT ~205-240, FF ~170-200, input-face hold -20..-50 = pad range): xcal kit
  core_infra_plan.json core_tree (now null) per the qkd_hr_phy_pad.json precedent: clock_port clk, BUFx24 trunk from the
  entry, stage_basis total, 6 region roots in the channels W-N (16,170) ~650 sinks, W-S (16,60) ~870, E-N (225,165) ~280,
  E-S (225,60) ~130, centre-N (125,137) ~700, centre (123,100) ~470; cts_stages 3 on every leaf; equal_load false +
  load_balance joint_nldm_plan; move rst_n pin + rst_q flop next to the W-N/centre root via the plan pin entry. Entry move
  to the face-flop centroid gains nothing. No die-specific clock script; ot_clk leaf_drivers/local_entry act on die
  provider netlists, not kits.

## EP_S1 re-station at the 405-um rule (sub-lane HBM-EPS1-23, estimate only; plan d22b) -- notes eps1/RESULT.txt
- Why B2o has 167-um pitch (CHECKED): tool side effect, not timing - B2o b2n.restation (cores_b2.RelayRouter, 360-um
  hop limit) places stations only on hard-core edges / partition perimeter; vsN1/vsN2 are empty pass-throughs, so the
  chain detoured via the W edge (2747 / 2574 um, 9 + 8 stations); the later per-bit step kept the counts on the straight
  1503/1331-um route.
- Recount (CHECKED from plan geometry, per-partition R3 route/stations <= 405): vsN1 4 (375.84 pitch), vsN2 4 (332.64)
  -> 17 -> 8 stations, 19 -> 10 cycles each way for L200/L201 and L118/L141 (same word, keep equal).
- 405-um hop closure: 261 ps + 1.135 ps/um x L (W15 routed fit, SS) with droop derate -> 769.8 ps at 405 um (UNCHECKED
  source figures, arithmetic CHECKED).
- Price (ESTIMATE, linear between TOK-HBM-11 CHECKED points 17 cyc 1.531 % / 34 cyc 3.195 %): EP_S1 3.195 % -> ~1.44-1.50 %;
  total 5.163 % -> ~3.41-3.48 % -> ~1842 tok/s (from ~1812): recovery ~1.7 % >= 1 % -> OWNER? line re-priced.
- Plan delta (not built): vsN1 slots L118x1/L141x1/L201x1 (S->N) + L200x2 (N->S) 9 -> 4 stations at y 0/375.84/751.68/
  1127.52 (L200 mirrored from 1503.36); vsN2 L118x2/L141x2/L201x2 + L200x1 8 -> 4 at y 0/332.64/665.28/997.92; x kept;
  regenerate L118/L141 per-bit sites; latency L118/L141/L200/L201 = 10 cycles / 8 stations; G0/G0C.
