# EP RX gearbox loop-variable repair

`ot_hep_rx_gbx` used the same module-level integer `j` in the combinational613-bit slot builder and the clocked510-bit previous-beat capture. The new fail-closed HBM RTL lint catches constant613 versus clocked510 drivers on that procedural integer before synthesis. The physical kit therefore correctly stopped before placement (compactq6c2, rtl_lint exit1/runtime exit8); the failure is retained.

The repair gives only the clocked loop its own integer `k`. All data expressions, ports, parameters, register update conditions and pipeline edges are unchanged. Added cycles:0.

The smallest complete mechanism is the full512-bit RX gearbox. `tb.sv` compares all615 output/state bits for4096 cycles with real5-data-beat marker groups and periodic IDLE insertion. Original versus repaired:4096 checks,0 errors. Deliberately incorrect MUT2 IDLE handling:4089 mismatching cycles, caught. The repaired actual RX source also passes Yosys `proc; check -assert` with0 problems (`lint_fixed.log`). Original failed lint and this passing result are separate records; no gate is relaxed.

Run files were produced on intel2 via ot-run in `/srv/opentallas-scratch2/claude/codex-hbm-ep-0825/loopfix/run2/`: unit4067096-1793117733 (8GB/8threads) and4096855-1793117850 (4GB/1thread). Fresh full EP kit lint/LEC/placement proceeds separately; no physical sign-off is claimed by this source repair.
