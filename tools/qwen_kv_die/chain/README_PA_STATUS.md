# Physical preflight and constant straps

`run_case.sh` records the container's raw result in `<log>.process_exit`, then
validates the log with `case_status.py`. `<log>.exit`, the shell return value,
and `<log>.status.json` carry the effective result. A caught OpenROAD error
therefore cannot pass because OpenROAD returned zero or a final timestamp
command succeeded. Real cases require zero overlaps/outside placements,
`OT_ASSERT PASS`, and `OT_PA DONE`; PDN cases require both VDD and VSS grid
checks, and new tie-cell M1 pins must contact literal same-net special rail
metal before those grid checks. Error messages and failure markers take precedence over success
markers. `die_chain.sh` also validates retained logs before resuming.

The immutable C15 failure is recorded in `testdata/constants/c15_failure.json`:
its real placement and track checks passed, but unmapped Verilog straps became
implicit POWER `one_` / GROUND `zero_` nets and PA rejected them with DRT-0305.

Fresh real-case generation copies `physical/common_flow/die_constant_cells.tcl`
into the case and runs it after macro placement. It uses actual ASAP7
TIEHIx1/H and TIELOx1/L cells, repairs fanout per load, places only the tie cells in legal row gaps using a
sparse obstacle cache, binds their actual VDD/VSS pins, and checks that no hard macro moved.
No full-die standard-cell placement grid is allocated. A missing legal gap
fails rather than leaving a cell unplaced. No power net is reclassified as signal and no PA error is suppressed. The
mapped tie outputs are ordinary signal nets; the supply nets remain special.

This mapping explicitly emits `OT_CONST PG_OPEN`. New tie cells require real
M1 supply rails and upconnect in the die PDN; the existing M8/M9-only core grid
does not establish their power connectivity. The shared
`die_constant_pg_check.tcl` guard checks actual transformed PG pin geometry
against actual M1 special-wire metal; complete grid connectivity is then
checked normally. Missing rails fail closed. PA success is a preflight result.
Actual PDN connectivity, timing, native die integration and throughput remain
separate required qualifications. The tiny real OpenROAD regression checks
mapping and PA behavior, not full-die power closure.

Run the focused regression with:

```sh
python3 -m unittest discover -s tools/qwen_kv_die/chain -p test_case_status.py -v
```
