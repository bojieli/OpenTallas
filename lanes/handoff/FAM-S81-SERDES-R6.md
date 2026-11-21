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

## Codex continuation after 14:15 PST

- `dec_j6c` final ODB/DEF/SPEF/netlist are on epyc8 `/srv/opentallas-scratch2/claude/fam-s81-serdes-build/dec_j6c/work/orfs`. Actual route reviewed in `results/geom_review/s81-serdes-dec-j6c-final-1121.md`. Empty detailed-route DRC and antenna logs. First STA TT load failed because the ref kit has no `TC_LIB_FILES`; separate `signoff_kit/config.mk` adds its canonical TT corner list (preserves source, original route, first STA evidence). `signoff_exact/signoff.json` SIGNED minimal 833.0 ps, TT +14.15, internal FF hold 0, DRC/ANT 0. Global FF -76.34, 759 endpoints, no per-corner vclk reference. DRV slew 34/23 and related-pair skew 369.5/275.2 ps remain for stricter review, pin-flop spread 72.24/71.85. Routed LEC private kit unit oth-ubuntu-3508924-1795299585, output `lec_kit/lec_final`. No export before exact LEC; signoff automatic export disabled.
- Keep `candS1` out of J7 adoption and route. Exact t4 PMA-to-dec pin fit review `results/geom_review/s81-serdes-t4-s1-rx-boundary.md` at 22624d3a6ad shows 415/544 bits above 400 µm and worst 1304.262 µm. A single falling-edge shell register leaves an unavoidable 652.131 µm half-cycle span. The revised cut keeps original face data/valid and AM partial capture, plus three of the four full-cycle transport stages, in the shell. It also moves three of the four reset-calendar stages out. Keep the final stage registered in the new child. Reviewed geometry estimate 90/90 µm for half cycles then at most 281.066 µm for each of four full-cycle legs using the exact current pins. New child has nine AM input pins and needs a fresh view.
- Private cut RTL and bench epyc7 `/srv/opentallas-scratch2/claude/fam-s81-serdes-build/rx_shell_j7_proof_1415`. Boundary miter extracted the existing actual face/full-transport logic and real `ot_pl_pad` and AM3 modules. PASS 992 edge comparisons across 4 epochs; data-short mutant caught 992, reset-short mutant caught 8. Full decoder miter with real behavioral SRAMs, unit oth-ubuntu-961039-1795300154 (intel2 `~/fam-s81-serdes-r6/rx_shell_full_1415.client.log`). The candidate compiles; complete output comparison pending.
- J6 t12 first private `1121125656` place was RC78 on draining epyc10. Its exact second private `1121132907` was admitted on epyc7 unit oth-ubuntu-331001-1795297977. J6 t16 a3 AP 39b76de8ddc7 also RC78 with no execution, shared recovery owned by wave. Hold unchanged t16 routing for actual START reach correction and floorplan review. Production t14 a5 AP 27b8bf5e2d1c continues on epyc8. Existing t4 private representative oth-ubuntu-293099-1795284746 on epyc10 is in GRT FF repair. Production rows and drain markers unchanged.
