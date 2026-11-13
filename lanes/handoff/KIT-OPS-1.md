# KIT-OPS-1 handoff (kit-wave operations lane; COORD is the coordinator) -- 2026-11-12 17:45 PST

## Tasks (in order)
1. KV re-kit on vN2 (main 66e6607e3f0e, train 20). IN PROGRESS.
2. HEAD re-kit on rp18 once train 21 (claude/head-96-rp18-1112@7bf527a804) shows MERGED. NOT STARTED (waits MERGED).
3. SRC-INCOMPLETE epyc7 qwen_compute (kw45/src_qc_s28_88018018ef + kw45/qcs28in absent on epyc7). NOT STARTED.
4. PLAN-CORE-NOT-IN-ONLY log event on branch claude/kit-ops-1-1112 (+ test), READY, not live. CODE DONE, tests running.

## Work dirs (epyc8)
- /srv/opentallas-scratch2/claude/kit-ops-1 (real dir): repo = my own clone (hub:OpenTallas, --reference kw45/repo);
  wt = my sparse worktree on branch claude/kit-ops-1-1112 (tools/autopilot, tools/die_plan, physical/common_flow).
- mk_src.sh -> kw45/src_kv_main_66e6607e3f = pure git archive of main 66e6607e3f0e (recipe of kw45/mk_main_only.sh).
- tests.sh -> branch_tests.txt / base_tests.txt (test_kit_wave* + test_autopilot*, -n 8, venv wt/venv60).
- Scratch helpers (localhost): /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/kitops/ (post.sh, handoff.sh).

## KV findings so far
- Wave KV is still on vF (event28w_c, dkv98/vF/plan_c.json, src kw45/src_kv_main_40e22dd1d2, bind dkv98/bind_vF2): the train-9 vN event was never armed in the wave.
- bind_vN2i (epyc8 dkv99/bind_vN2i/out) names HDL sources inside epyc8 wt/die-kv-99-e (a lane worktree, epyc8 only) and
  composed_rtl that was moved to dkv99/bind_vN2i/composed_rtl_moved, so it cannot serve other gen hosts as is.
  Plan: strict bind of the same vN2i plan on the staged main src (same command as dkv99/bind_e.sh), check RC 0 and rtl/ identical
  to bind_vN2i, mirror src + bind to every KV gen host (epyc7/8/9/2/intel1).
- main 66e6607 lacks the grtm-kv overlay 5796e77ff0 (KV core kits OT_GRT_TRANSITION_MODE) that src_kv_main_40e22dd1d2 carried;
  no KV core row sets that env, so a pure main src is used.
- Holds to settle at the switch: kv3_hg*/kv3_hgi*/kv3_hg_v1p* say "releases on the vN/vN2 switch"; KV-VN2-FIN 17:13 says hg/hgi build
  after GEOM-VIS-7's verdict on the vN2 drawing.

## Rules
- kit_wave.json edits only on intel2 under autopilot/kit_wave.lock (fcntl), with a backup, committed with coord-commit.sh, verified on origin.
- Never delete; never sync into a link/overlay tree (find -type l first); real dirs only; git -C only on my own clone/worktree.
