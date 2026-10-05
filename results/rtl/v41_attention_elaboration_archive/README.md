# DeepSeek V4.1 attention elaboration archive (historical)

Verbatim files from the standalone Codex repo `/tmp/ds-attention-elaboration`
(commits 93454e9a, 615a4986, a1497002, f5beeba6; HEAD f5beeba) that never
reached OpenTallas. Ported by `claude/w0-codex-reconcile`. Paths inside are
relative to that repo; nothing here is wired into the OpenTallas build.

- `ATTENTION_COMPILE_PLAN.md`, `plan/`, `probe-*/`, `control-cadence/`,
  `control_stubs.sv`, `tb_attention_cadence.sv`, `tools/v41_attention_*`,
  `tools/run_attention_cadence.py`: bounded full-shape attention compile
  failures (Verilator OOM at 8 GiB on the top) and a stubbed-arithmetic cadence
  probe. Superseded for the successful compile by 8ceefd23 (full geometry V4.1
  attention numerics); the failures are negative evidence.
- `PV_TWO_WORD_PROPOSAL.md`, `pv-bank-lifetime*.json`, `tb_pv_bank_lifetime.sv`,
  `tools/v41_pv_bank_lifetime.py`: exhaustive proof that the proposed two-word
  PV loader needs four stationary banks, not three (95609580 states the
  requirement without this proof).
- `WINDOW_NUMERIC_INTEGRATION.md`, `ot_v41_window_numeric_bridge.sv`,
  `tools/export_window_numeric_blocks.py`, `window-numeric-inputs/`: prepared
  (never run) WINDOW-source-to-numeric-engine bridge and real input blocks.

The two archived tests pass in place:
`cd results/rtl/v41_attention_elaboration_archive && python3 -m pytest -q -p no:cacheprovider --rootdir=. tests`
(5 passed at port time). The full-geometry vectors of that repo are already in
OpenTallas via 8ceefd23 and are not duplicated here.
