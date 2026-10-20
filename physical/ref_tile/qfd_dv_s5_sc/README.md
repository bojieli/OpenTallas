# qfd_dv_s5_sc -- slice2 scalar face leaf (QW-SLICE6 / Q.STA.SLICE.2)

Top `qfd_dv_s5_sc` (rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv): `qfd_dv_scalar2` (MU_NU 4) with the reducer PSUM tap
(red_addr[23:22] = 11) and the SU broadcast-scalar tap (lane-0 write window 11) decoded locally. One master per slice
(x12). It sits in r_sc (S band, E of ctl): ctl / argmax / VM-write / token ports W, reducer + SU lane ports N, the
chain words W (up_i, dn_o: dn face) and E (dn_i, up_o: up face).

## SAFE-DESIGN checklist (owner 10-19)
1. Pins: flow pin registers on every data input and output (recipe 4, pin_regs on: +1 edge in, +1 edge out, record
   pin_regs.json); rst_n lands in 2 registered stages in the RTL (qfd_dv_s5_rst2), so the flow reset landing is off.
2. Reach: one tile <= 216 um; every pin flop at its face (io_flop_at_pins). PASS.
3. Fanout: the ROOT cfg strobe clears the 32 PSUM slots (~1,050 loads after the pin flop): repair_design buffers it;
   gate textbook_lint high_fanout is the judge (fallback qfd_dv_s5_scb uses the same RTL with a looser outline).
4. Depth: the arithmetic is the closed LAT-3 qadd/qmul + rsqrt_q pipeline (ot_hdc_sfu_q); gate --cts path classes.
5. Storage: 32 PSUM slots x 32 b = 1 kb in flops (< 2 kb, written by index, read whole by the tree); no delay line of
   data >= 3 deep outside the MUT-1 fold mutant (not built). PASS.
6. Floorplan: no macros; square outline sized from the gate's synthesis area at 40-60 % util; one std-cell band.
7. Clock: one centre-fed TritonCTS root; pin-flop spread <= 80 ps TT/FF judged by the gate; io_hold_margin 0.03.
8. Schedule: static; the pin registers add +1 on every input and +1 on every output (sc_cfg -> cfg, chain hop
   dn_i -> dn_o becomes 3 edges, PSUM/RB/argmax taps +2) -> parent lp record / compiler NOTICE (lanes/QW-GEN3.md).

## Benches
eq lockstep (qfd_dv_s5_flat0 == qfd_dv_slice2, 4 modes), b2 programme benches (FACE 3), mutant OT_S5_SC_MUT (the RB
tap reads window 10) must print S5_EQ FAIL (witness results/arch/qw_slice6_1019/witness/sc_mut.log).
