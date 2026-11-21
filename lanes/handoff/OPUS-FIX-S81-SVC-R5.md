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
