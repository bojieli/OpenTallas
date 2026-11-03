# HBM plan event d44x = d44t + R8 bus latency groups (TOK-HBM-3, 2026-11-03)

Base: d44t (DIE-HBM-59/G0C FT S0 re-site, die_plan 3837d4886dad). d44x die_plan sha256 is in SHA256SUMS.
Tool: `tools/hbm_b2/r8_word_groups_event.py <d44t die_plan.json.gz> <out>` followed by
`tools/die_plan/gen.py latency <out> --inplace`. A re-run from the committed d44t gives a byte-identical die_plan.

## Why
d44t adds 1-4 stations to 34 FT lanes (+45 lane-cycles in total). I re-evaluated the bind's as-built landing groups
(`bus_groups.json` landing[], COORD R8, from the HBM bind intel1:/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/out_s11)
with the d44s and the d44t plan cycles. A group is aligned when every member keeps its as-built offset, i.e.
`cycles(lane) - asbuilt_stages` is the same for every member.
Result: 3992 groups judged (316 skipped because they name lanes that are not in d44), 81 misaligned before and 81 after.
- NEW from d44t (2): `hcb_NW1.u_c.$procdff$71842` (NW_b001) and `hcb_NE1...` (NE_b001). One register word is carried
  by L14 (1321 b), L167 (1389 b) and L168 (1386 b), all at as-built stage 0. In d44s all three lanes are 8 cycles. In d44t
  L168 is 10 and L14/L167 stay 8, so the bound word would arrive split over two cycles.
- HEALED by d44t (2): sm_NW3/sm_NW7 `g_qs_in.u_qs_c_land` (L100 7 -> 8 now equals L34/L35 8).
- Pre-existing misaligned groups (79) belong to the existing bind/R8 debt and are not changed by this event. 24 of them
  see different cycles under d44t (listed in results/token_pass/tok_hbm_3_1103/landing_delta_d44s_d44t.json).

## Change
Two R8 `bus` latency_groups, `L168_word` = [L14, L167, L168] and `L168m_word` = [L14m, L167m, L168m].
`Plan.lane_pads()` pads L14/L167 (+m) by 2, so 8 -> 10 = L168. The pad sites are the q_b001 / q_b001__physical_v1
in buses L14_i, L167_i, L167m_i. bus_pads() gives 14 sites and 0 conflicts (d44t: 10 sites, 0 conflicts).
No station, pin, window, outline, core or clock change. The landing re-check gives 79 misaligned (d44t 81): 0 new and
the 2 hcb groups fixed.

## Gates
G0 + G0C (`check.py --completeness`, the same main 7cf44d5c0 tools as the d44t numbers): 74 errors / 128 pending-view /
1178 warnings. All 1380 findings are identical to d44t [CHECKED by a set compare, g0/g0c_report_d44x.json.gz].
Latency check: 0 errors.

## Cost
+2 cycles on L14/L167 (+m), +8 lane-cycles in total, on top of d44t's +45. The tok/s price is in
results/token_pass/tok_hbm_3_1103/README.md. Tok/s loss is accepted (OWNER 12.21).
The q_b001 types gain 2 pad stages on L14_i/L167_i. HBM types are held (OWNER 11-02), so no kit is affected now.
