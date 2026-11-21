# S81-BKSEL-R6 handoff (Claude Opus; successor of S81-BKSEL-R5; started 2026-11-21 06:0x PST)

## Done
- Keep edit (dsdv_bk_dsp sd/sl (* keep *)) committed c6c79db984 in epyc7 /srv/opentallas-scratch2/claude/s81-bksel-r5/repo, PUSHED main @4e2b8ec778 (push log ../push_keep_r6.log). Proof+bench rerun oth-ubuntu-1218171 rc 0, all as wanted.
- chain_r6 oth-ubuntu-1218164 rc 0: LATCHECK PASS 873/873, PRE_PASS, place 0 groups >405, STATION_FAMILIES_OVER 0, R5 left-overs gone; non-reset >300 only u_ids.vr->lo 303.4 um (COORD: no row).
- J7 rows + bind-measured lane totals handed to S81-J6-ASSEMBLY-R4: lanes/handoff/S81-BKSEL-R6-J7-rows.json (tl_o0 = 67, not 66).

## Running
- Private WAVE-ENV sign-off kit bk_sel__t2: unit oth-ubuntu-3423615-1795275718 (epyc7, hub log ~/s81-bksel-r6/sk1.otrun.log).
  W=/srv/opentallas-scratch2/claude/s81-bksel-r6/w; script sk1.sh; kit W/kit/bk_sel__t2/gen/bk_sel__t2; route log W/route_s1.log; sign-off in kit signoff*/signoff.json.
  Env = live kit_wave.json (snapshot W/kit_wave_snap.json) through the wave's spec_for (fable-fix-s81-bksel-r2/w/event_gen_spec.py); tools rt/4f62b1308b5b composed by rt_launch_tree.sh (W/launch_4f62b1308b5b); bind = chain_r6 tree_r6 native_bind/out; --src-tree/--rtl-root = tree_r6.
  config.mk vs wave a14 (224567138ab): +A3P/L4 defines (intended), +GLOBAL_ROUTE_ARGS, +LATCH-SWAP restore TCLs (newer rt), -OT_GPL_SPARSE_OVERFLOW (a14 predates FLOW-NOADV-R3: leaf-only now). Earlier tries kit_try1_rc11 (src-tree), kit_try2_rc13 ($RG literal) moved aside.
  Re-arm: ssh intel2 'export OT_LANE=<lane>; ot-wait oth-ubuntu-3423615-1795275718 --timeout 80000'.
- Gates: DRC 0, TT setup >= -42, FF hold >= 0, LEC (lec/lec.json), bind+latency (chain_r6 LATCHECK). Post-hook CTS only. Visual never blocks.
- Provenance: this kit is private (tree not src_manifest); if it signs, J7 carries the rows (manifest tree) and the wave re-signs, or rebuild from a manifest tree.
