# HBM-SMXL2 (10-20): SM.MATVEC real x-batch path, fixed-slot replay PASS, measured + recomposed

Branch claude/hbm-smxl2-1020 = claude/hbm-smxl-1019 cbd6a417c (XSLOT: descriptor xb rides the go context and relocates
every command's xaddr = the die SM op_xb from the static programme, no tie; OPEN_IL open interlock; compiler residency
model) + codex/smxl-cache-1020 ba838d881 (cache-tail OPEN_IL fix ecec735b6, cache contracts) + tb PTRACE diagnostic.
Bench tb_toksim_smhbm.sv, Verilator 5.050, controller TOKSIM_PC=mc3 (4 x ot_hbm_svc_pc_ctrl_leaf_cfg_safe MC3 structure),
rotated layout, census rows, static GO cadence 80/64+8, OP_GAP/X_GAP 16. Every GO is a fixed compiler slot (sticky fault
on miss, never a stall); every result row checked bit for bit.

## Root cause of the Codex exact-6a FAIL (issuer late GO at 4852)
My compile of 6a reproduces all 29 observed GO slots exactly (dump_sched.py / cmp.py). Steady-state blocks meet the model
(S->go 104 vs model 102). The miss is the routed-expert blocks reserved only after the router ids (4310-4319): with
distinct DRAM rows the controller serialises PRE->ACT per bank (PTRACE A lines: row-29 ACTs on banks 13/12/15/14 ~49 edges
apart, refreshes interleaved), so block 28 (64 lines) landed at 4773 = 457 edges after reserve. The 6a knob SMB_FETCH=80
(per routed block after ids) was below this; the tool default FETCH=200 is the measured distinct-row bound
("one 64-line block per ~160-170 edges + refresh slack"). The cache tail is not the cause (cache fault 0 with ecec735b6).

## Runs (results in runs/; jobs1.txt / jobs2.txt = exact env)
| run | knobs | verdict | cycles |
|---|---|---|---:|
| xl_dsA_s1 | 6a knobs, SAFE PC | FAIL issuer 4852 (= Codex exact 6a) | - |
| xl_dsA_t1 / xl_dsB_t1 | 6a knobs (FETCH 80), MC3 | FAIL issuer 4852 / 7046 | - |
| **xl_dsA_f200** | FETCH 200, MC3, xl | **PASS 42/42 ops, 95/95 GO exact** | **18,429** |
| **xl_dsB_f200** | FETCH 200, MC3, xl | **PASS 24/24 ops, 169/169 GO exact** | **21,941** |
| x13_dsA_m / x13_dsB_m | bench13 serial x (release law), MC3 | PASS (reproduces release units ratio 1.1588) | 26,518 / 27,380 |
| xd_dsA_f200 | die x loader, serial (slot 0) | PASS 42/42 | 20,212 |
Release c_dsA/B_g16_p80 (SAFE) were 26,726 / 27,484. Mutants mi4 (IMUT=4: RTL drops xb) / ms0 (compiler xslot0) and
xlr / x13_f200 references: pending (ep6, see pending_results).

## SM.MATVEC + token (census --measured info_banklat_all, --bw 98 --bridge 1)
units_variants/smhbm_xl_f200.json: DS SM.MATVEC ratio 1.1588 -> 0.7715 (-33%). Qwen unchanged (every Qwen SM record is RAW
on its x, early issue does not apply).
| row | DS tok/s | Qwen tok/s |
|---|---:|---:|
| release measured (TOKSIM-HBM) | 1,162.5 | 1,002.9 |
| + SMXL xl f200 | **1,367.0** (+17.6%) | 1,002.9 |
| SU.VOP measured (HBM-SUFIX) | 1,110.1 | 417.5 |
| SU.VOP measured + SMXL xl f200 | **1,268.3** (+14.3%) | 417.5 |

## Priced cost / qualification boundary
- Every added cycle is in the measured spans (the f200 slots are the static schedule; occupancy = next op's first command).
- Grade measured-newest-bench-passing-NOT-bound: GEN2e4 die.v instantiates svg_SW* without XSLOT/OPEN_IL. Adoption =
  die generator params XSLOT=1, OPEN_IL=1 on ot_hbm_svc_sm_group_rel_id + svc tile safe checklist + pre-gate native32
  census (XSLOT adds a 7-bit xb to the go context and a mod-128 add in the existing feed R-stage add).
