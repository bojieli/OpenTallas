# d44v_gqi_cp1109_q3vm_smk: counter plan d44v_gqi_cp1109_q3vm_opsb + the q_sm kids (event smk_1109)

DIE-HBM-97/COUNT, 2026-11-09, for COUNT-ARCHIVE-2 (14:21 ANSWER (1): ot_hbm_accel_smh_xs cannot count because the
counter plan does not list the q_sm kids). Same mechanism as d44v_gqi_cp1109 and d44v_gqi_cp1109_q3vm: one overlay dir
whose `die_plan.json.gz` is the previous counter plan with a named set of leaves changed, plus byte copies of the tables.

Built with `tools/mk_smk.py BASE P11 OUT` (in this dir):
- BASE = gunzip of `../d44v_gqi_cp1109_q3vm_opsb/die_plan.json.gz` (sha256 0150e611c6a15d09..., the merged opsb overlay;
  its 2 opsb_output pins_file leaves are kept and checked by the builder).
- P11 = the HBM wave plan p11 (die_plan sha256 2bd45422144211955d0c...; DIE-HBM-97 12:52 READY), staged at
  intel1/epyc7 `/srv/opentallas-scratch2/claude/die-hbm-97/plan_p11`. Its q_sm0..3 are the restjrev_1109 (6cc23d96)
  types, i.e. SM-ASBUILT (DIE-HBM-92 11-08 10:30 option 2), unchanged since plan_final3.

Changed against d44v_gqi_cp1109_q3vm_opsb (nothing else):
- `partition_types.q_sm0`, `q_sm1`, `q_sm2`, `q_sm3`: the keys `hard_cores`, `contents`, `cells`, `hard`, `clock`,
  `reset`, `note` are taken from p11. Every other key of these types (outline, ports, buses, ft_slots, stations, ...)
  and their 8 partitions were already equal; the builder checks that and stops otherwise.
- hard cores: 352 per type (hnx_rp3h_gn 16, gs 16, lc 96, tl 192, xs 32) -> 236 per type (smh_xs 32, smh_bdc 32,
  smh_tcl_gu 64, smh_tct 32, smh_pt_w 16, smh_pt_e 16, sm_pv_merge 32, sm_attn_be cd9/cd13 x2, cd16/cd17 x1,
  sm_attn_be_seed cd20/cd21 x1, sm_attn_pstore, sm_kv_line, ot_smh_static_front, sm_i8w_front x1).
- top-level `note` extended.
- Leaf check in the builder: 0 changed leaves outside partition_types.q_sm0..3 and /note.
- Not changed: partitions, ports, lanes, every other type, and the clock_entries / core_conns / core_macros sidecars
  (the counter does not read them; they still carry the rp3h-era q_sm entries).

`cores/` = byte copies of `../d44v_gqi_cp1109_q3vm_opsb/cores` (gqi8, RF4T, vC5, q3vmE, opsb lwa375) plus the 17 `*smab1108*` q_sm kid
tables from p11 (gzip -n; sha256 of each unzipped table in `smk_1109_event.json`). `clock_entries.json.gz` is a byte
copy of the opsb overlay's one. Other tables resolve through the earlier overlays and hbm/cores as before.

## Dry counter (COUNT-ARCHIVE-2 method), 2026-11-09 16:5x, main 687cbb1835

The live `~/coord/tools/release_tree_plan.py` (copied unchanged), store mode (store refreshed from ~/coord/signed-store
after the 16:35 ingest, 51427 records; no host read), PLANS reduced to the HBM line, tags from the hub (flow-20261109-ho-hbm
-> 538206e4c4bb), G0C skipped. Runs on intel1 `/srv/opentallas-scratch2/claude/die-hbm-97/count_smk/work/out/`.

| run | HBM plan | HBM signed designs | vs live |
|---|---|---|---|
| A2 | d44v_gqi_cp1109_q3vm_opsb (live) | 80 / 107 | = live cache 16:05 |
| B2 | this plan, store as ingested | 78 / 119 | +smh_xs (COUNT-CREDIT deadx0), +smh_pt_e; -hnx_rp3h_gn, gs, lc, tl |
| B3 | this plan, DIAGNOSTIC: the 10 missing pin tables read on intel1 | 88 / 119 | +12 kids; -4 rp3h |

B2 vs B3: 10 of the 11 ho-hbm re-sign entries (bdc, tcl_gu, tct, attn_be cd9/cd13/cd16/cd17, seed cd20/cd21, pstore)
were ingested from the epyc7 signed2 copies, whose routed_db lies only on intel1, so the store holds no pin table for
them and the counter says "pins not readable". pt_e matches through its intel1 alias (an older store pin table on the
same pins path). With the pins read from the intel1 routed DEFs (the counter's own REC_PINS_PY), all 12 DESIGN-MATCH.
