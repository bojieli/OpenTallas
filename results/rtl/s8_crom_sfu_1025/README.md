# S8 CROM operand-age repair: SFU return-pipeline gate (2026-10-25)

Collected by QC-TOK from Codex's run intel2:/srv/opentallas-scratch2/claude/codex-s8-crom-sfu-1025 (no rerun). Bench
`rtl/test/qwen_dv/s8_memory_align/tb_s8_memalign_sfu.sv` + `run_sfu.sh` (codex/s8-crom-sfu-1025@0854ca24e), Verilator
5.050. Sources: the 32 files of `sources.f` (+ `rtl/qwen_dv/qfd_dv_head_safe1.sv`); `sources.sha256` = byte-identical to
this branch (includes the CROM alignment c1c42f554, opt-in `OT_S8_CROM_ALIGN`).

The original head miter covered VM/CROM/BTAB arithmetic on class 0 only. This gate drives the actual EXP / RECIP / RSQRT /
SIGM return modules through every class switch twice (5 classes x 64 outputs, idle/accept transitions, 192-edge guard >
TAPMAX 136, 416-cycle drain) and compares output, tags, fault and the SFU requests at the +3 edge alignment.

| run | result |
|-----|--------|
| clean (aligned) | **PASS**: checked 6,336 cycles, 320 outputs, 0 mismatches, classes 64/64/64/64/64, requests EXP 128 / RCP 128 / RSQ 64 |
| mutant `OT_S8_CROM_ALIGN_MUTANT` (wrong VM depth) | **FAIL as required**: 480 mismatches (first at cycle 298, class 0) |

Verdict: PASS (clean exact, negative caught). This clears the gate that held the CROM-enabled 12-slice row calibration
(`codex-qc-crom-cal-1025`) and full stage. It is an RTL-functional unit gate, not a physical or token claim.
