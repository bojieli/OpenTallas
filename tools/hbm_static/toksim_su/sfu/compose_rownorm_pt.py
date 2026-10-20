#!/usr/bin/env python3
"""HBM-SUFIX (b) 10-19: compose Qwen FUSED.ROW_NORM per record on the d4g SU WITH the closed HH-6 pre-tree bound
(hbm_su_pretree_s_1018-p3-1dad69123) from the MEASURED pieces + the RTL-header fixed edges of the rest of the chain.
All edges serial (SU / reducer clock, 0.9 GHz); stream (833 ps) = x 4/3.
MEASURED (Verilator 5.050, exact edges + bit-exact csum golden, mutant witnesses FAIL):
  PT  tb_hbm_su_red_pretree @1dad69123 (4 x pretree_s + qcore_r5 PRETREE + reducer): tree_cmd edge E -> EXPORT edge
      (run_rownorm_pt.sh: seg128 heads, 1 / 2 independent blocks per quarter; interleaved d4096: 8 blocks per quarter,
       each block exported (LOAD + EXPORT, DEP 10))
  T32 su_reduce_tb tree32: reducer 0 joins the 32 RF block values in golden order (16 pairs + 15 tree) -> 91 to scalar
HEADER CONSTANTS (prod_compile.py / RTL headers, not benched here):
  FILL 16  dispatch -> first emit (VM fill commit E + RR 12 + 3, ld 8 before the emit)
  LIN 28   emit -> lane value on ro_x (MLAT 4, ALAT 3, LEAF 1): the pre-tree / red_sel sample edge
  RF 45    EXPORT edge -> RF word readable by any lane / reducer (+13 + L_RF 32, stree RF_TREE 1)
  RSQ 74   rsqrt issue on the global-lane-0 side pipe -> its value at the reducer (LIN + sfu_depth(rsqrt) 46), one
           issue per scalar per edge; s*fp32(1/d)+eps in the same issue (cp_m1 3 imm, ca_ad 4 imm)
  R2RF     the r scalar re-enters the RF through reducer 0: LOAD at the lane-out edge, EXPORT DEP 10 later, + RF 45
  Y        y = (x * r) * g on all lanes (B = RF broadcast, C = gain row in VM), out BF16/FP32: issues + LIN + drain 2 +
           (2 sectors per issue on the 8 ports) + LG 4 + WR 10
The gain row g (HBM BF16) is a static-address prefetch to VM issued before the record: not on the chain (the price's
+25.2 HBM first access is therefore not charged).  Golden order is unchanged: s = csum(mul(x,x)) (chunk-8 + aligned pairwise
tree), r = rsqrt(s * fp32(1/d) + eps), y = (x * r) * g (lib.row_norm), so the composition is exact by construction of the
measured parts.
usage: compose_rownorm_pt.py PT_OUT RMS_OUT > rownorm_compose.json
"""
import json, sys
from pathlib import Path
FILL, LIN, RF, RSQ, DEP = 16, 28, 45, 74, 10

def y_pass(issues):
    return issues - 1 + LIN + 2 + (2 * issues - 1) + 4 + 10

def main():
    pt, rms = Path(sys.argv[1]), Path(sys.argv[2])
    c = {k: json.loads((pt / k / 'case.json').read_text()) for k in ('seg128_q2', 'seg128_k1', 'd4096_q8')}
    t32 = json.loads((rms / 'tree32' / 'calendar.json').read_text())['rows'][0]
    out = {}
    # seg128 heads: head h = block h, quarter h % 4, issue h // 4; s per head is quarter-local (one block = the whole head)
    for name, case, heads, issues in (('q_norm_1024', 'seg128_q2', 8, 2), ('k_norm_256', 'seg128_k1', 2, 1)):
        e = c[case]; E = e['first_tree_edge']; X = max(x['edge'] for x in e['exports']) - E
        rd = X + RF                                  # last head s readable
        rs0 = rd + 2                                 # rsqrt issues rs0 .. rs0 + heads - 1 (lane 0 side pipe)
        lo = rs0 + heads - 1 + RSQ                   # last r at reducer 0 (LOAD)
        r_rd = lo + DEP + RF                         # last r readable (EXPORT DEP after its LOAD)
        tot = FILL + LIN + r_rd + 2 + y_pass(issues)
        out[name] = dict(serial=tot, stream=round(tot * 4 / 3, 1), terms=dict(fill=FILL, lin_xx=LIN, pt_ss_to_export=X, rf_s=RF,
                         rsqrt_issue=2 + heads - 1, rsqrt=RSQ, r_to_rf=DEP + RF, y_pass=2 + y_pass(issues)))
    # d4096, the VM layout as is (block b of the row in quarter b % 4): every quarter exports its 8 block subtrees (PT
    # blocks on consecutive edges, LOAD at E + PT_RED + i, EXPORT DEP later); reducer 0 joins the 32 in golden order (T32)
    PT_RED = c['d4096_q8']['PT_RED']
    X_last = PT_RED + 7 + DEP                       # last block EXPORT (blocks of a quarter emitted E .. E + 7)
    # T32 loads evens first: even block 2i (quarters 0/2, emitted at E + i // 2) readable at PT_RED + i//2 + DEP + RF;
    # start so that every LOAD i (start + i) and ADD_EXT i (start + 16 + i) finds its operand readable
    start = max(max(PT_RED + (2 * i) // 4 + DEP + RF - i for i in range(16)),
                max(PT_RED + (2 * i + 1) // 4 + DEP + RF - 16 - i for i in range(16)))
    X2 = start + t32['export_cmd'] - t32['first_cmd']
    rd = X2 + RF; lo = rd + 2 + RSQ; r_rd = lo + DEP + RF
    tot = FILL + LIN + r_rd + 2 + y_pass(8)
    out['prenorm_4096'] = dict(serial=tot, stream=round(tot * 4 / 3, 1), terms=dict(fill=FILL, lin_xx=LIN,
                               pt_and_t32_to_export=X2, last_block_export=X_last, rf_s=RF, rsqrt_issue=2, rsqrt=RSQ, r_to_rf=DEP + RF,
                               y_pass=2 + y_pass(8)))
    print(json.dumps(out, indent=1))

if __name__ == '__main__':
    main()
