# d44v_gqi_cp1109_q3vm: counter plan d44v_gqi_cp1109 + event P-Q3VM-2 (q3_vm pin table)

HBM-CORES-B, 2026-11-09, per COORD ruling to HBM-CORES-B ("post a READY that adds the q3vm pin table to the counter
overlay, the same way as corepins_1109, EQ-gated: table == signed kit pins.json"). For COUNT-ARCHIVE-2.

Made with the tool already on main, `physical/die_plan/hbm/delta_q3vm_e_1108.py` (event P-Q3VM-2, e6da5ab8039),
run unchanged with `--expect-rd-sha b2c55e78` on a base dir assembled from main:
- `die_plan.json` = gunzip of `../d44v_gqi_cp1109/die_plan.json.gz` (sha256 74ed22ba7fd0ee4f...)
- `clock_entries.json` = gunzip of `../d44v/clock_entries.json.gz` (sha256 92669babc64eb493...)
- old table `cores/ot_hfd_coll_q3_vm_core__328.32x717.12__canon__fr15__codex_g21__centry.json` = gunzip of the
  `../d44v/cores/` copy (sha256 3eccb9f38cef89f8...), the table d44v_gqi_cp1109 resolves today.

Changed against d44v_gqi_cp1109 (leaf diff, nothing else):
- `partition_types.q_hub_nw.hard_cores[u_hb_coll_Q_vm__q0].pins_file` -> `cores/ot_hfd_coll_q3_vm_core__328.32x717.12__canon__fr15__codex_g21__centry__q3vmE.json`
- `partition_types.q_hub_nw.clock.taps[u_hb_coll_Q_vm__q0].xy` (1218.24, 393.12) -> (1218.24, 535.68), and its `note`
- top-level `note` extended
- `clock_entries.json.gz` (new in this dir; d44v copy with one entry changed): `q_hub_nw.u_hb_coll_Q_vm`
  xy_um (164.16, 358.56) -> (164.16, 501.12), island_um follows, source extended.

New table: 2049 of 9200 pins differ from the old one (vmasm_rd_il x2048 N/M5 -> E/M4 x 328.224; clk (164.184, 358.56)
-> (164.184, 501.12)). PIN CYCLES 0, internal stations 0, outlines and every other type unchanged.

`cores/` = byte copies of d44v_gqi_cp1109/cores (gqi8, RF4T, vC5) plus the new q3vmE table. Other tables resolve
through hbm/cores as for d44v_gqi_cp1109.

## EQ gate (table == signed kit pins.json)

`tools/q3vm_kit_eq.py KIT_PINS TABLE` converts the kit pins with the corepins_1109 rule (core_pin_event.py
`to_plan`: face pins inset 0.096 um toward the interior, entry pins unchanged) and compares by name.
Kit: q3vm_vF signed kit pins.json, sha256 5bfbfe10c6906371c371e131539e2d9c4c34395d8c583bf9c7f4e77ae4bcb594
(epyc7 /srv/opentallas-scratch2/claude/hbm-cores-b/q3vm_vF_eco1/i1/pins.json; mirror epyc4). Result
(`q3vm_kit_eq.txt`): 9200 names on both sides, same set, 0 differences (layer, x, y, w, h). The q3vm_vF re-sign
on flow-20261109-gq-hbm (LEC EQUIVALENT) used this kit.
