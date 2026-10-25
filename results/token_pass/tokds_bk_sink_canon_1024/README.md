# TOK-DS: S81 BK addressed-drain sink made canonical (2026-10-24)

COORD ruling 2026-10-24 18:55 PDT: the BK drain / slice-CTL namespace collision is a functional bug; the addressed-drain sink
(`ot_dsdv_vstop` / `dsdv_bk_g` `BK_DRAIN_SINK=1`) is canonical. Branch `claude/tok-ds-1024`:

- `rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bk_g.sv`: `BK_DRAIN_SINK` default 1. The bind and profile set no override, so the
  default is the die value. 0 is the retired transparent-forwarding behaviour, kept only to reproduce old records.
  The S81 bk tiles (bk_sel / bk_col kits) must be re-kitted from this RTL (S81 lane).
- Compiler (`tools/s81_dv/dv_layer_compile.py row_ctl_events`): a V-S calendar row whose CTL template is an addressed BK
  drain (payload [7:0] = u_bk_sel uid 0x5B, [10:8] = op 1) produces no slice or line CTL arrival. It is recorded as one
  internal `BKDRAIN` event at u_bk_sel.vi_n, with `ctl_at` = its landing edge.
- Expectations: `lower_bk` layer bench and `tb_dsdv_bk_wrap`: the drain is consumed, not forwarded. The legacy record is
  available under `OT_BK_LEGACY_FWD=1` / `+define+OT_DSDV_BK_LEGACY_FWD` on default-0 RTL.
- Replay: the `--bk-drain-sink` expectation filter is removed from `dv_cut_replay.py` and `run_entry_replay.py`. The earlier
  candidate record `results/token_pass/tokds_bk_layers_1024` used that flag; it stays as an old record.

Verilator 5.050. All runs on epyc3 via ot-run. Run root: `/srv/opentallas-scratch/claude/tok-ds/`.

## 1. BK unit benches + lower_bk layer-job bench (`tools/s81_dv/tokfunc/fc31/bk_verify.sh`, `bk_verify.json`)

| run | RTL | expectation | sel m0 / m1-m4 | col m0 / m1, m3, m4 / m2 | layer L2/L14/L20 topk_local+final | layer mutants (L2, corrupt+early x local+final) |
|---|---|---|---|---|---|---|
| canon | sink (a1cd3dec06) | canonical | PASS / all FAIL | PASS / FAIL / PASS | 6/6 PASS, 0 mismatches | 4/4 FAIL (3..148 mismatches) |
| legacy (old record) | main 9721734fee (sink 0) | legacy forwarding | PASS / all FAIL | PASS / FAIL / PASS | 6/6 PASS | 4/4 FAIL |
| cross 1 | legacy RTL | canonical | FAIL | FAIL | L2 2/2 FAIL (1 extra beat = forwarded drain 0x14c2b600801 at edge 6570) | - |
| cross 2 | sink RTL | legacy | FAIL | FAIL | L2 2/2 FAIL (missing drain beat at edge 6570) | - |

- Layer-job windows (ncyc): topk_local 17,398 edges (L2/L14) and 33,782 (L20); topk_final 6,851 / 6,836 / 6,993.
- The canonical expectation has 72 beats per job and legacy has 73: the drain beat is the only difference.
- Collector mutant 2 (dsdv_bk_v: a single drops type/tag) is not reached by the collector bench, under both the canonical and
  legacy expectations. The column unit carries frame words only, so this is a property of the bench and not a sink
  regression. The selector bench catches m2.
- The cross controls show that the expectation flip is visible in both directions: the benches detect exactly the drain
  beat.

## 2. fc31 HOST cut layer control, canonical, no expectation filter (`canon_layers.sh`, `canon_layers.json`)

Steps: recompile L0/L2/L14/L20 on tree_fc31 with the sink-aware compiler, run `prepare_split_control.py`, then
`run_entry_replay.py` on the BK-sink cut_3S_ctl build (`codex-s81/bk_drain_layer/out/obj`), jobs 0 and 1, and the
calendar-length mutant hf_7N_l0 bit 33. Run dir: `fc31c2/`.

| layer | verdict | job0 checks / mism / layer cycles | job1 checks / mism / layer cycles | CTL events job0/job1 (old) | line W/E | mutant |
|---|---|---|---|---|---|---|
| L0 | PASS_CUT_COMPONENT | 849 / 0 / 10,447 | 41 / 0 / 238 | 122/5 (122/5) | PASS | CAUGHT (10) |
| L2 | PASS_CUT_COMPONENT | 847 / 0 / 21,605 | 41 / 0 / 238 | 122/5 (127/11) | PASS (94/94 job0) | CAUGHT (10) |
| L14 | PASS_CUT_COMPONENT | 847 / 0 / 21,636 | 73 / 0 / 2,119 | 122/9 (127/15) | PASS | CAUGHT (18) |
| L20 | PASS_CUT_COMPONENT | 847 / 0 / 24,473 | 41 / 0 / 238 | 122/5 (127/11) | PASS | CAUGHT (10) |

- All jobs have 0 faults, 0 unencoded events and 1 internal BKDRAIN event (L2/L14/L20). On L0 nothing changed.
- Scope: this checks native job control on the HOST cut only. It makes no claim about arithmetic or a full layer.
- `layer_cycles` is the replay window of each job, not a stage latency.

## Tests

- `tools/s81_dv/test_dv_cut_replay.py`: ALL PASS.
- `tools/s81_dv/test_dv_layer_compile.py`: PASS (L0 compile 65 ops); both tests on a9064fa84c.
