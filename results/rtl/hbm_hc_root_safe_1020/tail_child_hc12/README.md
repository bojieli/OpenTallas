# HC tail child k6 (HBMc/HC-TAIL2 10-22)

## k5 native 5/48: root cause

The netlist generator caused the k5 failure; the RTL did not. On every fleet host /usr/bin/yosys is 0.52, and its
dfflibmap maps the ASAP7 DFFASRHQNx1 cell (liberty ff IQN, next_state !D, clear !SETN, preset !RESETN) with set and
clear swapped. Every async-reset flop therefore reset to the inverted value. The ot_rst_relay sync flops then never
asserted the core reset, so the native lockstep depended on the init mode.

- `yosys052_async_repro/`: a 2-flop repro (yosys 0.52 inverted, yosys 0.68 correct).
- `tailc_k5r_native_m0_run.log`: k5 regenerated with yosys 0.68 at OPIPE 0 passes 48 (+495).
- `nl.sh` now refuses yosys < 0.68.

## Bench and init fix

The random-init FAILs (1-3 of 48, on RTL and native alike) came from the reference unit. Its Sinkhorn is on the derived
sink clock, and with rst_n low from t = 0 there was no negedge. The bench now pulses rst_n at t = 0.5.

## k6 netlist (OPIPE 1, child offset 496)

`OPIPE=1 nl.sh k6 17 1 3 496 1040` produces 48,758 flops and passes the census (limit 32, max 24).

Evidence, all with Verilator 5.050 on gold2:

| Check | Result | Log |
|---|---|---|
| RTL lockstep | PASS 48 | `tailc_k6_rtl_m0_run.log` |
| RTL, init modes 1, 2:1, 2:2 | PASS | `*_init*` |
| RTL mutant MUT1 | FAIL 44/48 | |
| RTL, offset 495 | FAIL 48/48 | |
| Native lockstep | PASS 48 | `tailc_k6_native_m0_run.log` |
| Native lockstep, new bench | PASS 48 | `tailc_k6_native_m0_newtb_run.log` |
| Native, init modes 1, 2:1, 2:2 | PASS | `tailc_k6_native_m0_init*` |

Native mutants:

- Sinkhorn XOR2 to XNOR2 at sk_c241920: FAIL 48/48.
- result[300] driver INV to BUF: FAIL 47/48.
- Sinkhorn NOR2 to NAND2 at sk_c100022: escaped. That cone is not observable on these vectors; it is kept as a record.
