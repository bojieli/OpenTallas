# Qwen3-8B ROM TP8 die: what blocks geometry (2026-10-14, die lead)

Sources: g9 terminal `414d80093` (results/arch/qwen_tp8_1013/g9_terminal), slab window `5fa38c8e0`,
per-pin budget `8f20ee74b` (results/arch/qwen_tt_slab_window_1014/pin_budget), r10a/r10p case on ot-epyc4
/srv/opentallas-scratch/claude/qwen-tp8-die/{r10a,r10p}. Counts overlap; do not sum.
Sign-off (owner option B, restated 10-14 06:35): setup at TT, hold at FF, DRC 0. SS figures are a reported sensitivity column only, never a blocker.

**No Qwen die has reached GRT or STA.** r10a died at real-case placement (19:04:57 10-13) before PDN; there is no
overflow map and no three-corner STA. g9 is a planner-only geometry FAIL; no GRT launched on it (invalid plan).

| # | Blocker | Measured fact | Class | Element(s) | Fix (structural) | Owner |
|---|---|---|---|---|---|---|
| G1 | Legal origins | r10p: 132 OT_PLACE_FAIL: 64 qkd_ctrl_pc MY no legal non-overlapping origin, 64 qkd_rhead R180/MY x off the M6/M7 8.64 um lattice, 4 qkd_ectl | plan | qkd_ctrl_pc, qkd_rhead, qkd_ectl | snap head/ectl/PC rows to the pin-layer lattice in the generator (head x and y), re-space PC column | die lead |
| G2 | Stack registered reach | 315 hops > 500 um, all stack_local, max 2182.7 um | reach | qkd_rhead, qkd_land/astk(_n), qkd_ctrl_pc, qkd_cdc_wleaf | relay stations inside the stack corridor, stack repack so head->PC->land hops are <= reach | die lead + stack/head |
| G3 | Unrepairable relay paths | 128 (64 te + 64 ts) zero legal terminal relay sites | reach/plan | stack terminal faces | reserve relay channels in the stack plan (not BFS after the fact) | die lead |
| G4 | Cut | 0.654 > 0.60 at y14150 / x19760..20020: 2130 bits / 3257 tracks (KVN 1048, spine 563, corridor 509, reset 10) | cut | KV landing / spine / corridor | split the KVN bundle over two windows, move the corridor off the KVN window; 2-D window check | die lead |
| G5 | Face/pin access | 330 FAIL: 193 stack_local, 132 HBM_CDC, 4 spine, 1 CROM; 36,828 bits without pins | pin | stack masters, qkd_cdc_wleaf, unclosed masters | top-down pin files per unclosed master (contract v5) | die lead -> element streams |
| G6 | Reset reach | 19 > 500 um, 16 unreachable ECTL sinks | reset | qkd_ectl_*, qkd_rstseq | staged reset tree (relay per <= 438 um), ECTL sinks given a reachable reset pin | die lead |
| G7 | Slab group area | 8 groups need 2.536444 mm2 vs 1.430970 per port frame (1.77x); six frames >= 6.632845 mm2 raw deficit | area | qfd_port_tiles_{0,1,2}{,_f1} (slab groups) | re-pack/re-partition slab groups; take area from elsewhere inside the 35 mm2 reticle margin | die lead + slab |
| G8 | Column output arc | ot_qwen_slab_pg_col m5: TT launch 330-334 ps (all 256 bits; outhold BUF-HB4-BUF at every pin), FF 244-251 (SS sensitivity 492-503); cid capture TT 197-200 | pin (tile) | qfd_slab_pg_col (3 views) | output flop at the pin without the outhold chain (hold met at the die hop), or col within 231 um of its core (TT pair 331+176) | slab |
| G9 | Slab core | core_rs0 launch TT 303 ps; lane_a 3 bits 225 ps (SS sensitivity only: 1434 launch / 2216 capture bits over) | reset/pin | slab core | registered local reset release; lane_a pin flops | slab |
| G10 | Head ARG2 | TT 247/634 launch bits fail (kvd_tiles 360 ps, cmd 174 bits to 291), 104/233 capture fail (rst_n 326, ret 52 bits to 315) | pin/reset | qkd_rhead (128) | head pin-register repair + local reset sync; native HEADS1/Q_FP32 head footprint | head stream |
| G11 | Tile height | tile bound 1493.856 um > 1425.6 by 68.256 even without ctl/cache/node/TX | area | qfd_tile_nk (768) | compact RQR / bank shapes | q-tile |
| G12 | VM region seams | 8325 boundary fails / 5136 > 500 um; 32-root station geometry 26 relay conflicts; band cut 1.062967 | reach/cut | qfd_sp_vector_memory, band | equalized face stages; root stations outside the M1-M9 wall | VM |
| G13 | x-line functional gap | die broadcasts one 128-b line per root; array gives tile t line t % 512 | function | VM roots, tile ctl, stations | 32 cyclic line-indexed root streams + tile epoch cache (see x-line section of the log) | die lead |
| G14 | Placeholders | 1,078 of 2,192 non-relay instances real (r10a); 768 tiles, 128 heads, VM, SU, IO, host, land/astk, all relays are placeholders | view | see ordered queue | element queue at top of el1011-qwen-tp8.log | elements agent |
