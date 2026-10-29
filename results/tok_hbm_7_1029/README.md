# TOK-HBM-7 2026-10-29: IDX multirow row clear vs actual reader round trip (169/171 price)

Question (Codex packet codex_tokens_hbm_to_claude_20261029_0204, ABI.md "combined row boundary OPEN"): the actual bound
reader (VM_RT 171 SW/SE/NE, 173 NW; donor 2) shifts every query/scorer field of the compiled IDX frame by vm_rt, but
ot_hnx_idxq_qctl issues row_start (query seen-clear) on the launch edge. Row r+1 clear must land after row r last head emit.

Estimate (tools/hbm_next/idx_row_pitch_price.py, row_pitch_price.json; 6 rows, 8 INDEX N6 records a pass from a122 census):

| case | frame | class pitch | pitch, clear at launch | pitch, clear delayed D=vm_rt-2 | extra edges a pass |
|---|---|---|---|---|---|
| rt171 vp1 | 1566 | 328 | 381 | 328 | 2,120 -> 0 |
| rt173 vp1 | 1568 | 328 | 383 | 328 | 2,200 -> 0 |
| rt171 vp2 | 1695 | 346 | 510 | 346 | 6,560 -> 0 |
| rt173 vp2 | 1697 | 346 | 512 | 346 | 6,640 -> 0 |

Class pitch = OPR/QEM/KEY/PRE/LIN/LOUT exclusive, SEL per selector (row mod 4), scorer one-query G2MIN 23. Donor (rt2)
drain is never binding (328/346). So the 169/171 delta costs 53..166 edges a row boundary if paid in pitch, 0 if the clear
is delayed by D = bound vm_rt - 2 (the same shift the compiler gives the query tile, so the query core sees the donor-relative
timeline exactly).

Structural fix (opt-in): ot_hnx_idxq_qctl parameter ROW_CLEAR_DELAY (default 0 = unchanged: rcl = rs, no flops). D>0: one
pending clear (W-bit counter + pend), second row_start while pending = FAULT.

RTL check (rtl_rowclear/, intel2 ot-run unit oth-ubuntu-2263228-1793266569, Verilator 5.050, 833 ps, actual compiled frame
rt173 vp1 1568 words in the frame SRAM, N=6, pitch 328): qctl D0 vs D171 lockstep, every non-clear output equal for 3,444
edges, 192 emits, 1,026 key beats, no calendar fault. Delayed clears 501/829/1157/1485/1813 each after previous row last
emit (384/712/...) and before first query slot + 173; clear-at-launch violates the drain on all 5 rows (330 vs 384).
Controls: +DMUT (compare D-1) caught at edge 172; pitch 327 -> calendar collision fault at edge 681 (328 is the RTL minimum).

Not claimed: query-core numeric multirow run (needs reader+query+scorer composition), bind of D per quadrant (one programme,
common vm_rt), source/manifest adoption.
