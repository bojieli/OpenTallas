# QC-CORES-1: s8x_vmr F4H (2026-10-27)

## Root cause of the F4G 2-violation DRT stall (CHECKED from the DRC marker reports and an ODB probe)

F4G (QC-SU-F4G, epyc2 `qc-f4g-1026/kits/qfd_dv_s8x_vmr_f4g`) detail-routes every clock net alone first (B1, DRC 0). It then runs one signal DRT. In that DRT, every clock net keeps its wire and loses its guides, so DRT treats the clock wires as fixed shapes.

The markers from iteration 20 through 50 (`f4g_drc_it20.rpt`, `f4g_drc_it50.rpt`):

| marker | nets | location | what is there (probe `marker_probe.tcl` on `5_1_grt_f4g_clk.odb`) |
|---|---|---|---|
| M2 Short | `_02281_` vs `ot_ms_Q4B1L1_clk` | (83.77..83.87, 13.41) | `_02281_` = pin B of XOR2x2 `_15072_` (83.70-84.29, 13.23-13.50); the leaf wire of the 58-sink `Q4B1L1` crosses this pin field |
| M3 spacing | `_04805_` vs VDD | (118.94, 15.37..15.41) | pins B1/B2 of AO22 `_10327_`/`_10829_`/`_10079_`, under the via stack where the M2 rail at y 15.39 meets the M5 stripe at x 118.84-118.96; locked leaf wires to `l_sud[12]` and `l_sud[179]` CLK sit next to it |

At iteration 20 there were 3 more markers of the same kind: `_02289_` vs `Q4B1L0`, `net1183` vs `Q7B1L2`, and M1 spacing `pvm_waddr[116]/[3]` vs `Q4B1L0`. All of them involve leaf nets.

Cause: the B1 leaf nets `ot_ms_*_clk` (66 of them) were routed without any knowledge of signal pin access, and the lock then made them immovable. The F4F co-route of the same database reached DRC 0, and RP1 F4G try 2 re-routed leaves locally in pin areas. Both show that this pin-field conflict is resolved once the leaves can move.

## Structural fix (F4H)

The trunk lock that ruling (a)/(b) asks for is kept: the tree nets `ot_ms_*_n` (37 of them, on M5/M6) stay pre-routed. They lose their guides, keep the NDR geometry from B1, and are covered by the same M6 strip obstruction.

The 66 leaf nets `ot_ms_*_clk` drop their B1 wire, keep their guides, and are routed together with the signals (`OT_F4H_LEAF=reroute`, `f4g_pre_drt_sig.tcl`). The LOCK gate is now scoped to the tree nets (`clkdiff.py SCOPE=tree`).

Nothing else changes: same F4F post-hold GRT, same CTS and hold, same B1 database, same M6 strip, and the same finish/RCX/sign-off/LEC tail. There are no trims, pads, clock ECOs, or data/reset cycles.

Smoke test (CHECKED): the pre script reports leaf_nets_rerouted 66, clock_nets_prerouted 40, m6_obstructions 687. After it runs, 0 leaves have a wire and the leaves hold 10761 guides.

## Run

- ot-run unit oth-ubuntu-3601087-1793095695, on epyc2, started 03:08 PDT.
- Kit: `epyc2:/srv/opentallas-scratch2/claude/qccores1-1027/kits/qfd_dv_s8x_vmr_f4h`.
- Files to collect: `f4h_chain.txt` (F4H_LOCK / LAYER_SEP / F4G_LEAF / SIGNOFF / CHAIN_DONE), `f4h_drt.log`, `signoff_main/signoff.json`, `lec_final/lec.json`, `island_shift.json`, `meas/rcx_*_prehold.tsv`.
- The F4G job (unit 714733) is left running and untouched.
