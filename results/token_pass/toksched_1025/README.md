# TOK-SCHED 2026-10-25: ROM cycle changes in the static schedules and the accepted-cost ledger

Analytical composition, not a token run. Exact commands: `rom_ledger_cmds.sh`.

| change | design | cycles on the token | tok/s before -> after | loss |
|---|---|---:|---|---:|
| (a) S81 vsw LR=1 (+1 SW/SWR output edge) | s81 | AR +40, MTP +50 (map) / +48 (DAG) | AR 784.9 -> 784.9; MTP 2749.4 -> 2749.3 | 0.003 % |
| (b) QC MIF=1 vmr/btab/prog (+2 serial edges a SU command) | qwen_rom | +866 (+1 edge bound: +433) | 4186.9 -> 4174.2 (bound-current QC composition) | 0.301 % (0.151 %) |
| (c) KV v3.9r 839 lanes + L663 | qwen_rom | +263 priced (6 x 36 + 47); bracket +1739 | 4810.9 -> 4805.9 (ledger DAG) | 0.105 % (bracket 0.692 %) |

- (a) Codex 841db2c43 is on main as c967be25c. compose_tok_ds re-run on main 05f9f5c69 reproduces it exactly. The L14 layer_schedule goes 28081.9 -> 28082.9.
- (b) This re-runs Codex's `results/uarch/qwen_s8_crom_price_1025` recipe. Its +3 point reproduces 288025, so the bound-current base is the one of record (286726). The token price stays HELD.
- (c) L663 (host FDI) adds 0 token cycles: it is a boot/admission lane, and the token-path DAG has no host node. The interior attention lanes are not priced, because their hardened equalisation budgets absorb them. `kv_v39r/kv_v39r_price.json` gives the serial bracket.

Ledger after these rows: s81 accepted 3.502 % (+ proposed 6.349 % = 9.851 %); qwen_rom accepted 1.471 % (+ proposed 7.121 % = 8.592 %); both within 15 %.
