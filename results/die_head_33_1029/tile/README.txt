DIE-HEAD-33 hd_tile (fork, step 1) Thu Oct 29 06:25:36 PM PDT 2026. Data intel2 /srv/opentallas-scratch2/claude/die-head-33/tile.

ESTIMATE (est.py on DIE-HEAD-32 V1r geom.tsv + kit land_slots/face_guard; CHECKED own run):
  pin_reg_p90 80.0 is NOT led by the 2 scalars: all 568 ring-landed pins are judged at their FARTHEST of 4 slot flops;
  568/568 >= 30 um, 116 >= 80 um (p50 of ring pins 62.3). Cause 1: 568 read-select registers u_ring.dch[c].u_dsel/y[j]
  (one per bit, bit = 64c+j) do not match the 2-D ffkey and sorted by NAME to the band bottom (y 708-768), pushing
  every slot up ~60 um. Cause 2: the scalars cland_dn_ready_i/fault_i are ring bits 566/567 -> +ffr puts them first
  (band bottom y 769) although their pins sit at y 863-865 (132.4 / 129.8 um).
  Floor: the 4 slots of one bit sit in 3 x-columns 17.3..38.3, so the farthest-slot distance is >= ~38 um for every
  ring pin; p90 <= 30 is not reachable by placement of a DEPTH-4 ring judged at its farthest slot (GEOM ruling item).
  pin_unreg cland_fstart_in_i = t_rst_n of the CA writer (sync reset of the tc/status counters through logic; by design
  the declared ring_start, COORD (B)); not a placement item -> anchored by locality only (tc keyed at its pin y).

VA (built) = V1r kit + kit-local landing_placement.tcl tag +ffp (patch_ffp.py, ffp.tcl): ring flop band order follows
  the input-pin y of each flop data cone (BFS back from D, <=12 comb levels, stop at seq/clock); read-select y[j] takes
  its bit pin; no-pin control flops stay at the band bottom. Verified on the V1r ODB (ffp_test.tcl): 2272/2272 slot
  flops map to their own pin i[k] / dn scalar (CHECKED, ffp_pins_v1r.txt.gz). Placement only: 0 cycles, 0 flops,
  RTL unchanged. Placed (ot_face_flops.txt, CHECKED): dn_ready/fault slots y 846-849 (pins 863/865; was 769),
  i[565] slots y 715 (was 769.5), dsel y[j] with their bits, tc at y 853 next to the fstart pin (y 867).
  PLACE unit oth-ubuntu-1143333 (intel2 die-head-33/tile/va); AUTO-GEOM -> geom_va/ (see RESULT below).

CLOCK ENTRIES (clk_est.py, k-center on legal tap sites = 17.28 lattice, TAP_CLEAR 8.64 off the 5 macros; CHECKED run,
  clk_est.out): the DIE-HEAD-30 '12 (<=220) / 16 (<=200)' count ignored capacity and macro clearance. With both:
  R200 -> 13 greedy entries, 11 street-edge sinks uncoverable on the lattice (reach 303.9), loads 4..7056 vs the kit
  hard cap OT_TAP_MAX_SINKS 3000 (OVER); R220 -> 12 entries, loads 3..6383 (OVER). So 12-16 uncapacitated entries
  do not hold. The existing tool for this is clock.tap_mode density (taps.density_taps: <= tap_target_sinks per tap
  within tap_radius_um; sinks from the placed netlist via sink_bins_file), i.e. a fix-only hd_tile PLAN delta (ports
  clk + clk_t<i>) whose taps the die clock (ot_clk head config) must feed. A partition kit has no in-tile
  core_tree hook, so a kit-only entry set is not available. NOT built (plan + die-clock event -> die owner).
