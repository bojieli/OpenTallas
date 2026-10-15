# Per-pair die hop check (2026-10-13)

The die statement evaluated for every connected pair of placed instances with each side's real view numbers
(`tools/hier_contract/pair_check.py`, runner `pinreg_pairs.py`, tests `test_pair_check.py`). Text: `el1013-pinreg-audit.log` 13:35.

| file | what |
|---|---|
| `view_timing.json` | timing table of the 68 die masters that have a real view (O, S at TT; l, h at FF; measured R per clock pin; forwarded clock arcs). Input of the generators' hop gates (`pair_check.Gate`, `$OT_PAIR_TIMING` overrides). Rebuild: `pinreg_pairs.py table --masters s81_masters.json --out view_timing.json`, then `--masters qwen_rom_tp8_masters.json --merge view_timing.json`. |
| `s81.{json,md}` | S81 v15 run 5 (`s81_v15_plan.json.gz` = `tools/s81/c5diag_v15_dump.py`, branch claude/el1011-s81dieit + overlay 4e241d57f+3c64383dc). |
| `qwen_rom_tp8.{json,md}` | Qwen tp8b a1 (`qwen_rom_tp8_plan.json.gz` = `tools/qwen_tp8/pairs_plan_dump.py` on the relay generator of claude/qwen-tp8-relay-data-1013, r8 a1 source). |
| `*_token.json` | uses per token of an added stage, per bus class, with its source. |
| `insertion_measured_1013.json` | the 35 views whose `insertion.json` was measured today from the closed archive (routed ODB + SPEF). |
| `s81_v15_pair_gate.json` | `hop_gate.json` of `dsrom_s81_fulldie.py real` (v15 opts) with the per-pair gate: FAIL, 402,553 bits over their pair limit, 6 forwarded hold races. |
| `qwen_rom_tp8_pair_gate.json` | the relay generator's release gate with the per-pair check (tp8b a1): 29 hops over their pair limit (the exact-bound ones), 0 hold races, direction-bound pairs listed as candidates. |

Re-run: `python3 tools/hier_contract/pinreg_pairs.py s81 --plan s81_v15_plan.json.gz --table view_timing.json --audit ../s81_takeover_reexport.json --token s81_token.json --out s81.json --md s81.md` (same for `qwen`).
Not judged here: tiles placed inside a parent (S81 collective / SU / HC / VM / P2 tiles): dump the parent in the plan format and run the same command.
