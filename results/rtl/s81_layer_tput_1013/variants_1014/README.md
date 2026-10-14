# S81 layer variants, measured 2026-10-14 (T3 rom-layer-tput-s81)

Bench: tb_s81_die_layer NG 256, HCH 1, FP dpi, nom (EPER 0), --coef-split --h-stream, -GPIPE=1 -GHST=1 -GHTX=2 -GPGAP=600; L14 via hc_chain_L14.pkl; ot-epyc1tb.  Source: claude/s81-layer-variants-1014 b98003e84 = main be0b9ccca + merge claude/s81-norm-tree-1014 7d904baa4 (NTREE default 0).  Script: `var.sh`.

every positive run PASS: y 640/640, NORM rows 330/330, H_STORE 640/640, hand-off flits exact; def mut_hc L0 FAIL (NORM 85/330, H_STORE 0/640).

| variant | L0 | L2 | L14 (Engram) | delta vs def | e2e % AR |
|---|---:|---:|---:|---|---:|
| def: current default: LVM 54 (leaf hop 2 + FE, the owner-accepted VM read), NTREE 0, priced SU durations | 8,702 | 17,610 | 19,183 | [0, 0, 0] | +0.000 |
| def10: bench default LVM 10 (cross-check: reproduces the NORM-tree branch g2c base 8,660 / 17,566) | 8,660 | 17,566 | 19,050 | [-42, -44, -133] | -0.229 |
| xgos: XGOS prefetch EQUIVALENT: LVM 54 -> 38 (unit bench hierarchy 107 -> 91, -16 a dependent read; the vehicle VM is behavioural, no controller XGOS issue) | 8,688 | 17,594 | 19,130 | [-14, -16, -53] | -0.082 |
| ntree: NORM tree NTREE 1 NT_K 67 (claude/s81-norm-tree-1014 7d904baa4), LVM 54 | 8,276 | 17,190 | 18,752 | [-426, -420, -431] | -2.043 |
| su: SU RA/RB/QR as on main (hier 65c59faf5): --dur attn.q_rope=123 ffn.bias=108 ffn.softplus_sqrt=210 on the behavioural SU port (priced 118/118/186), LVM 54 | 8,716 | 17,624 | 19,196 | [14, 14, 13] | +0.067 |
| all: xgos + ntree + su together | 8,272 | 17,190 | 18,718 | [-430, -420, -465] | -2.061 |

e2e: token delta = 38 x mean(dL0, dL2) + 2 x dL14 (40 S81 layers a token, 2 Engram), / 828,866.4 AR price-basis token cycles; negative = faster. Layer-local, HC share only for VM effects (field / SU / svc VM reads are behavioural or absent in this vehicle).

Findings: (1) the 10-14 "AssertionError: cycle" was a staged source without results/rtl/s81_ctrl_20261008/programs (empty layer), not a program change; fixed by named errors in be0b9ccca. (2) XGOS saves 14-16 cycles a layer (53 on L14), not the ~45 estimated: with --h-stream the H_LOAD no longer reads the VM, so only the attn COEF-a read stays serial; the whole VM read latency 54 -> 10 is worth only 42-44 (133 on L14) a layer in the HC share. The XGOS value is in the field / SU VM-fed classes, which this vehicle does not hold. (3) NORM tree: -426 / -420 / -431 a layer (2 NORMs), -2.04 % AR, consistent with the branch record. (4) SU RA/RB/QR at their measured hierarchical cycles: +14 a layer (+0.07 % AR).
