# s81su_full composition gate at main 2974cb067 (stream rom-layer-tput-s81, round 5)

Hierarchical SU slab `dsfd_sp_su_h`, full shape, `tools/s81_suhc/su_gate.py run --shape full --hier --fp dpi` under
Verilator 5.050 on ot-epyc1tb through `ot-run --mem 48` (`su_main.sh`, `otrun.log`: RAN exit 0). Source is
`git archive` of main 2974cb067; `run_full_dpi_m0_a0_h.json` carries the sha256 of every compiled file.

This is the re-run of the retired PVE1 DPI build (no process and no directory were left on ot-pve1). The SU control
RTL changed after the 9e37b21b2 record (`ot_s81_su_ctl.sv`, `dsfd_sp_hc_c.sv`); the job cycles did not.

- Positive: golden_L0 / golden_L2 / stress_0 PASS, 0 / 1,722 rows, 3,149 cycles.
- Mutant 5 (stale denominator): FAIL as required (stress_0 220 / 1,722 rows, `run_full_dpi_m5_a0_h.json`).
- Job cycles at the slab pins (start to done), identical in the three runs and identical to 9e37b21b2:
  QN 301, KV 357, QB 167 and 167, SW 353, SE 387 and 466, SO 303 and 303.

The accepted-cost rows SU.QB, SU.SW and SU.SO (`results/arch/accepted_cost_ledger_1013.json`) therefore stand at
their figures. It qualifies no tile (that is the routed-top gate `s81su_tiles`).
