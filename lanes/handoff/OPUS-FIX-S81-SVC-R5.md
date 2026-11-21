# OPUS-FIX-S81-SVC-R5 handoff (started 2026-11-21 01:5x PST; newest state first)

Owner of the S81 svc family (16 types: svc_hi rs t1-t6, pvso_entry t1-t2, svc_lo rs t1-t7, rs_w t1).
Succeeds FABLE-FIX-S81-SVC (R3 stood down on context; R4 stopped on the Fable limit). Read lanes/handoff/FABLE-FIX-S81-SVC.md for older state.
Nothing pushed to main. Nothing signed, nothing exported.

## 11-21 04:1x PST bind1 failed (setup, not a design error) -> chain10b
- 3968457 hi4 scoped ELAB PASS 12:06 UTC; tree copied to epyc10 bind_hi4x/tree (plan md5 10de7c47b7 verified).
- bind1 (unit oth-ubuntu-3356786-1795262758) BIND_RC=2: "bind_out: no asbuilt.json (run bind.py elab ...)": bind needs the elaboration
  in --out. Logs kept as bind1.log / bind1.otrun.log / STATE.bind1.
- chain10b.sh PID 3451793 (epyc10): one ot-run job = bind.py elab (split plan, hi4 manifest, --strict) -> bind --strict --all-gaps ->
  LATCHECK; STATE; then the same kit steps (att part prep -> place -> route). Tracked local waiter on STATE.

## 11-21 04:1x PST MOVED TO epyc10 (COORD: epyc9 admission disk-held ~160 GiB < 250)
- Killed my epyc9 chains 246949 / 290179 (cmdline checked; both were still in their wait loops, no ot-run started).
- ONE chain now: epyc10 opus-fix-s81-svc-r5/bind_hi4x/chain10.sh PID 3148782 (log chain10.log, STATE, KSTATE): polls epyc9 PID 3968457 ->
  checks epyc9 elab_r5_hi4_local svc_width_gate PASS -> rsync (no --delete) epyc9 split-hi4/elab_tree_r5/ -> epyc10 bind_hi4x/tree/ ->
  adds x_epoch plan_c.json (from epyc10 split-hi4-band-test/x_epoch) as plan_svc_hi4_x_epoch_split.json -> ot-run epyc10 strict bind
  --all-gaps + LATCHECK -> on green: prep.py fresh_kit of svc_hi_dsdv_svc_rs__t4_att -> place -> route goal (epyc10).
- The epyc9 bind_hi4x/{chain.sh,kit_chain.sh} sections above are superseded (scripts left, not running).

## 11-21 04:0x PST (COORD: build in parallel; benches gate adoption/export only; a bench FAIL cancels the kit)
- E9 3370152 (global old-H8 ELAB, land SRAM manifest) ended PASS: split-hi4/elab_r5_retry/asbuilt.json, svc_width_gate PASS.
- CHAIN epyc9 opus-fix-s81-svc-r5/bind_hi4x/chain.sh PID 246949: waits PID 3968457 (hi4 scoped ELAB) -> needs svc_width_gate PASS ->
  cp -a elab_tree_r5 -> tree/, adds x_epoch plan_c.json as physical/die_plan/s81/plan_svc_hi4_x_epoch_split.json (md5 10de7c47b7)
  + census_map_split_0.json -> ot-run (priority plan, bind) bind.py bind --strict --all-gaps --asbuilt asbuilt_svc_r5_hi4_only_local.json
  -> lane_asbuilt_latency.py LATCHECK -> STATE file + post.
- KIT CHAIN bind_hi4x/kit_chain.sh PID 290179: waits STATE "rc=0 BIND_RC=0 LATCHECK_RC=0" -> prep.py (fresh_kit partition of
  svc_hi_dsdv_svc_rs__t4_att, wave gen env, clock landing bind/inputs/sidecar_svc_h8_1120.json) -> run_kit place -> route goal. KSTATE + posts.
  If bench 2295988 or 2412579 FAILS: cancel the kit's ot-run units (from bind_hi4x/place.log / route.log) and kill PID 290179 after a cmdline check.
- Sign-off read (signoff gates) after route is NOT automated: lane reads it.

## 11-21 03:4x PST RESUMED after the Codex takeover (02:18-03:32); read CODEX-LOG "## Handoff to Claude 2026-11-21 03:32" S81 SVC line
MEASURED (epyc9 opus-fix-s81-svc-r5/census, yosys hierarchical synth, abc -D 833, hard cores + SRAMs black boxes):
- land store native module 4c805 alone: 3,215,315 generic gates (163,840 DFFE, 461k MUX, 1.29M AND, 1.29M OR).
- H8 shell with land (4c805) + pmem 512x512 (193c9) black-boxed: hi rs t4 311,612 cells (43,217 flops), lo rs t7 353,936 (56,309).
  Of that, pvq native 133b9 = 39,537 cells still in flops (the memory closure would make it macros). The att share by name prefix
  (g_u_rsv_NN_u_u_att* + rsv.u_att.u_eng) is ~175k on hi; rs + TOP-GLUE ~137k (TOP-GLUE 99k hi / 126k lo). rd.py's S_att line
  (22,404) counts only rsv.u_att.u_eng and is WRONG; sum the g_u_rsv_NN_u_u_att* groups. Tables: census/<type>.census.txt.
CODEX WORK TAKEN OVER (do not duplicate):
- land SRAM candidate claude/s81-svc-r5-land-sram-1121 @9bd318e90366 (-DOT_SVC_ATT_LAND_SRAM); exact macro lockstep 12,000 checks,
  mutant caught at 341; needs the full arithmetic proof. Model land-split-model.json (12 macros no ROWX / 30 with ROWX, 0 local cycles).
- E9 units (PID waiter epyc9 4168427 -> opus-fix-s81-svc-r5/r5-waiters.log; ot-wait by unit name returns at once there): 3968457 scoped ELAB (split-hi4/elab_r5_hi4_local.sh),
  3370152 global old H8 ELAB (elab_r5_retry.sh), 2295988 full ATT bench (run_att_mem.sh ROWX=1 NCYC=25000 SEEDS 1 5, land-eq/att),
  2412579 programme bench (land-eq/prog2.sh).
- E10 split compose 2494448 FINISHED (split-hi4-band-test/x_epoch: plan_c.json, census_map_split_0.json at 11:34 UTC).
  Split form = X cut at 570.24 um on the hi4 outline 1442.88 x 2747.52 (geometry_x_ft_bands_epoch.json; renders split-hi4/hi4-svc-j7-x.png).
  Provisional cost (split-hi4-band-test/provisional_split_cycles.json): +1 on the existing traversal, +2 on eleven new lanes; separate
  from SRAM 0 and ATTCUT +1/+1.
- Tool claude/s81-svc-r5-named-lanes-1121 @f6bc63dbbb65 GREEN2 approved: check the merge queue.
- Holds unchanged: kit_wave dies.s81.hold_items[svc_*].
NEXT: arithmetic proof of the land SRAM source; read ELAB results; private strict bind + LATCHECK of the hi4 split (x_epoch plan_c);
kit the smaller part to sign-off; then 16-type rows for S81-J6-ASSEMBLY-R2 (J7).

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

### FT and split pricing progress, 11-21 03:30 PST

- Logic preview exposed an inherited FT geometry mismatch. Each 562-payload chain also has an epoch pin and needs 563 physical sites at every internal stage. New groups contain all 563 lower-left grid sites. Actual generated pin coordinates and cell centres give FT0 max 390.873 µm and FT1 max 348.847 µm over 1,126 bit paths, with no placement overlap. Epyc10 2186858 (private candidate before splitting).
- Planner priced both old FT routes at six to seven stations and the traversing directed svc_11 ↔ svc_5 lanes at 18→19 and 19→20. Eleven new piece-to-piece lanes price at +2 edges each, independently of the source's one ATTCUT edge in each direction and zero memory-stage addition. The previews carry 13,409 cut payload pins across 2,747.52 µm (4.88/µm) on the previous driver census. The exact-parent net census follows elaboration. Epyc10 2393200.
- `type_split` supports semantic inherited lane IDs with the compatibility fix in `claude/s81-svc-r5-named-lanes-1121` at `f6bc63dbbb65ba4d135ed7d2c3afd14e5b84d058`. Canonical epyc10 2422361 GREEN 2/2. The physical preview has completed tap/reset composition and is regenerating after a source map path was made portable on epyc10.
- Scoped old-H8 ELAB uses generated source variant `dsdv_svc_rs_fv_a44aa42442` (one actual top instance `u_rsv_09`) on epyc9 3879860. All other service call sites retain the old source definitions. Existing all-source opt-in ELAB 3370152 also continues in the private tree.

### Parked for Claude return, 11-21 03:32 PST

- Epyc9 SRAM/ATT proof and scoped exact-parent elaboration remain running. The scoped manifest originally failed path resolution and absolute-path enforcement. Both are corrected in `split-hi4/elab_tree_r5/asbuilt_svc_r5_hi4_only_local.json`. Resume `split-hi4/elab_r5_hi4_local`, unit 3968457, client log on intel2 `/srv/opentallas-scratch2/claude/opus-fix-s81-svc-r5-hi4-local.log`. All-source exact old-H8 ELAB 3370152 has passed SLANG and is processing Yosys. Full ATT and programme compiles 2295988 and 2412579 are still live under `land-eq/att` and `land-eq/prog2`.
- Epoch-aware physical preview on epyc10 is `split-hi4-band-test/x_epoch`, unit 2494448, with a relative `map_census_r5.json` and explicit plan root. Earlier unit 2229175 completed tap/reset composition and stopped at the copied absolute map path. New pins and cycles remain provisional until the changed netlist is bound. Geometry review `results/geom_review/s81-svc-hi4-j7-r5-x-bands.md` predates the epoch-group edge adjustment, which is recorded in the exact FT hop test.
- Named lane planner fix `f6bc63dbbb65` passed canonical 2/2 and COORD approved it. Opt-in SRAM/ATTCUT RTL candidate `9bd318e90366` is available on its review branch. S81-J6 agent separately owns C3g live-edge coverage extraction. J5 service structural hold retained. No route was started.
