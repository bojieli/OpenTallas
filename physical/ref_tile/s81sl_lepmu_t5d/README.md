# s81sl_lepmu_t5d (S81-LINK5 L5B-LEPMU 10-21)

S81-LINK5 L5B-LEPMU 10-21: s81sl_lepmu (475.2x691.2, lanes B on S, never closed) re-floorplanned to the lepw_mab_mu slot: 475.2 x 1900.8, pairs A+B on W in four lane bands [20,340] [640,960] [1020,1340] [1650,1880] (each inside its u_ln tile overlap), ro/ri/mu/clk on E, ml on N, fault S. FALLBACK-native: central core -- TX 2 x 10 block (x 43.2 / 259.2, y 345.6.., 86.4 pitch) with the RX SRAMs as 4 lane rows of 5 directly above it (y 1209.6.. 43.2 pitch), ri [960,1300] beside the RX rows. REGATE after t5a/t5b native census FAIL (default params: max 1,559 loads, 694 drivers > 32; floorplan refused): kit params RX_SRAM 1 / IN_PIPE 1 / NATIVE32 1 = the Codex-qualified native32 structure of lep_mu_a/_h (6cb5f3eff, now plumbed through ot_s81sl_lep_mu_ab, defaults 0 unchanged); RX = 5 x 32x128 SRAM per lane. IN_PIPE adds +1 edge on ro / mu_c: die u_lep params + calendar are a LEAD call before bind. Clock: one TritonCTS tree, r6g recipe (no km16: r5e km16 lep twin 91.9/89.6). Same RTL as the die instance (e93685328) except the params listed, same ports and SDC.

SAFE checklist:
1 pins: source-registered (ro / li / ml_rd / mu_c land in pin flops; ri / lo / ml_wd / mu_rt / fault leave flops), reset_landing 2 stages: PASS.
2 reach: RISK, measured by the gate -- the slot geometry spreads the 4 lanes over 1,860 um of W face; cross-lane one-cycle hops (roq -> TX write reg of lanes 0+2 / 1+3, RX head -> ri merge, ml_rd -> ri) are up to ~700-950 um. No relay without an RTL change (+cycles, lead/calendar call); t5b concentrates logic so the long hops are pure flop->flop wires.
3 fanout: native census measured by the gate (default params = die instance; NATIVE32 replicas not exposed by ot_s81sl_lep_mu_ab).
4 depth: unchanged RTL (MU-S81-2/RX rebuild: show-ahead heads, AO222 rid, 0 added cycles).
5 storage: TX 20 SRAM macros; RX 8-deep x 553 flop FIFOs per lane (DR 8 = lane credit depth, RX_SRAM 0 is the die instance param): waived, die binding exactness.
6 floorplan: macros on the 43.2 lattice, 86.4 pitch (35-um channels), full core rows, faces <= 4.7/um; aspect 4:1 waived (slot set by the lane pitch).
7 clock: one tree, r6g recipe, spread <= 80 TT+FF measured by the gate; io_hold_margin 0.03.
8 schedule: 0 added cycles.
