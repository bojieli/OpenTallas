Existing Qwen controller event binding
=====================================

`decode_existing.py EVIDENCE OUTPUT` decodes retained FQREG HB imgh events and
the enabled native TLOAD fixture's stimulus schedule. It starts no simulator.
Evidence is in `results/token_pass/qwen_source_events_1113`.

HB sources/logs came from intel1 `/srv/opentallas-scratch2/claude/qct10/ctlm/hb`,
run `runs/fq_imgh/{ev,log}_m0_b0_TB_LANDED.txt`. The source explicitly selects
NU1 with OPSEG/CTX/INIT/CALR/F16 off. Its CSR, CMD, ROM and XPF observations
remain local fixture facts; they cannot supply ROOT/X/HEAD37 production dates.

The enabled native fixture came from intel2
`/srv/opentallas-scratch2/claude/qct10/ctlm/fx/tb_hp13_native.sv`, with producer
`fx/calr10/producer.json`. It selects NU4, OPSEG, CTX/FCTX, INIT, PRIVATE_CALR
and F16WTN. Reset releases on source negedge16, then warm starts at1.
PW installs on source negedges35..1058, DW on1059..1066, and user0 stages
0..37 start at1315+6200*stage. These are derived from the fixture source,
not global production clocks or measured output dates. Native fixture clock
is1ns; no833ps conversion is applied.

Retained current-main `results/qc_types_10_ctlm_1108/logs/ncmp_fqreg_calr2.txt`
records TLOAD_PRODUCER PASS and LP_LOCKSTEP PASS4,744,920/cycles237300.
It omits the TLOAD_CHECK latency lines. The decoder consequently leaves
actual table output dates unknown; the source's six-edge landed offset alone
cannot determine them. Selected production programme identity, ROOT commit,
X/HEAD leases and global START/reset/clock remain open. No RTL or calendar
adoption is made here; CALREG1 fixture behavior does not silently replace the
current zero-added-edge CALREG0 production source.

DS source phase frontier retained from the current bound wrappers: all four
final `u_cland_unit_i0` instances select `ot_dp_clk_landing` WNEG1, W177 for
7N and W46 for7S/0N/0S. Metadata nominal three cycles cannot replace an actual
negative-edge-writer/receiver-clock phase join.
