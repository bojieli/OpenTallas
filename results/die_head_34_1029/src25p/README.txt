DIE-HEAD-34 src25p (2026-10-29): one combined fix-only HEAD event on HEAD-KITS-T src25m_kt (sha256 9ec2309c...)
Source: intel2 /srv/opentallas-scratch2/claude/die-head-34/src25p  source_plan.json sha256 dfc1826f91e0059650b82897ae062bdbf82313c418db809a2eaebecf081f4b99
Generator: src25p.py src25m_kt OUT (EA1 default m864).  0 added cycles, 0 outline changes beyond the admitted lep0N growth.
Plan deltas:
 1 hd_tile clock density r200/1500/1200 + sink bins (tile/tile_density_delta.py) + u_eA1 origin 371.52 -> 362.88 (-8.64).
   The -4.32 shift was off the 8.64 lattice (1 new G0C ERROR; track_offset must be < 2.16). With no shift, density_taps
   fails (sink (653.4,5.4) has no tap within 200).  At -8.64: 38 taps, max load 1252, worst sink-to-tap 191.2 um.
 2 hd_turn_b + 4 spine shims: density r200 over the placed local clk register inventory (strip_sink_bins.py on the
   HEAD-KITS-T V2 dumps; wshim_rx from V1, which has collapsed stations).  Taps 1->5 / 1->5 / 1->4 / 2->11 / 2->4,
   worst sink-to-tap 151 / 122 / 165 / 173 / 184 um (was a single tap with reach 660-1028).
 3 HEAD-013 lep0N +319.68 W = the src25n-vs-src25m delta: types hd_lep0N + hd_st_n4, partition lep0N, reset.in_sites, note
   (RTL is identical between src25m and src25n).
 4 hd_mesh_e rst_start_raw_0/1/3 moved onto M7 tracks (820.832 / 558.752 / 330.4) + insertion_ff_ps 342.67 with its basis.
RTL: only the clk_t<i> wrapper ports + instance hookups for the 6 density types (same region net as .clk), plus the
DIE-HEAD-31 start_d wire on u_st_b0 in start_stages.sv.
Gates (CHECKED):
 G0C --completeness: 2680 ERR / 18 WARN, the same as base src25m_kt; 0 new findings, 0 removed (2698 findings each).
 Strict die port-bind (run_source_portbind.py): HEAD_DIE_PORTBIND_SOURCE PASS, nested PASS (4299 instances).
 Die clock check (ot_clk, head_src25m.yaml config pointed at src25p_m864, whose clock taps are identical to src25p's;
 only hd_mesh_e reset-pin x differs): GRT0 overflow 0 TT/FF, 10661 taps, duty outside 45-55 0/0, MPW 0,
 spread worst raw 100.2 TT / 97.0 FF (0 regions >150), OCV+droop shared 112.3 / 106.2, stated 134.9 / 119.2 (0 >150).
Not in this source (no plan field reaches them):
 (c) hd_st_turn: band OK (V2 FIT_RESERVE placed 2676/2686 ring flops at spread 4.29, 0 overlaps).
     hd_st_n3_turn: the failure is not band size. Status flop cland_up_fault_d1_o has a fixed +-2.16 um window at a top-margin
     pin (y 602.144 > core 600.48), which leaves one row; FIT_RESERVE footprint vs a tapcell near x 354.3 (UNCHECKED).
     Needs a flow fix (status window) or a pin move.
 (a) hd_st_str / hd_st_n3_transit: fault/ready collector from the E band (x~1380) to the W status pin = ~1440 um in one cycle,
     which needs relay cycles or a pin move: OWNER ASK.  hd_turn_a: origin (at the tstart die pin, y 617) -> fstart_t_o
     (y 2.7) = 614 um: same.  wshim_tx 490: u_rrl relay collapse = FLOW-KITFAIL-2 face_flops fix, not plan.
