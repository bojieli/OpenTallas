# Scan + stuck-at ATPG on one DS S81 ROM element and one HBM-accelerator SM element (0.833 ns, 2026-10-04)

All numbers in `record.json`; open tools only (Yosys/ORFS/OpenROAD, `tools/dft` inserter + otatpg PODEM, Verilator).

| | DS S81 q element `ot_v41_rom_elem_q_qp_w10` | HBM SM tensor-core column `ot_gpu_bd_col` |
|---|---|---|
| Scan | 31,606 flops, 31 chains (max 1,032); ROM outputs X-bounded (1,096 AND2), ICG opened in test | 6,006 flops, 6 chains (max 1,001) |
| Stuck-at faults | 1,281,058 | 380,326 |
| Fault / test coverage | **95.58% / 99.77%** | **94.44% / 99.78%** |
| Patterns (tester cycles) | 9,042 (9.34 M) | 1,606 (1.61 M) |
| Gate-level replay | 0 good-machine mismatches, 48/48 capture + 16/16 chain faults confirmed | same |
| Scan-off == no-scan | proven, 31,793 points (macros/ICG as cut points) | proven, 6,056 points |
| Netlist area added | +2,457 um2 (+10.6%) | +516 um2 (+7.9%) |
| Routed delta at 0.833 ns | **does not route**: util 88% vs 84%, detailed route 18,839 DRC after 15 iterations / 6 h (no-scan converges) | +10.3% std-cell area, +16.7% wirelength, SS WNS -102.6 -> -117.0 ps (-14.4 ps), FF hold +3.5 -> +4.4 ps |

Notes
- New default-off tooling: `tools/dft/macro_bound.py` (+ `run_abi3_physical.py --dft-bound-macros`): scan around hard
  macros (X-bounding) and ICGs, ATPG netlist in test mode, cut-point equivalence. Earlier records unchanged.
- The whole SM element was never routed (hbm_accel_fmax_inventory); its replicated leaf was used. The baselines do
  not close in these frames: q element boundary paths (reg-to-reg SS +124.5 ps), bd_col generic recipe (-102.6 ps,
  its committed closure used per-port budgets). Deltas are scan vs no-scan in the same recipe.
- Verdict for the q element: full scan does not fit the routed 510.84 x 126.9 um frame. A larger frame or scan
  compression is required before the element abstract can carry DFT; not tuned further (owner rule).
- Not covered: transition-fault ATPG, die-level chain stitching / compression / TAP, the ROM arrays (MBIST).
