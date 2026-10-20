# Token path 2026-10-18: graded composition with inter-die terms

Tool: `tools/token_compose_xdie.py` (lane TOKEN-COMPOSE). Test: `tests/test_token_compose_xdie.py`.

This is the live baseline of the token release gate (owner 10-18). Every cycle of the token is a term with one
grade, a source record and the commit that holds it. The grades rise as the TOKEN-PASS (per-layer die RTL) and
TOKEN-XDIE (multi-die co-sim) records land; the composition method itself does not change.

## Method

    T_token = sum_l n_l * C_die(l)  +  sum_l n_l * sum_x max(0, E_meas(x) - O_meas(l, x))
    tok/s   = 1.2 GHz / T_token          (MTP: per accepted token = step / tau)

- `C_die(l)`: the critical-die cycles of layer `l` without its inter-die exchanges.
- `E(x)`: the cycles of inter-die exchange `x`, from the producer's last-word issue to the consumer's first-word land,
  PHY and switch included.
- `O(l, x)`: the cycles the static schedule overlaps `x` with independent work. It is read from a schedule, never
  assumed:
  - **HBM (DS and Qwen):** the S2 compiler schedule of record (`priced_layers.py` / `static_schedule.json`, the
    schedules the HBM layer vehicle asserts against). `O` is the time a COLL record shares with any non-COLL unit
    record of the same layer.
  - **S81:** the token-path DAG solve. A critical node gets `O = 0`; a node off the critical path (slack > 0) gets
    `O = E`. No S81 die-run compiler schedule exists yet (TOKEN-PASS-S81 is BLOCKED on the DV layer vehicle).
  - **Qwen ROM:** the 10-13 die run's op-fetch window partition. The windows that "hold link" are controller stalls
    on the collective, so `O = 0`.
- A mixed exchange is split into one part per grade, and the exposed cycles are shared over the parts in proportion
  to `E`. On the HBM die, for example, a mixed exchange has three parts: transport measured on the current GEN2 RTL,
  the switch and cable modelled, and the on-die COLL stages priced.
- Grades:
  - `measured-current-RTL`: measured on the die RTL of record (10-18: d4g GEN2, S81 p4l, Qwen dv2f14 + kvs14c).
  - `measured-old-RTL`: measured in RTL on an older revision or vehicle (10-08 field phases, 10-13/14 layer runs, 10-15 KV attention service).
  - `modelled-PHY`: off-chip legs (PHY analog, FEC, switch, cable, package trace) at cited constants.
  - `priced`: analytic price only.
- **Price check (also in the test):** with every exchange at its priced `E`, the S81 and HBM terms reproduce the
  price of record exactly (`T_at_price_cycles`). The composition therefore moves away from the price only where a
  measured term replaces a priced one.

## Baseline 10-18 (existing records only)

| design | mode | composed tok/s | price of record | T cycles | % current RTL | % older RTL | % modelled PHY | % priced |
|---|---|---|---|---|---|---|---|---|
| DS ROM (S81 p4l) | AR | 1,365.7 | 1,365.7 (+0.00%) | 878,670 | 0.0 | 80.3 | 14.0 | 5.7 |
| DS ROM (S81 p4l) | MTP | 4,045.4 | 4,045.4 (+0.00%) | 1,233,698 (step, tau 4.159) | 0.0 | 84.1 | 10.9 | 4.9 |
| Qwen ROM (compute + KV + D2D) | AR | 4,767.1 | 4,810.9 (-0.91%) | 251,723 | 0.0 | 99.3 | 0.0 | 0.7 |
| HBM d4g, DeepSeek | AR | 1,993.8 | 1,905.4 (+4.64%) | 601,856 | 9.6 | 0.0 | 8.2 | 82.2 |
| HBM d4g, DeepSeek | MTP | 3,258.7 | 3,258.7 | 368,245 | 0.0 | 0.0 | 0.0 | 100.0 |
| HBM d4g, Qwen (TP8) | AR | 930.9 | 946.2 (-1.61%) | 1,289,008 | 6.9 | 0.0 | 0.1 | 93.0 |

**MU.S81.SCANCHK (10-18):** the DS ROM rows now charge the index scan at p4l's real 1 HBM stack a die (the 10-09
DAG and the p4l price charged the 10-04 4-stack reader): AR 1,243.0 -> **1,186.4**, MTP 3,806.2 -> **3,454.7**
(`results/arch/s81_scanchk_1018/`, ledger S81.SCAN_STACKS_P4L proposed).
**S81-SCAND (10-18, option D adopted, coordinator 0iq):** the full-scan keys are spread over k = 3 TP4 stages, and the
reader term is the measured 1-stack reader at the per-die key count. The legs and the merge are priced. Result:
AR **1,224.1**, MTP **3,711.7**. The ledger row is now MTP 2.76 %, within the unit limit
(`results/arch/s81_scand_1018/`).

Qwen ROM MTP is AR-only by owner decision (10-05 AR_MODE). The HBM MTP rows are priced only: the owner parked HBM
MTP (recorded, not blocking).

What moves the numbers today:
- **HBM-DS (+4.6%):**
  - Most of the gain comes from schedule overlap. The S2 schedule hides part of most gathers behind SM/SU work, so
    `O > 0`. The TOKEN-XDIE-HBM record used `O = 0` and got about 1,960 tok/s.
  - The measured transport is below the price for single-crossing gathers.
  - The measured transport is above the price for the 2-crossing o-group reduce: 1,569 against 1,326 per instance.
- **HBM-Qwen (-1.6%):** the realisable hypercube TP8 all-reduce measures 1,688 against 1,394.5 priced per
  instance. With 5 die links, the direct form is not possible, so the TP8 package topology needs a coordinator
  decision.
- **Qwen ROM (-0.9%):** the composition uses the TP4 reference-core vehicle (old RTL) plus measured KV-die
  attention (1,555 service + 65 D2D, 10-15).
  - The TP4 all-reduce windows are 2,184 cycles a layer and dominate the inter-die term.
  - The TP8 unit bench (862 cycles for 2 ARs) is evidence only, not substituted, because no TP8 layer vehicle exists.
- **S81:** every node grade comes from the 10-08 field-phase DAG. The p4l DV deltas and the ledger/hop basis are
  priced. The 10-13/14 hub-vehicle layer ratios are attached as evidence on L0, L2 and L14, with no substitution:
  that vehicle has none of the p4l masters.

## Files

- `index.json`: per design and mode: tok/s, T, banner, cycles by grade, price of record, the inputs with sha256 and commit, and the records seen.
- `<design>.json`: every term (slot, kind layer/xdie/adjust, n, cycles, grade, source{record, pointer, commit, origin}). For xdie terms it adds E, O and O_source, plus a per-layer table and an inter-die summary.
- `inputs/`: snapshots of the records that are not on main yet, each with its origin branch@commit in `index.json` `inputs`:
  - `s81_layer_price_p4l.json`: claude/tokpass-s81-1018 36e5c2683.
  - `xdie_hbm_record.json`: claude/xdie-hbm-1018 38149e70b.
  - `hbm_qwen_{price_per_layer,static_schedule}.json`: claude/tokpass-hbmq-1018 f5c3d8ba9.
  - `hbm_ds_priced_layers_all.json`: claude/tokpass-hbmds-1018 `priced_layers.py` run on ot-epyc5, 10-18, adding layers 8/20/24/28/32/36. It reproduces 629,775.1 cycles.
- Token page: `tools/fleet_viz/explorer/token/data/*.json` carry `composition_1018`. The page shows it as the top
  panel: "% of token cycles measured on current RTL", with a grade bar.

## Reviewer reproduction

```
git checkout <this commit>
python3 tools/token_compose_xdie.py --check                 # recompute from the pinned inputs: CHECK PASS
python3 -m pytest -q tests/test_token_compose_xdie.py       # price check, grading, override, outputs match
python3 tools/token_compose_xdie.py --page-data tools/fleet_viz/explorer/token/data   # rewrite outputs + page data
```

To regenerate an input from its own vehicle, use its lane's recipe. For example, the HBM-DS schedule:
`PYTHONPATH=tools python3 -m hbm_layer_vehicle.priced_layers --out X.json --layers 0,1,2,3,8,14,20,24,28,32,36,head`
on the hgi_sim bundle of claude/tokpass-hbmds-1018. The cross-die sweep: `tools/xdie_hbm_compose.py --run <run dir>`
on claude/xdie-hbm-1018.

## Override records (how the grades rise)

By default the tool reads EVERY record by discovery, with no path list (`--list-records` prints them):
every `results/rtl/*_layer_tput_*/**/*.json` (TOKEN-PASS, LAYERBENCH, LB2 per-layer layer-bench records) and every
`results/rtl/xdie_*/**/*.json` (TOKEN-XDIE, e.g. `xdie_qwen_1018/pair_r1/record.json`) that carries a `token_compose`
block, each family's top-level `record.json` (listed even without a block), and any committed `results/**/*.json` with
a block. `--pass-records` / `--xdie-records` replace discovery with exactly the given files (what-ifs). A record that
carries a `token_compose` block replaces base terms by slot:

```json
{"token_compose": {"terms": [
  {"design": "hbm_gen_ds", "workload": "ar", "slot_re": "^L3\\.die$", "cycles": 13012.0,
   "grade": "measured-current-RTL", "pointer": "layers.L3.cycles", "note": "d4g GEN2 layer vehicle, exact, 0 schedule faults"},
  {"design": "qwen_rom", "workload": "ar", "slot": "Lc.xdie.d2d_attention",
   "E": [{"grade": "measured-current-RTL", "E": 71.0}, {"grade": "modelled-PHY", "E": 9.0}], "O": 0.0,
   "O_source": "dv2f14 compiler schedule issue cycles"}]}}
```

- A term gives either `cycles` (a layer term) or `E` parts plus O_meas (an exchange). O_meas is never assumed: give
  `O` with a non-empty `O_source` naming the compiler schedule / calendar it was read from, or
  `"O_ref": {"record": "<path, repo- or record-relative; omit = this record>", "pointer": "a.b.0.c"}`. An exchange
  term without either is rejected (listed under `records_seen[].rejected`) and the base term is kept.
- Two records that replace the same slot are reported in `overrides_used[].replaces_override_from` (the later path wins). `n` defaults to
  the multiplicity of the slot it replaces.
- Slots are listed in `<design>.json` `terms[].slot`, for example `L14.die`, `L2.xdie.96x512 index TOPK_MERGE`,
  `Lc.xdie.tp_allreduce`, `L0.xdie.L0.attn.out_allreduce`.
- A record without a block is listed in `index.json` `records_seen` with `used: false`.
