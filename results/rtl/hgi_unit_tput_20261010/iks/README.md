# IDX index-key stream issuer (IKS = 1) on a real svc stack

`rtl/hbm_accel/generic/idx/ot_hgi_idx_iks_issue.sv` driving `ot_hbm_svc_core_native` IKS = 1 (the kind-2 stripe over
all 32 PCs), bench `rtl/hbm_accel/generic/idx/tb_hgi_idx_iks.sv`, runner `tools/hgi_unit_tput/run_iks.sh` (ot-epyc3,
Verilator 5.050).  Controller model: a 4-sector read a PC a cycle, beats in order LAT 104 later, one beat a PC a cycle.

| run | blocks | lines exact | go -> ik_done | delivered | priced (104 + bytes / 791.7) | ratio |
|---|---:|---|---:|---:|---:|---:|
| q0 (quarter 0) | 342 | 1,368 / 1,368 | 460 | 404.5 B/cycle | 339 | 1.36 |
| q3 (quarter 3, N 9,000) | 99 | 396 / 396 | 174 | 309.5 B/cycle | 172 | 1.01 |
| q0a (adversarial stalls + credits every 23 cycles) | 342 | exact | 2,603 | exactness only | | |
| q3m (MUT 1: B_q of the previous quarter) | | **FAIL as required** (1,368 lines for 99 blocks) | | | | |
| qmis (key-region base not row-aligned: base[19:0] = 4,096) | | **FAIL as required** (issuer fault, nothing issued) | | | | |

row0 (lead decision 10-10): from the record's key-region descriptor base, row0 = base[34:20]; the issuer faults unless
base[19:0] = 0 and base[36:35] = 0.  Open: the IDX.INDEX record must carry that descriptor (proposed operand I; compiler
owner e) and the die idx bus must carry it; the four e beats go to the stacks' svc e ports (hbm-phys).
