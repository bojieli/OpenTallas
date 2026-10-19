# Exact final IDX256 pickup: adoption HOLD

The exact 129.6 x 129.6 um, no-SRAM component route `hdie_col_idx256_1019-fan32g1-2727e1f68` is daemon CLOSED at 11:36:07 PT. Source `2727e1f68fe35352898f603aa751441ae447096f`; record `e5862b501d09b19f9392c466a956186ce0c88c95` has 27 files, with an automatic merge conflict on four original source/test/tool files. This collector does not merge that record or adopt the parent.

**Actual final internal PG connectivity fails:** 322 `BUFx24_ASAP7_75t_R` clock leaf buffers have both VDD and VSS disconnected in OpenDB (644 native PG MTerms). Every other 196,220 PG MTerm resolves to a net with its matching POWER/GROUND signal role. See `pg_connectivity_summary.json` for every missing native pin; `raw.json.gz` preserves the unfiltered graph. Exported child PG access lint PASS does not establish internal clock-buffer power. No free global-connect repair, gate resubmission, or claim of physical PG qualification is made.

## Routed evidence

- Final ODB SHA256 `851903b3ea016e159ac50862a1c80c5b3f4c6276e13df27789182736ce4e72c6`; SPEF `a86653e98ff953e441f905ec66347cec4a7dd5cfb453b33f3903b59a8e2c29a2`. All native/ETM metrics below use this final routed artifact, not earlier CTS geometry.
- TT setup +92.98 ps; FF hold +19.39 ps. SS sensitivity -234.40 ps, not acceptance. Routed self-reference uses actual measured clock arrival; parent compensation and neighbor matches remain unproved.
- Detailed router final DRC 0; final antenna net/pin violations 0. Final `6_finish.rpt` reports zero max-slew, max-cap, and max-fanout violations (minimum slew slack 26.6055 ps against 260 ps). Its raw route-time 174 hold checks are historical to the route constraints; final signoff FF with routed reference is +19.39 ps. Both records are retained.
- Exported face/PG lint: VDD/VSS 24 M5 stripes each, 96% spread, 100% coverage, M6 strap; 2,330 face pins with zero blocked-above/same contacts. These are exported access facts, not replacement for internal PG connectivity.

## Complete logical census and native boundary

The fresh collector exported ALL 98,432 physical instances, 76 masters, 2,332 native BTerms, 30,282 nets, every native pin connection and signal/direction role from immutable final ODB. Exact master inventories are retained. The strict `969965293` oracle adapter removes only explicitly POWER/GROUND pins and PG-only physical cells from the LOGICAL census after validating native pin inventories and roles. PG connectivity is audited separately, including those removed pins. No instance-name exclusions or pre-collapsed roots are used.

Logical graph: 30,237 cells, 30,535 drivers, 57,401 endpoints; 5,417 FF, 24,674 combinational roots, 298 input roots, 146 physical tie roots. Every BUF/INV transparency decision is proven by native Liberty Boolean function. All nonclock logical roots, including ties and inputs, have at most 32 loads; zero violations and zero virtual literals. Clock pin roles come from the actual native FF function, not net names. 255 open-output clock-loading buffers retain their physical input capacitance records in the compressed full census; open output is not a zero-load electrical claim. The five real ASAP7 libraries are independently parsed with hashes; unused FAKE bundle files are manifested but do not replace any used master.

296 nonclock data/reset inputs terminate only at FF data pins, all 2,032 outputs originate at FFs, and ETMs show no combinational data pin arcs. `clk` drives 5,417 native clock pins; `clk_in` is deliberately unused under the source's mandatory XSER=0 guard, not an unregistered data input.

Final measured TT/FF clock boundary spreads are 46.3/41.2 ps; all 5,417 FF arrivals have the same extrema. Native own-reference TT launch/capture 166.506/116.704 ps; FF 118.056/86.923 ps. FF earliest launch is 51.493 ps, maximum input hold requirement -2.001 ps. `native_etm_summary.json` records exact pins and references. This is own-clock component characterization; no parent reference was invented.

All cell boxes lie inside 2.16..127.44 um in both axes. With all external pins confined to the 129.6 um component outline, a conservative any-two-pin Manhattan bound is 259.2 um <405. This geometric upper bound does not price actual die links. The original two sampled-edge reset landing remains; no asynchronous stopped-clock assertion guarantee is claimed. Original daemon production-shaped guard bench passed 9 cases, 3,356 identity edges, 1,026 writes, four launches, 32 records, plus five causal mutant failures, unchanged calendars and all 256 configuration rows. This pickup adds no new behavior or token qualification.

## Remaining closure

ROOT must choose a source-bound clock/PG structural repair and review its actual legal contacts/physical graph before a future gate. Preserve original FAILED PG evidence. Parent ANY `prm` face assignment, NF5/native die binding, neighbor budget and composed throughput remain open. No new gate or submission was launched.

Raw export and strict replay ran through unpinned ot-run with data locality on ep7: units `oth-ubuntu-29530-1792440408` and `oth-ubuntu-30657-1792440443`, both exit 0. Collector remote root `/srv/opentallas-scratch/claude/hbm-idx-final-native-1019`; full original libs and graph remain there. `replay_native.py` is a read-only diagnostic adaptation, not production helper activation.
