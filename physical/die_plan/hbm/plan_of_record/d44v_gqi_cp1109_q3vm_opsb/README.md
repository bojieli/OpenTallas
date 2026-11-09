# d44v_gqi_cp1109_q3vm_opsb: counter plan d44v_gqi_cp1109_q3vm + event opsbpins_1109

DIE-HBM-97/COUNT, 2026-11-09, for COUNT-ARCHIVE-2 (14:21 ANSWER (2): the opsb_PS2f_eco1/i1 resign_gd record fails
DESIGN-MATCH; the routed pins lack the 9 plan pins lwa[375..383], 1443/1452). Same mechanism as d44v_gqi_cp1109 and
d44v_gqi_cp1109_q3vm.

`die_plan.json.gz` = gunzip of `../d44v_gqi_cp1109_q3vm/die_plan.json.gz` (sha256 ecf9d3126dc155eb...) with exactly
2 `hard_cores[].pins_file` fields changed, plus the top-level `note`:
- `partition_types.q_b113.hard_cores[u_sfucore_Q_opstore_b__o].pins_file`
- `partition_types.q_b113__physical_v1.hard_cores[u_sfucore_Q_opstore_b__o].pins_file`

both `cores/ot_hgi_sfu_opsb_output__760.32x280.8__ev74_tall.json` (sha256 3379bbf2f6a796ee..., 1461 rows; the same
file as in d44v and in the wave plan p11) -> `cores/ot_hgi_sfu_opsb_output__760.32x280.8__ev74_tall__lwa375.json`
(sha256 68eaa7f152b1f25d..., 1452 rows). The new table is the old one minus the 9 rows lwa[375]..lwa[383]
(M4, x 760.224, y 173.736..174.504). Every other row is identical and in the same order. It is byte-equal to the table
of the wave-plan event opsbpins_1109 (intel1 `/srv/opentallas-scratch2/claude/die-hbm-97/plan_p12_opsbpins`, base p11).

Why the pins can go (evidence in `opsbpins_1109_event.json`):
- Core: the signed kit's face shell drops these 9 bits as unread (face_shell.json `dropped`). The routed core has
  input [374:0] lwa and ties the core port to {9'd0, lwa}. The core RTL (ot_hgi_su_lgroup2_wp, WP=3) reads lwa only as
  lwa[g*24 +: 15].
- Parent (bind_F5c q_b113 and q_b113__physical_v1): the bits come from the store_b cmd3 register, and the parent reads
  them itself in its own fault term |cmd3_Q[383:375] && cmd6_Q[15] (static_operand_store.sv:67). That load stays in
  the parent. Only the unread core-input load goes away.
- Plan: no lane and no core_conns entry names lwa of this core, so no lane, station or crossing changes.

`cores/` = byte copies of `../d44v_gqi_cp1109_q3vm/cores` plus the new table (gzip -n). `clock_entries.json.gz` is a
byte copy of the q3vm one.

## Dry counter (COUNT-ARCHIVE-2 method)

The live `~/coord/tools/release_tree_plan.py` (unchanged), store mode, HBM line only, hub tags, G0C skipped
(intel1 `/srv/opentallas-scratch2/claude/die-hbm-97/count_smk/work/out/`, run D):
base d44v_gqi_cp1109_q3vm 79/107 (= live 14:00) -> this plan 80/107. Added ot_hgi_sfu_opsb_output (resign_gd
fd43ebd7684b, flow-20261109-gd-hbm, DESIGN-MATCH pins from routed_def). 0 dropped.
