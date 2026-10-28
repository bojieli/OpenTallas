# DIE-HEAD-9 FACE (b): FSTART structural fix -- design note (NOT implemented; UNCHECKED analysis)

Measured today (hd_tile 1_2_yosys.v sha ebc5cd6c, face_guard @ claude/die-head-9-face-1028):
`cland_fstart_in_i: 8 loads on u_cland_origin/p_start` and `cland_fstart_out_o: net u_cland_origin/start has 15 loads
besides the port chain`. Both are `shared`. Everything else on the hd_tile face passes (568 hold_mux slot bits + the
clock_export contract once the RTL is regenerated with the contract source).

## Current structure (rtl/common/ot_dp_clk_landing_ca.sv, tools/die_plan/clock_landings.py)
- IN: `cland_fstart_in_<b>` -> `ot_meso_ring_ca.t_rst_n` (tclk=fclk_in: resets tc, GATES every slot write,
  ring_ca L245-250) AND -> `ot_dp_landing_origin_s.p_start` (clk: async_reg s0 via strap_efall mux with the negedge
  sf, L414-420). Emitter: clock_landings.py L672-683 (ring), L797 / L829-L847 (origin).
- OUT: `assign cland_fstart_out_<b> = cland_start` (clock_landings.py L605-606); `start = taps[strap_pad]`,
  taps = {pd, s2} (origin_s L421-424): a strap MUX output shared with the receiver rings' rst_n and monitors.

## Proposed fix
OUT (0 added cycles): a dedicated registered copy in ot_dp_landing_origin_s (new output `start_o`, keep):
  `taps_e = {pd[PADMAX-2:0], s2, s1}`;  `always @(posedge clk) start_o <= !rst_raw_n ? 0 : taps_e[strap_pad];`
  Invariant start_o(t) == start(t) for all t (pad 0: s1(t-1)=s2(t); pad j>=1: taps[j-1](t-1)=pd[j-1](t)); same reset.
  Emitter: `assign cland_fstart_out_<b> = cland_start_o`. Internal loads keep `start`. Port net = one FF Q only.
  Proof: SBY/Yosys induction start_o == start over all strap_pad/efall (strap form) + mutant (taps_e = taps, i.e.
  +1 cycle) must FAIL; LEC of the tile vs old RTL with start_o mapped to start.
IN (needs the sender pre-issue to stay at 0 cycles):
  receiver private capture FF on fclk_in: `fs_q <= cland_fstart_in_<b>` (one load on the pin); ring t_rst_n and the
  origin p_start both take fs_q. fs_q(e) = pin(e-1), i.e. the ring write gate and origin see start ONE fclk cycle late.
  Because t_rst_n gates the slot writes, a late gate DROPS sender word 0 (not just a K shift), so it must be
  compensated at the sender: export one tap EARLIER, `start_o <= taps_ee[strap_pad]`, taps_ee = {pd[PADMAX-3:0], s2,
  s1, s0}. For strap_pad >= 1 the source is s1 or later (resolved synchroniser stage): net 0 cycles end to end, no K
  change, phase class unchanged (fs_q launches from fclk_in, which arrives with the same flight as the old pin).
  For strap_pad == 0 the source would be s0 (first async_reg stage, metastable) -> NOT allowed. Those senders take
  strap_pad := 1 (sender count origin +1 cycle): K ledger +1 on every crossing that sender drives, root/boot deadline
  +1 if on the longest origin chain.
Ledger to produce before RTL: per HEAD crossing (427) sender strap_pad (count_align_bind straps strap_ca_pad), count of
pad==0 senders (= crossings that pay +1), resulting K and D4 window margin (K+1 must stay inside the ring window,
count_align_plan hull), boot depth. Root senders (ot_dp_landing_root / non-strap origin) need the same start_o form.

## Bench / proof set (smallest vehicle: one sender origin_s + one receiver landing_cas pair)
1. existing crossing bench 56/56 (8 types x phase 0/+-183 FF/+-201 TT/+-300) rerun: word-exact, fault 0, same K.
2. mutants: (a) receiver capture FF without sender early tap -> word 0 dropped / fault; (b) start_o from taps (not
   taps_e) -> +1 misalignment caught; (c) start_o from s0 at pad 0 -> refused by a structural check (no async_reg Q
   to a non-sync load).
3. face_guard on the regenerated hd_tile: cland_fstart_in_i / cland_fstart_out_o as ordinary 1-load / 1-FF pins.
Shared files: rtl/common/ot_dp_clk_landing_ca.sv, tools/die_plan/clock_landings.py, count_align_bind.py (pad>=1
rule) -> ROOT-MERGE; HEAD plan straps die-local.

## Status 2026-10-28 07:00 PDT (DIE-HEAD-9 face fork)
- DONE: ot_dp_landing_origin_s gets `start_o` (registered copy, taps_e = {taps[PADMAX-1:0], s1}); not yet connected
  by any emitter (unconnected output: no behaviour change; Yosys removes it). Proof fv_origin_start_o.sh: SAT temporal
  induction start_o == start, PADW 1..4 x every strap_pad x strap_efall 0/1 = 60/60 PASS (induction length 1);
  mutant OT_ORIGIN_MUTANT_LATE (so <= taps[pad], +1 cycle) caught 60/60 (CHECKED, fv_summary.txt).
- OPEN: emitter hookup (clock_landings.py L605-606 cland_fstart_out_<b> = cland_start_o) needs start_o on every origin
  form that can drive a forwarded start: strap (+ strap_ca_root mux: root copy too), child ot_dp_landing_origin,
  root ot_dp_landing_root, relay rx. Then regenerate hd_tile, face_guard, crossing bench 56/56, strap_lec per value.
- OPEN: FSTART in (receiver fclk capture FF + sender early tap, pad 0 senders +1 K) -- ledger first.
