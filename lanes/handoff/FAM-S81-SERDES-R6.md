# FAM-S81-SERDES-R6 handoff (started 2026-11-21 11:1x PST, successor of FAM-S81-SERDES-R5)
Read also: lanes/handoff/FAM-S81-SERDES-R5.md (layouts, sibling notes), lanes/posts/FAM-S81-SERDES-R6.md.
Client logs: intel2 ~/fam-s81-serdes-r6/*.client.log. Builds: epyc8/epyc7 /srv/opentallas-scratch2/claude/fam-s81-serdes-build/<label>.
Lane clone epyc7 /srv/opentallas-scratch2/claude/fam-s81-serdes-core is checked out DETACHED at 87eed3536ba (builds use it as /src: never switch it while a build runs; push from a worktree, e.g. epyc7 fam-s81-serdes-r6-push).

## Done
- ENCODER SIGNED: enchp_j6b (ot_s81_kp4_enc_core, route over-constraint 740): TT +25.72, int FF hold 0, DRC 0, LEC EQUIVALENT 6879/6879. AUTO-EXPORT s81/ot_s81_kp4_enc_core__ax_767ee407a6. View pack (lef/libs): epyc8 fam-s81-serdes-build/views/ot_s81_kp4_enc_core__fam_j6b_1121.
- encla_j6c (kit s81fam_kp4_encla = ench + define OT_S81_KP4_ENC_LA, look-ahead CRC loop, 0 cycles, epyc7): SIGNED TT +56.9; LEC on epyc7 (intel2 PID 3473805, kit encla_j6c/lec_kit with -DOT_S81_KP4_ENC_LA). Backup / structural fix if more margin needed.
- LA bench fix on main 58c3be2128 (REF define-off; mutants now FAIL). Bench PASS 9/9.
- t12@3 / t14@4 E2BIG retries (kit_wave_edit c134dd299bd). t14 relaunched a5 (wave). t12 did not relaunch -> private wave-env kit, spec ~/coord/autopilot/private_specs/FAM-S81-SERDES-R6/s81_serdes__t12_1121125656 (run-item intel2 PID 3560718, log ~/fam-s81-serdes-r6/t12_runitem.log); run-item stops at geom: then route via run_kit.sh GOAL=route (as R5 did for t4).
- ECO track on ench_j6a stopped (not needed); its dirs deleted.

## Codex 14:23-18:1x (adopted; CODEX-LOG.md ~14207, lane posts 14:19-18:08)
- dec_j6c SIGNED minimal (Codex signoff_exact: TT +14.15, int FF 0, DRC 0) under intel2 fam-s81-serdes-build/dec_j6c_export_stage_1415/. Routed LEC first run NOT EQ (33 BM tail points, naming); OFFICIAL retry rt a87de12be91a = intel2 ot-run PID 2433138 / unit 2434187, out dec_j6c_export_stage_1415/lec_a87de12be91a -> the gate. private_tail_split_1415 (unit 2645858) uses a MODIFIED lec.py = diagnostic only. Export dec only on official EQUIVALENT (stage view with ref_tile export, then bind S1).
- S1 split geometry HELD (PMA->dec 544 pins max 1304 um; RXNEG shell stage cannot split). Alternative = front3 child (alt RTL from private overlays on 58c3be2128): dec_front3_flp_1415, front3_shell_reference_1415; child TT +44.80/FF +17.79 at 795 ps diag; shell AM hold -762; all-Q unit 2949360 running. Needs RTL on main + fresh child view + shell link before any route/sign-off.
- t4 UNSPLIT private kit (E10, oth-ubuntu-293099-1795284746) in DRT: final GRT setup ws +99, scoped hold +7.09 viol 0, broad hold -150 (ports), 444k cells. If it signs -> LEC -> export; t4 then needs no split.
- t14 a5 (wave, E8) in FF GRT; Codex private t14_a5_geom_only_1415 geometry fixes. t12 private FT5 +1 geometry/LAT only. t16 needs boot W7 native proof.
- PHY corner leg (729 um to k_wstrb) is NOT serdes family (phy type) - confirm owner with COORD.

## Live
| what | unit/pid | next |
|---|---|---|
| dec_j6c (epyc8) | intel2 PID 1603457 | GRT hold chunks -> DRT -> EXIT; then signoff.py (name s81fam_kp4_decc; ot-run --dir B --stage rt/current/tools) -> LEC (lec_kit like enc: config from dec kit, top ot_s81_kp4_dec_lp_core) -> view export (python3 tools/ref_tile/ref_tile.py export, no -I) -> lef2pins |
| t4 private kit route | oth-ubuntu-293099-1795284746 | GRT/route/signoff; tell S81-J6-ASSEMBLY-R4 to release struct stop bf6905ce91d07 when it ends |
| t12 private kit | intel2 PID 3560718 | geom -> route |
| t14 a5, t16 a3 (wave) | kw-s81-serdest14-5-89674, kw-s81-serdest16-3-88184 | run by themselves |

## Private bind (epyc10 /srv/opentallas-scratch2/claude/fam-s81-serdes-r6)
- candS1 = hardlinked copy of s81-j6/candJ7c (BIND/LATCHECK/PRE PASS) with a FRESH native_bind/out (5 inputs ln'd), RTL overlays (col/ot_pdie_serdes_col.sv main, lp/ot_s81_kp4_dec_lp_core.sv, ot_s81_kp4_enc_core.sv) and rows/split_t4_delta.json applied (apply_delta.sh; gen_split_delta.py + rows/layout_t4.json).
- enc view installed: physical/die_plan/s81/results/fam_s81_serdes_r6/enc_j6b/*, inputs/core_pins/kp4_enc_core_216_pins.json (scratch lef2pins.py).
- MISSING: dec view files at results/fam_s81_serdes_r6/dec_j6c/ot_s81_kp4_dec_lp_core{.lef,_tt.lib} + inputs/core_pins/kp4_dec_lp_core_726x389_pins.json.
- Then: bash gate.sh candS1 S1 (bind strict -> LATCHECK -> G0 vs candJ7c -> PRE) via ot-run on epyc10.
