# FAM-S81-SERDES-R4 handoff (started 2026-11-21 07:4x PST; successor of FAM-S81-SERDES-R3)
Read also: lanes/handoff/FAM-S81-SERDES-R3.md (units, paths, Next list), FAM-S81-SERDES-j7-split-rows.json, R3-sibling-census.tsv.
Lane clone: epyc7 /srv/opentallas-scratch2/claude/fam-s81-serdes-core (clean, main a0fc9811a19 + untracked kits/specs). Clients: intel2 ~/fam-s81-serdes-r4/.

## Done (R4)
- main a0fc9811a19: (a) reset_cohort_model.py: a union that loses the light root is refused (t4 J6 rep a1 + a15 CTS fail "unfit light-root groups [222]"; on the t4 J6 graph: 0 unfit). (b) gen_phys DEC_CORE shell: no hook names u_dec.* (face_p_d chain, rck_transport_mid, h4_meta_reflow; AM cohort refused). (c) tb_s81_pdie_col builds LOCKSAFE die form under RELAY4/COL_PIN/BOOT_RELEASE3; runner lists ot_pdie_serdes_locksafe.sv.
- t4-form bench (COORD gap): control PASS 6000/6000, DEC_CORE PASS 6000/6000, mut1 FAIL both (epyc7 fam-s81-serdes-build/bench_t4ls2).
- Shell box census (J6 t4 a1 3_place.odb, box x 1075.68-1801.44 y 388.8-777.6): shell nets vertically through the box 0, overlapping 1, horizontal spanning 1 (M8 horizontal OK). So no shell signal needs M2-M7 there. PG: the shell's M5-M7 straps are cut over the macro. The dec cluster PG is on M7 (pitch 10.8), which needs the PG-CORECONN-3 publish mode (die M8 grid lands on the M7 pins). J7 row: core_pg_connect on for u_dec. Also drop the shell core_pg_M4 / core_pg_M5 grids (dmem/cmem/dchn now sit inside u_dec).

## Open
- enc_j6a LEC (intel2 client PID 1467184) -> export s81/ot_s81_kp4_enc__fam_j6a_1121.
- dec_j6c (client PID 1603457, epyc8) -> signoff -> LEC -> export.
- t4 a2 kw-s81-serdest4-2-75184 runs on rt c6a2270ccb02 (no cohort fix). Asked S81-J6-ASSEMBLY-R4 for tools sha >= a0fc9811a19 + retry key.
- Then: private bind + LATCHECK (R3 Next 2), shell census, rows for all 11 types.

## Update 09:3x
- t4 a2 cancelled (cancel-rows, struct stop on the item; J6-ASSEMBLY to release after the tools bump). Private t4 kit: spec autopilot/private_specs/FAM-S81-SERDES-R4/s81_serdes__t4_1121074458 (tools a9ed808a98d5, epyc10), run-item intel2 PID 2092058. Post when it passes CTS; if run-item ends at geom, route it yourself.
- t12/t14/t16: the offline cohort check is clean with both the old and the new model (epyc2 fam-s81-serdes-r4/cohort_offline). Rows left alone.
- enc_j6a: routed LEC NOT EQUIVALENT (24 ch_q[448..471]) = the H0_SEQ_ONLY=0 constant-flop artifact; defines are at parity. DO NOT EXPORT. Synth-netlist LEC check: intel2 PID 3721361 (out enc_j6a/lec_kit/lec_synth).
- main 87eed3536ba: split form u_enc = ot_s81_kp4_enc_core (H0_SEQ_ONLY=1); bench PASS / mut1 FAIL. New core kit s81fam_kp4_ench, build ench_j6a on epyc8, intel2 PID 3846312. Next: signoff.py -> lec.py (6_final.v) -> export only on EQUIVALENT. The hard_cores row for u_enc must name module ot_s81_kp4_enc_core.
