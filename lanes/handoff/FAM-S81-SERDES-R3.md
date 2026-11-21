# FAM-S81-SERDES-R3 handoff (stand-down 2026-11-21 ~07:2x PST, COORD: context; successor FAM-S81-SERDES-R4)
Read also: lanes/handoff/FAM-S81-SERDES-R2.md, FAM-S81-SERDES-j7-split-rows.json, FAM-S81-SERDES-R3-sibling-census.tsv, lanes/posts/FAM-S81-SERDES-R3.md.
Lane clone (git, commits): epyc7 /srv/opentallas-scratch2/claude/fam-s81-serdes-core (mirror without git on epyc8, same path; rsync kits/specs epyc7 -> epyc8 before launching).
Build out: /srv/opentallas-scratch2/claude/fam-s81-serdes-build/<label>{/,.exit} (epyc8; enc_j6a also copied to epyc2 + epyc7). Clients: intel2 ~/fam-s81-serdes-r3/*.client.log. Every ot-run has OT_LANE=FAM-S81-SERDES-R3 and self-posts DONE/DIED.

## Units running at stand-down (handed to R4; do not cancel)
| what | unit | intel2 client PID | next |
|---|---|---|---|
| enc_j6a post-route LEC (tools/die_plan/lec.py on enc_j6a/lec_kit, gold RTL vs 6_final.v, out enc_j6a/lec_kit/lec_final, epyc7) | oth-ubuntu-2838510-1795274014 | 1467184 | exit 0 = EQUIVALENT -> export enc_j6a (AGIdock + rtx-pro, standard export, name s81/ot_s81_kp4_enc__fam_j6a_1121); 1/2 -> read lec_final |
| dec_j6c: kit s81fam_kp4_decc = cluster, signals M2-M7, dchn as hard child, dmem/cmem macros, 725.76x388.8, no die hold budget (epyc8) | oth-ubuntu-3823626-1795274482 | 1603457 | on EXIT=0: signoff.py run --run-dir B/work/orfs --kit B/work/orfs --sdc B/signoff.sdc --name s81fam_kp4_decc --out B/signoff --corners tt,ff; CTS post-hook only |
| t4 J6 rep (kit_wave) | kw-s81-serdest4-1-63632 | - | stage geom at 07:0x; at CTS read 4_1_cts.log cohort line (group 222 unfit = reset-cohort row, not a retry) |
| t12 / t14 / t16 J6 a1 (kit_wave) | kw-s81-serdest12-1-66906 / kw-s81-serdest14-1-66906 / kw-s81-serdest16-1-66898 | - | in place |
| old rt SUPERSEDED-KEEP: t15cla21 a7, t15cla3d a5, t1clb45 a7, t1clfe a9 (ENQUEUED/geom), t13 a7 (place) | kit_wave rows | - | keep; a false PLACE-SETUP-STOP -> retry item@N:fix=eda19506a55 |
Localhost waiters of this lane (kwwait.sh, ot-wait ssh) die with the session; R4 re-arms its own.

## Done
- Enc core SIGNED: enc_j6a (kit s81fam_kp4_enc, pd 0.3, relief 30) signoff.py minimal: DRC 0, ant 0, TT +29.23 ps at 833.0, internal FF hold 0 violators (complete census), boundary rst_n -30.13 advisory. Signoff record: epyc2 + epyc7 copies enc_j6a/signoff/signoff.json (the epyc8 copy has no signoff dir: epyc8 scratch2 was at the 50 GB floor at that point).
- encb_j6b (reference env pd 0.5 relief 0): minimal SIGNED but achieved period 859.79 ps (TT -26.79), so NOT used. It is evidence that the env-parity kit closes too (COORD ruling d442c09bb6e). enc view = enc_j6a.
- dec_j6a DIED PDN-0233 (dchn PG pins are M5; fixed in the spec with pg_layer M5). dec_j6b (leaf M6) DIED GRT-0116: 8 gcells at the dchn interior clk/rst pin (x 356-359, y 108-113), the same as FABLE-RCK-RX vC, fixed there with M7. The leaf contract forbids M7, hence the dec_j6c cluster.
- RTL on main @22c4c3c5837: OT_S81_SERDES_DEC_CORE (col u_dec = ot_s81_kp4_dec_lp_core, ck -> 4 region clocks, wiring only, 0 cycles). Test tools/die_plan/test_serdes_dec_core.py; bench default/DEC_CORE PASS 6000/6000, mut1 FAIL.
- Sibling census (lanes/handoff/FAM-S81-SERDES-R3-sibling-census.tsv): all 11 serdes types share the form; the dec box fits under the PMA rx in every type; shell est 87k-183k kit cells (< 400k).
- COORD env ruling: core kits diffed vs svc hslice_mm3r (closest signed S81 core); the wave-only vars are absent from the ref_tile flow. Declared deltas: pin_regs/reset_landing off (0 cycles), group_max 1 pin balance, dec macros/layers. The SHELL kit must use the serdes__t4 wave env + gen args exactly (kit_wave dir s81_serdes__t4_bf6905ce91d07/a1/spec.json); diff config.mk before launch.

## Next (R4)
1. enc LEC -> export. dec_j6c -> signoff -> LEC -> export.
2. Private strict bind + LATCHECK tree on epyc10 (pattern s81-j6/mk_cand.sh + rows/svc/elab.sh + gate.sh): base J6 tree src_s81_pin_3c913dbdfb23_d8j6_1117_work plan_h2_2249.json; t4 delta = +define OT_S81_SERDES_DEC_CORE, hard_cores = [u_core.u_dec (ot_s81_kp4_dec_lp_core, origin [1075.68, 388.8] R0, so the in-core dchn lands on the old dchn site), u_core.u_enc (ot_s81_kp4_enc, place near u_ptx / tx path)], drop the u_core.u_dec.u_chn row and the two SRAM physical_parts (now inside the dec); manifest: add lp/ot_s81_kp4_dec_lp_core.sv to the sources; the tools rt must be >= 22c4c3c5837.
3. Shell kit census (< 400k) from the bound tree; gen_phys.txl_mid_exports RXPIPE/RCK4 chains name u_dec.u_face_p_d / u_dec.u_rck_transport4 (inside the hard core now): expect a gen fix.
4. Rows to S81-J6-ASSEMBLY-R3 for J7 + update j7-split-rows json (dec 725.76x388.8 cluster M7, enc 216x216 M5).
