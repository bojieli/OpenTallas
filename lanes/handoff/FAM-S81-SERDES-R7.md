# FAM-S81-SERDES-R7 handoff (2026-11-21 19:0x -> 21:4x PST; STAND-DOWN -> FAM-S81-SERDES-R8)
Read also: lanes/handoff/FAM-S81-SERDES-R6.md, lanes/posts/FAM-S81-SERDES-R7.md (all results), COORD messages 11-21 ~20:xx (dec keep ruling; t4 split ruling).
Client logs: intel2 ~/fam-s81-serdes-r7/*.client.log. Lane dir epyc9 /srv/opentallas-scratch2/claude/fam-s81-serdes-r7.
Lane clone epyc9 /srv/opentallas-scratch2/claude/fam-s81-serdes-r7-core = main 5aab47bd4b + branch claude/s81-bm-keep-th-1121 b4d98fc16875 (NOT pushed; dec_r7k builds from it as /src: do not switch it while dec_r7k runs; push from another worktree). Untracked copies there: physical/fam_views/ot_s81_kp4_dchn, physical/ref_tile/s81fam_kp4_decc (from epyc7 fam-s81-serdes-core), route_core_r7.sh.

## 1. Decoder (ot_s81_kp4_dec_lp_core) - TOP PRIORITY
- dec_j6c: official routed LEC NOT EQUIVALENT (33 pts, gold-only slang key th[11][10]); NOT exported, superseded.
- Fix = (* keep *) on th[] in rtl/dsrom_sys/s81_link/ot_s81_kp4_bm.sv. Official LEC (rt 2c3fa5fd9727) on dec_r7k SYNTH netlist = EQUIVALENT 30241/30241 (epyc9 fam-s81-serdes-r7/lec_synth_r7k/lec).
- dec_r7k route: intel2 ot-run PID 2907958 / unit oth-ubuntu-1620888-1795318810; epyc9 fam-s81-serdes-r7/build/dec_r7k(.log/.exit, work/orfs). In GRT at 21:39. Waiter: re-arm `ot-wait 2907958`.
- Then: signoff exactly as dec_j6c (R6 14:30 post: signoff.py name s81fam_kp4_decc, explicit matching TC_LIB_FILES 5 std + 3 macro libs per corner; Codex kit intel2 fam-s81-serdes-build/dec_j6c_export_stage_1415/signoff_exact) -> official routed LEC: lec kit = copy of lec_synth_r7k (config.mk + src) with net/6_final.v from dec_r7k; `python3 -I <rt>/tools/die_plan/lec.py KIT --netlist KIT/net/6_final.v --out KIT/lec --jobs 8 --mem 32 --image openroad/orfs:asap7lock` via ot-run --stage <rt>. EQUIVALENT -> ot-push-main the keep commit -> ref_tile export (python3 tools/ref_tile/ref_tile.py export --orfs-dir .../work/orfs --kit physical/ref_tile/s81fam_kp4_decc --out views/...) -> confirm AUTO-EXPORT row.
- Root cause posted to FLOW-OPS-1300 (lec.py slang element naming + yosys alias name thq[1]).

## 2. J8 rows (gated, posted 21:4x to S81-J6-ASSEMBLY-R5)
- Combined plan (J7eL6 + 6 serdes START ops + 31 PHY/ENG ops) sha dc29277503f6: strict bind RC0, LATCHECK 873/873. G0 + PRE were still running at stand-down inside the gate_j8s.sh run (intel2 chain PID 423422; epyc9 gates/J8s/g0.log, pre.out; client ~/fam-s81-serdes-r7/j8s_gate3.client.log). Post the G0/PRE verdict. The chained gate_j8p.sh run (j8p_gate2.client.log) will exit 10 (EXPECTED_OLD mismatch) because a cancelled earlier J8p run left the J8p plan in the tree: harmless, the J8s run above IS the combined gate.
- Tree candJ8s = plain copy of sealed J7eL6 (ref_tile small files only, --max-size 20m).

## 3. t4 (COORD ruling 11-21 ~20:xx): unsplit FAILED sign-off (TT -199.68, FF -138.04, DRC 4, 444k) -> split is the only path.
- Need J8 rows for S81-J6-ASSEMBLY-R5 by the 16:00 cut: S1 split (R6 epyc10 fam-s81-serdes-r6/rows/layout_t4.json + gen_split_delta.py; dec at [1075.68,388.8] R0) leaves PMA->dec p_d legs up to 1304 um (544 pins, median 649). COORD: move/rotate the decoder hard core next to the PMA (pre-approved) or add stations on those legs. Fix front3 shell AM hold -762 ps structurally (lockup / hold-buffer rows), not settings. Codex front3 work: intel2 fam-s81-serdes-build/dec_front3_flp_1415, front3_shell_reference_1415 (j7el6_shell_preflight_1415). NOT STARTED by me.
- Struct stop s81|serdes__t4|bf6905ce91d07 still set; keep it until split rows land.

## 4. PHY corner leg (phy__t1) - now this family
- Plan rows are in the J8 combined gate above (phy_eng_pair + eng view). Next: private-spec s81 phy__t1 --plan <candJ8s plan_j8p.json> --tree candJ8s --bind-out <candJ8s native_bind/out> --host epyc9 --src-manifest off (proof), diff config.mk vs wave kit, run-item, route. epyc9 is now an s81 gen host.

## 5. t12/t14/t16: ride the J8 START rows (COORD). t12 a4 / t16 a4 wave running, t14 a5 ENQUEUED. Codex t14 private fixes are ODB move chains incl. reset copies (not a positions-only overlay).

## RESUMED 21:4x (COORD: no stand-down; R7 continues)
- J8 combined plan G0/PRE: PRE PASS; G0 FAIL 10 errors (dfi__svc_14__phy_hbm hop 924 um, 2 cuts, 6 monitor cland hops, reset msg). Base-vs-J8 G0 diff running (intel2 PID 4174329, epyc9 gates/G0base) to tell inherited from new.
- phy__t1 private kit: spec ~/coord/autopilot/private_specs/FAM-S81-SERDES-R7/s81_phy__t1_1121214212, run-item intel2 PID 3945510 (log ~/fam-s81-serdes-r7/phy_t1_runitem.log), host epyc9, plan = combined J8 (candJ8s).
- t4 front3 path (stations on the PMA->dec legs, 0 cycles): worktree epyc9 /srv/opentallas-scratch2/claude/fam-s81-serdes-r7-f3 branch claude/s81-serdes-rx-front3-1121 (764fbb8bb2 keep-th + 191a63ac2d RX_FRONT3 RTL from Codex rx_shell_j7_proof_1415 / r6-push overlays). Child kit physical/ref_tile/s81fam_kp4_dec_front3 (untracked copy). Child build decf3_r7a: intel2 PID 4138606, out epyc9 fam-s81-serdes-r7/build/decf3_r7a.
- J8 t4 rows generator: epyc9 fam-s81-serdes-r7/gen_split_front3_delta.py (R6 gen_split_delta + extra_defines [OT_S81_SERDES_RX_FRONT3] + dec module override + core_taps). Hold fix = early core taps (kind core) at u_core.u_dec.ck [1439.1,777.6] (insertion from decf3 view insertion.json boundary means) and u_core.u_enc.clk [842.44,599.96] (enchp_j6b TT 270.6 / FF 223.8 boundary means). Layout file to write once the decf3 view exists.

## 11-22 02:4x (after the weekly limit)
- PUSHED main: 132f74ad819 keep-th (RiBM), a8ade98de24 RX_FRONT3 opt-in RTL.
- dec_r7k (epyc9 fam-s81-serdes-r7/build/dec_r7k): routed LEC EQUIVALENT 28726/28726 (lec_route_r7k/lec_routed/lec.json). Sign-off (signoff_r7k.sh, kit build/dec_r7k/signoff_kit = orfs config.mk with /work/src paths + macro TC libs + hooks + src copies) NOT SIGNED only on 1 internal FF hold endpoint -0.13 ps. eco_loop hold ECO: eco_r7k6 (intel2 PID 3865065). Kit-adapter fixes: hooks/ and qwen_die_masters/common_flow/ref_tile tcl copied under signoff_kit/src with /src->/work/src, OT_MM_SETUP_CORNER=tc, OT_PRD_OBS_ALLOW=M6=2 (stn_pin_keepout). After PASS: LEC the ECO 6_final.v (same lec_route kit form), then ref_tile export.
- J8: 6 serdes START ops READY alone (posted). PHY/ENG: plan_j8p3 = J8 + phy_eng_pair_delta(31) + eng_view_lib_delta + eng_ft_regs_fix.json(2) + phy_seam_shift.json(7). Gate gates/J8p3 (intel2 PID 1615013). Then rerun phy__t1 private kit on candJ8s (spec copy of s81_phy__t1_1121214212) -- previous GRT-0116 NE corner hotspot.
- t4 front3: decf3_r7a routed EXIT 0; sign-off signoff_f3.sh (intel2 PID 1537550, rt 6d2e187f0d65). Rows: gen_split_front3_delta.py + layout (dec module ot_s81_kp4_dec_lp_core_front3, extra_defines OT_S81_SERDES_RX_FRONT3, core_taps for u_core.u_dec / u_core.u_enc).
- R8 exists (Codex-side?) and owns t12/t14/t16 per my RESUMED post.

## 06:1x
- dec_r7k CLOSED: hold ECO broke TT (-89 on CMEM->bsrc); not exported; superseded by front3 decf3_r7a (R8 owns t4 front3 rows + export).
- PHY/ENG rows READY in lanes/handoff/FAM-S81-SERDES-R7-j8-phy-eng (J8p3 gate clean). phy__t1 J8p3 kit: GRT ovf 42 (was 225), GRT-0116 NE corner. J8p4 = + macro x -0.012 (phy_macro_grid.json); kit run-item intel2 PID 1801800 (log ~/fam-s81-serdes-r7/phy_t1_j8p4_runitem.log, spec s81_phy__t1_1122061135). candJ8s tree plan = J8p4 now.

## 17:3x RESUMED
- Pin generator already exists on main (tools/s81_dv/phy_pin_track_form.py, 4103cdee09; LEF physical/asap7_memory_macros_v2/ot_hbm3e_phy_v41x_aw30_e8p5_k_track1117). The plan never adopted it. phy_lef_track.json (1 op: phy__t1 contents/0/lef -> track1117, origin 77.76) is in lanes/handoff/FAM-S81-SERDES-R7-j8-phy-eng (R8 relayed it to R5). It supersedes phy_macro_grid.json.
- J8p4 kit stopped (superseded). J8p5 gate: epyc9 copy = intel2 ot-run 589061 (gate_j8p5.log); epyc8/intel1 copy = ot-run 3741517 (dir .../fam-s81-serdes-r7/j8p5gate, gate_j8p5b.log). First to start wins, the other is killed.
- Next: private-spec phy__t1 on J8p5 (tree = candJ8s on the winning host, --rt-floor-exempt as before), --goal route.
