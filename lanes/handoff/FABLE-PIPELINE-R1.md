# FABLE-PIPELINE-R1 handoff (Fable) -- own memory across context compression

Task (OWNER via COORD 11-21 20:1x): one dependency-driven command plan -> sign-off: tools/autopilot/ot-build DIE TYPE --plan P [--tree T].
Input-hash stamps per derived artefact, staleness detection, automatic R8 refresh from bound depths, early consistency checks.
Added scope (COORD 20:3x): incremental bind -- (1) per-type bind input hash, re-bind only changed types, die checks on merged result;
(2) seconds-fast pre-check before elab (plan keys vs schema, row modules in RTL, landing depths vs station counts, taps in outline);
(3) binds on least-loaded host. Measure before/after on one real QC or KV row change.
Steps: 1 design post (DONE 20:3x), 2 land small steps via ot-push-main with tests, 3 prove e2e on one real type of a live family lane
(ask first, passing bind), 4 kit_wave wave rows use it. Report COORD <250 words at design / each landing / proven.

Peers: FLOW-PRIVSPEC-R1 (private-spec --tree/--bind-out/--rt, run-item --goal; LANDED, in rt/current), FLOW-TREEFORK-R1 (tools/fleet/ot-tree-fork, landed),
FLOW-OPS-1300 (drain, push tests).

## Landed on main (push recipe below)
- 11fc581363 bind_emit_par + Binder._emit_one + build_graph ; a593d9b734 ot-build (ot_build.py bind stage / plan-overlay, ot_build_hub.py DIE TYPE)
- 035f8e7d6b kit_wave.py auto_rebind hook (die option auto_bind, default OFF) + ot_build_hub.wave_rebind ; fff2e6eaf2 alias/memo fix
- 0092847a58 counters summed (`add` op, COUNTER_RE names), pick_host skips draining hosts (disk < 250 GB), realpath plan paths
Push recipe: edit scratchpad fp/*.py (local tests: python3 -m pytest fp/test_*.py) -> scp to intel2 .../FABLE-PIPELINE-R1/tmp -> script (see scratchpad fp_c5.sh):
fetch warm repo, git rebase refs/remotes/origin/main, cp into clone, venv pytest (exit status; do NOT set OT_BIND_EMIT_J for test_ot_build*), git add explicit paths,
commit (trailer Fable 5.2), nohup python3 -I rt/current/tools/fleet/ot-push-main > tmp/pushN.log. rt/<sha12> syncs to hosts in ~2 min.

## Measurements (KV D27d3 sealed tree kw45/src_kv_pin_eb1e73448bd0_hg15_48b92c30_t4e46a7ec_d27d3, plan_c 48b92c30, epyc8 load ~0.6/cpu)
- BEFORE serial (my phase-timed baseline, epyc8 kvbase/, out kvbase/out): elab 649 s cold (88-130 s warm), strict bind 4087 s = head 108 + regen 16 + emit 3646 (one core) ; LATCHECK 3 s.
  KV-PLAN-R6 portable bind same inputs: 4567 s total.
- ot-build nodes: pre 34-48 s, elab 88-130 s, r8 (head + table check) 127-148 s (KV table fresh).
- Parallel emit J=8: all 56 types emitted in 704 s (vs 3646 s), worker private mem ~6 GB each (parent 8 GB) -> ot-run --mem ~ 8 + 6*J (+margin; used 110).
  Run 1 (kvob/b_55caed3292c4, plan unchanged) and run 2 (kvob/b_103ca094a86c, delta1 one-row plan) FELL BACK to serial (safe): (1) self.pc.B alias +
  clock_landings._physical_clock_plan memo -> fixed fff2e6eaf2; (2) self.pc.stats['cells_emitted'] counter -> fixed 0092847a58.
  Run 3 = kvob/par3.sh (delta1 plan, rt 0092847a5866), client log intel2 tmp/kvpar3.log, waiter b8csqb5k0. If it merges: diff -r its rtl vs b_103ca094a86c/rtl
  (same plan, serial fallback) = byte-identity proof; report timings as AFTER.
- Row change = kvob/delta1 (plan-overlay of plan_of_record, kv3_io_cor_v1 reset.bank_taps row 0 {'tap':1,'sinks':['u_ft_ft4_o_4']} dropped).

## E2E (COORD said YES 21:1x: kv3_io_cor_v1 on sealed D27d3, outputs in my lane dir, sign-off counts; post result + every ot-build defect)
- Running from intel2: python3 -I rt/fff2e6eaf2fb/tools/autopilot/ot-build qwen_kvsys kv3_io_cor_v1 --tree <d27d3> --lane FABLE-PIPELINE-R1 --rt fff2e6eaf2fb --host epyc2 --emit-j 8 --bind-mem 110
  log intel2 /srv/opentallas-scratch2/claude/FABLE-PIPELINE-R1/tmp/e2e1.log ; bind out epyc2 /srv/opentallas-scratch2/claude/FABLE-PIPELINE-R1/ot-build/qwen_kvsys/<tree>/b_10566ab423ec
  (this bind also falls back to serial ~70 min, then private-spec + run-item --goal finish + auto_export enqueue; kit stamp dir ~/coord/autopilot/private_specs/FABLE-PIPELINE-R1/ot-build/qwen_kvsys_kv3_io_cor_v1).
  If the hub process dies: rerun the same command (bind FRESH by stamps, kit reruns).
- Defects so far: D1 host pick ignored draining hosts (fixed), D2 parallel emit unsafe forms on KV (2 fixed), D3 scratch alias path (fixed).

## Open
- Step B (per-type emit reuse keyed on type inputs) not started; kit-level per-type reuse exists (kit stamp = type block + bound RTL + plan rest).
- auto_bind is OFF for every die; to turn on: kit_wave_edit dies.<die>.auto_bind true (COORD decision) after the e2e proof.
- R8 pre-check: no exact plan-only invariant (bound == lane cycles holds for 48% of KV members); staleness decided by r8 node (head ~2 min KV).
- Report COORD <250 words when proven.
