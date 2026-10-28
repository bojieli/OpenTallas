# HEAD die, all 253 active tiles on the REAL released head.weight (TOK-ALL-14, 2026-10-27 15:50 PDT)

Vehicle: the generated native partition ot_s81hd_tile_p -> ot_s81hd_tile_native + real CV/ROM models + all 40 FT pins
(results/token_pass/head_native_1351/partition_native, unchanged), lock-step against the independent legacy reference
tile, same transformation as tools/s81_head/head_native_partition_miter.py plus +ROW0/+EXP_ROW/+EXP_BITS plusargs
(tb_native.sv here). Driver: tools/s81_head/head_native_fullweight.py (gen / build / run).

Inputs: DeepSeek-V4.1-Flash dba1be0a shard 43 head.weight (header sha256 9c6d4d66...1d54, read-only copy
intel1:/srv/opentallas-scratch2/claude/ref/DeepSeek-V4.1-Flash-dba1be0a-partial), golden ctx1048576_head.npz
(sha256 9b3502ec...4a49). Tile rows = die_plan.json id_straps strap_row0 (rank 0, 253 of 264 slots ten=1; 32,384 rows).
Images written at the closed-view skew SK 11. Self-check: tile tE3b4 (row0 21888) images + xa/xb are byte-identical to
the pinned fixture images of the Codex native run (12/12 sha256).

Result (result.json, per_tile.json): PASS_ALL_ACTIVE_TILES. 253/253 tiles emit exactly the golden argmax {row, FP32 bits}
of their 128 golden logits; GO->result 8,429 cycles on every tile (single value); 2,277,759 lock-step payload/control
checks; 45,646,260 FT scalar checks. Rank-0 argmax over the 253 RTL tile results = row 21946 bits 4173a558 = golden
(and = the golden global argmax). Controls on the same binary: wrong-ROM (tE0b0 images under the tE3b4 expectation)
CAUGHT golden mismatch; MUT_ROW caught at 509; MUT_FT caught at cycle 3.
Scope: per-tile minimum component on all real rows; per-logit values are internal to the CV views (only the tile
argmax leaves the tile), so each tile is checked on its argmax, not on all 128 logits. The die-level wavefront
(ctl/spine/chain/turn/rank merge) is composed, not simulated. 11 ten=0 slots carry no rows.
Runs: intel1 units oth-ubuntu-1605723-1793141040 (gen), -1605725-1793141040 (build), -1625582-1793141171 (run), all exit 0.
Raw: intel1:/srv/opentallas-scratch2/claude/tok14-head-fw.
