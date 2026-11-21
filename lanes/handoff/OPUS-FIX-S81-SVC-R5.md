# OPUS-FIX-S81-SVC-R5 handoff (started 2026-11-21 01:5x PST; newest state first)

Owner of the S81 svc family (16 types: svc_hi rs t1-t6, pvso_entry t1-t2, svc_lo rs t1-t7, rs_w t1).
Succeeds FABLE-FIX-S81-SVC (R3 stood down on context; R4 stopped on the Fable limit). Read lanes/handoff/FABLE-FIX-S81-SVC.md for older state.
Nothing pushed to main. Nothing signed, nothing exported.

## 11-21 02:1x PST
DONE (URGENT): kit_wave cancel-rows s81 'svc_*' (owner OPUS-FIX-S81-SVC-R5, verdict STRUCTURAL): 16 live rows had stops placed
(11 cancelled, 5 ended FAIL while the stops ran; 0 live after). Hold `dies.s81.hold_items["svc_*"] = "split pending (OPUS-FIX-S81-SVC-R5)"`
(kit_wave_edit commit a5c9d70467b). Release this hold only when J7 split rows are on the plan of record.
Not touched: census jobs (epyc9 fable-fix-s81-svc-1121/census), R2 count jobs on epyc8 (fable-fix-s81-svc-r2/count), the epyc10 chain PID 618307.

FINDING: the H8 soft shell is dominated by ONE module, `ot_bind_native_4c805a5536bda0930879099e` = the bound form of
`reg [255:0] land [0:TR-1]` (TR = 640) in dsdv_svc_att.sv line 493 (main too): a 164 kbit landing store in flops, 4 combinational read
ports (lrd[j] = land[4*(rc-1)+j]; ports 0/1 shared with the export x_s0/x_s1) and up to 12 merged write slices. It is the module all 3
census jobs sit on in abc (since 08:48-09:33 UTC). OT_SVC_ATT_MEM_MACRO (sw/wq/qmem/pbuf -> macros) does NOT cover land.
The ot_sram_1r1w_160x256_m1_r0c0 macro exists (4 x 160 = 640 rows, 256 wide = 4 row-interleaved banks, one per engine read lane).
So a split alone cannot put S_att under 400k while land is flops; J7 needs land as 4 x 160x256 SRAM banks (dsdv_svc_mem_ar style, read at
the D input of rc, 0 added cycles) PLUS the att cut.

RUNNING (mine, epyc9 /srv/opentallas-scratch2/claude/opus-fix-s81-svc-r5/census, OT_LANE set):
- land.sh: generic gate count of the land module alone (synth -noabc) -> land.gates.txt.
- census.sh svc_hi_dsdv_svc_rs__t4 / svc_lo_dsdv_svc_rs__t7: same census as FABLE's, land module black-boxed -> <type>.hier.txt / .json,
  read with `python3 -I rd.py <type>` (S_att vs rest).

## Next
1. Read the two censuses + land count; post measured S_att / S_rs / land.
2. RTL: land as 4 banked 160x256 macros (write-port and export-conflict analysis first), lock-step bench vs flop form.
3. J7 split rows (att part + rest, both < 400k, tiling the outline, lane latency declared), private bind + LATCHECK + kit to sign-off.
4. Rows to S81-J6-ASSEMBLY-R2 for J7.

### Codex takeover update, 11-21 03:15 PST

- Default-off candidate `claude/s81-svc-r5-land-sram-1121` at `9bd318e90366ad7990d4e00ba88a3474085b9275`. The source replaces the 640×256 flop landing store with 12 writer-bank SRAMs on H8 and 30 when ROWX supports two arbitrary same-bank reads. The memory consumes the existing capture edge. The optional registered attention wrapper costs one cycle in each direction.
- Exact SRAM model proof passed 12,000 directed comparisons and detected 341 priority-mutant edges on epyc9 unit 2296393. Directed integration passed six engine, ROWX old/new and idle checks on epyc9 unit 3130938 using the ATT controller and an engine interface sink. Full arithmetic ATT and cut program builds continue on 2295988 and 2412579.
- The retained H8 parent ELAB hit unknown 160×256 module on 2947558. The private manifests now declare the existing SRAM blackbox and retry runs on 3370152. No production define or plan adoption occurred.
- Hi4 seam x=570.24 µm passed the prior bound unique-wire estimate at 6,896 and 2.51/µm. The y candidate failed 8.78/µm against cap 8. The x draft initially stopped in composition because an old hbm_i0 reserve rectangle crossed the seam. The revised S_rs/S_att pack moved FT0 to y=354.24 µm with the fit under 367.05 µm between stations and kept FT1 below 324.61 µm. The first re-seat trial produced all seven bands within their own pieces and 402.84 µm reach on epyc10 unit 1981363. A second re-seat keeps the exact previous reserve-area floor and uses the new FT bank locations.
- Remaining candidate gates are exact-parent map and proof refresh, loaded clock taps, split timing/latency and geometry review. The J5 svc structural hold remains active.
