# DIE-HBM-20-EPA (2026-10-29): hfd_ep_static variant (a) = tx/rx core split (COORD 13:38 plan-change ruling)

Probe runs epyc2:/srv/opentallas-scratch2/claude/die-hbm-20/epA/{eq,tx,tx2,tx3,rx1,rx2,rx3,review}. Opt-in, die-local; the
existing hfd_ep_static.sv / kits / plan of record are untouched. Probes = synth + floorplan + place in openroad/orfs:asap7lock
from a copy of the HBM-CORES-KITS-18 ep_my kit, then tools/autopilot/geom_check.sh (AUTO-GEOM, GRT M2-M5 adj 0.25, 50 it).
Probe deviations from a real kit: master-plan slice / island clock+reset infra STUBBED (so clock_reach is not comparable
to a kit), no CTS/route/sign-off, pins placed by mk_kits.py (not the plan pins file).

## 1. Root cause (estimate, CHECKED from the LEF + ep_my kit)
SRAM ot_sram_1r1w_64x512_m1_r2c2 = 171.288 x 77.784, OBS M1-M4, M4 pins on BOTH edges: x=0 side rd_out 512 + wd_in[265:0]
+ clk/ce/addr (= the side each leaf really uses: W=306 of 512 bits), x=171 side wd_in 246 + w_mask 512 + repair (ties /
40 used wd bits). Kit max layer M5 (V) -> nothing crosses a macro horizontally. ep_my: 4 SRAMs in one MY column at
x 35.3 leave two ~31-um strips; TX gearbox (W face pins) in the W strip, RX + the SRAM main pin side in the E strip
-> GRT 255,546.

## 2. Split RTL (rtl/hfd_ep_static_split.sv; rtl/ot_hep_gbx.sv = lines 1-156 of the kit hfd_ep_static.sv, byte copy)
- hfd_ep_static_tx: clk, rst_n, tx_v, tx_frame[611:0] -> sd_tx[511:0], tx_cal_fault (own 2-flop rst sync -> rn_tx; p_tx regs;
  ot_hep_tx_gbx unchanged); face-shell regs on every pin (as face_shell.py).
- hfd_ep_static_rx: everything else (own 2-flop rst sync -> rn_rx/rn_bd/rn_o; ot_hep_rx_gbx + ot_hep_rx_pingpong with the
  4 SRAMs unchanged; status regs), input tx_cal_fault (face-registered).
- Parent: two wires (tx_cal_fault), no logic. Cost: fault_cause[9] (cal_fault) and its term in `fault` arrive +2 edges
  (tx out face reg + rx in face reg); every other output bit cycle-identical. cal_fault is sticky status -> no data/token cost.
- Synth area (CHECKED synth_stat): tx 1,270.6 um2 std; rx 56,424.0 incl. 53,296 SRAM (3,128 std); original 57,692.1.

## 3. Equivalence (CHECKED, Verilator 5.050 on epyc2, eq/tb/tb_split.sv)
Original face-shelled hfd_ep_static vs hfd_ep_static_pair (tx core + rx core), each sd_tx looped into its own sd_rx,
same random/legal-protocol COLL stimulus. Every cycle: all outputs except fault_cause[9]/fault exact; pair.fault_cause[9](t)
== orig(t-2); fault equal outside the 2-edge window. 10 runs (8 legal-protocol: 109-125 blocks, 1,744-2,000 rx_pin_v
frames each, 2 random) x 30-40k cycles: 0 errors (eq_results.txt).

## 4. Core probes (AUTO-GEOM lines CHECKED, review/<v>/auto_geom.json; PNGs viewed)
| probe | outline | pins | AUTO-GEOM GRT50 | FAIL rules |
|---|---|---|---|---|
| ep_my (before, KITS-18) | 241.92x397.44 one core | W tx / E rx | 255,546 | r2r 539.9/59, col_v 2.03, channel_v/h, grt |
| tx | 112.32x133.92 | sd_tx S, tx_frame W | 0 | fill 0.0895, empty 0.67 |
| tx2 | 99.36x99.36 | sd_tx S, tx_frame W+N (0.192) | 0 | fill 0.1365 only (r2r 159.9, col_v 0.33) |
| tx3 | 95.04x95.04 | 4 faces | 0 | fill 0.1492, partial_face 1 (sd_tx on S+E) -> tx2 preferred |
| rx1 | 241.92x397.44 same slot/column | E as plan | 33 | r2r 470.7/2 (status N pins), col_v 2.0, channel_v 1.59, clock_reach* |
| rx2 | 285.12x397.44, column x 12.96 | sd_rx S, rx_pin_flit E | 0 (21 it) | fill 0.057 + empty (macro 47 % < 50 -> not INFO), r2r 415/1, col_v 1.81, clock_reach* |
| rx3 | 263.52x397.44, column x 12.96 | sd_rx S, rx_pin_flit E, status N over strip | 0 (17 it) | r2r 430.6/3 (block0 bank pin_flit top -> merged pin_flit low-E), col_v 1.73 / channel_v 1.51 at the SRAM E-edge gap (est.), clock_reach* |
*clock_reach: island clock infra stubbed in the probe (not comparable; ep_my with islands 188.6).
Verdict: TX core clean apart from the fill band (pin-limited: 1,125 pins vs 1,271 um2 std; fill grows with CTS/hold
cells; fill is a GEOM-AUTO-2 band, not routability). RX core: GRT 0 needs the column-to-one-side + ~70-um strip (rx3);
same slot (rx1) leaves GRT 33. Next for rx3: rx_pin_flit pins spread over the whole E face (bank 0 SRAMs are top) or one
relay stage on the bank->merge hop (+1 RX cycle, price it), then CTS with the island infra.

## 5. Plan delta needed (NOT applied; plan of record d16k_q2L untouched)
- +1 core type hfd_ep_static_tx (6 placed: NW_io u_ep_N0 + u_host_ep, NE_io u_ep_N2, q_spb0 / q_spb0__physical_v1 u_ep_S0,
  vsN0 u_ep_S1); hfd_ep_static -> hfd_ep_static_rx in the same slots (types stay under the <~80 target).
- tx slot: 99.36 x 99.36 in the 453-um street between the SerDes u_lk (y <= 635.04) and the EP (y >= 1088.64), x over
  u_lk's tx pins; pins sd_tx S (faces u_lk: fixes the G0C q_spb0 u_ep_S0 sd_tx 'face W, re-pin to S' error by construction),
  tx_frame W+N toward the COLL bus; rst_n / tx_cal_fault on E; clock entry centre (+1 tap per instance, ~2.7k sinks).
- rx slot: widened 241.92 -> 263.52 in place (+21.6 um in x; all five partitions have room: max x1 496.8 of 648 in NW_io),
  SRAM column MY at x 12.96, sd_rx/sd_st on S (faces u_lk), rx_pin_flit E, status N; tx_cal_fault from the tx core = one
  1-bit core-to-core wire (+2 edges on the sticky cal-fault status only).
- Then: core_conns (u_eptx<->u_lk, u_eptx->u_eprx), bind map (hfd_ep_static instance -> pair), kits from the plan pins.
