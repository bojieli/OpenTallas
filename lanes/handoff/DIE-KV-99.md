# DIE-KV-99 handoff (KV qwen_kvsys die owner) -- updated 2026-11-12 06:55 PST
## 1 Scope
KV vN2 hand-floorplan event (COORD rulings 11-12), on base vN2 = vN 52a724781a52 + ft_nudge class fix + census exemption + SerDes bump rects.
Items: 1 census exemption DONE; 2 pg_domain rects DONE; 3 hgi_EN_0 cut (fork); 4 hroot ASPECT EXCEPTION (decided, no edit); 5 merge 21 types (fork);
6 taps cap 1200 + hgi_v8 min 39 + clock INSERTION BALANCE (COORD 06:4x) = REACH-FIX-2 tools/die_plan/reach_fix.py at compose; 7 hg+hgi W street (fork);
8 stations out of PHY (fork DONE, see 5); 9 drawing + decision table by 11-13 12:00 PST into lanes/kv-vn2-1112/ for GEOM-VIS-5 (data DONE, see 5).
Then compose vN2 -> G0 -> strict bind -> READY. hg/hgi build to P&R only after a visual verdict.
## 2 Worktree
epyc8 /srv/opentallas-scratch2/claude/wt/die-kv-99, branch claude/kv99-taps-path-1112, HEAD ae71bf887a8f (pushed, clean). Tools tree for plan work: epyc4 /dev/shm/dkv99/main (main d767dc851b + that taps fix; physical/ = hardlinks of /dev/shm/dkv98/main/physical).
Old predecessor worktree epyc8 wt/die-kv-98 = clean checkout of 52a724781a52 (do not modify; the confirming bind reads it).
## 3 Running jobs
- epyc8 ot-heavy pid 3741564 (tag otrun-ubuntu-2558108-492613167): /srv/opentallas-scratch2/claude/dkv99/bind_exp.sh = strict bind of vN from clean checkout 52a7 (confirmation only). Result: epyc8 dkv99/bind_exp52a7.run (RC line), log dkv99/bind_exp52a7.log, out dkv99/bind_exp52a7/. Was load-gated at 06:50.
- Forks (Claude subagents of this lane; die with it): item 3 cut -> epyc4 dkv99/cut/; item 5 merge -> epyc4 dkv99/merge/ (may have an ot-run strict bind in flight); item 7 W street -> epyc4 dkv99/wstreet/. If they are gone, redo from their dir state.
## 4 Watchers
none persistent (only in-session monitors). Helper: ssh retry /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad/rs.sh (copy: epyc4 dkv99/rs.sh not present; trivial loop on ssh rc 255). Compose: epyc4 dkv99/compose3.py BASE CUR DELTA OUT [--report R] (3-way JSON, exits 2 on conflict).
## 5 Results not yet posted
- G0 baseline vN2 with main tools: epyc4 dkv99/g0_vN2b: 27 ERR (all hgi cut segments, model issue posted 07:18 FINDING), census+pg GONE. Plan dirs need a ../census link (census paths are relative): ln -s /srv/opentallas-scratch2/claude/dkv98/census <dir>/../census or put the plan dir under dkv98/.
- dedup.py apply with --bound-rtl dkv99/bound_vNb/rtl: all 11 merges GEOM-BLOCKED (bound RTL: reset-relay naming = geometry; rst_o_N/start_o_N + strap_r8pad_* = interface). Without RTL gate: 56 -> 45.
- Item 8: only sys_c moved (kv3_sys_c ft1 regs_um = window + bit-site centroids, 0 cycles), plan epyc4 dkv99/phystn/plan/plan_c.json sha256 eeed436e9cbc..., G0 0 NEW. Real count 160 street_die_leg (84 PHY = host.hbm_rst_n L668/L678/L689/L699 in phy_v1 own glue band x 432, 125 um E of the real PHY body; 71 pv macros pvg*; 5 sys_c). PHY: not moved (pc-side reroute = +1-2 boot cycles, no physical gain); proposed checker exemption prototype dkv99/phystn/patch_streets.py (not committed) -> decision COORD.
- Item 9 data: epyc4 dkv99/draw/{fill_vN2.tsv, trunk_vN2.json, README.md}: fill 47/56 measured, 0.004-0.094 (all < 0.15 exception); trunk from DIE-PROTO-3 vFk tree (epyc8 die-proto-3/kv/vFk/tree/kit/clock/tree.json); re-run trunk_x.py on die-proto-3/kv/vN tree when CHAIN_DONE.
## 6 Next steps
1. Collect fork results (cut, merge, wstreet). Each = full plan from vN2 base + G0 slot diff vs g0_vN2b (rule: 0 NEW except listed re-site items).
2. Compose order on epyc4 dkv99/vN2c: base dkv98/vN2/plan_c.json -> merge (types) -> phystn -> cut -> wstreet, each via compose3.py (rule: any conflict -> resolve by hand on that path, never -X).
3. Re-site once: landing tool + collector_reattach.py --sidecar + added_tap_recentre.py --sidecar on the wstreet resite list; then REACH-FIX-2 reach_fix.py (KV cap 1200, hgi_v8 min-taps 39, insertion balance) when READY.
4. G0 (cd /dev/shm/dkv99/main && nice python3 -I tools/die_plan/check.py PLAN --out DIR), /dev/shm/dkv98/g0_slot.py BASE NEW. Hop check <= 405 (worst 401.8).
5. Strict bind via ot-run (model: epyc8 dkv99/bind_exp.sh / epyc9 dkv98/bindj_vNb.sh). RC 0 -> plan_package.py package+verify -> branch -> READY.
6. Drawing: render die map + data flow + trunk + fill, decision table into lanes/kv-vn2-1112/ (draft 2 for GEOM-VIS-5 CHANGES 05:14 items 1-5).
## 7 Open READY/ASK
- READY 06:52 claude/kv99-taps-path-1112@ae71bf887a8f (main regression: taps.py Path) -> ROOT-MERGE-60.
- ASK 07:18 G0 core_obs model (M7 over detail-view cores) -> COORD; default at 09:00: ruled 350-b move, others carried as checker item.
- To ask: item 8 PHY checker exemption vs reroute -> COORD.
## 8 Gotchas
- epyc4 sshd drops connections under load: retry on rc 255.
- DIE-KV-98's /dev/shm/dkv98/hgex tree lacks hgclk_1030 view LEFs -> optimistic cut capacity; use dkv99/main only.
- vN2 plan's kv3_head_eighth_e2 lef is an ABSOLUTE path (/srv/.../kv-plan-2/views_e2s): fix in packaging.
- No git in /home/ubuntu/OpenTallas on intel2; no pkill.
## UPDATE 07:25 PST
- Confirming clean-checkout bind of 52a7 = RC 1 (CompositionError native_composite_hub_Eo_astk_ES). READY for 52a7 RETRACTED (queue 07:25). Fork root-causing: epyc8 dkv99/cleanbind/ (+ maybe new worktree wt/die-kv-99-cb). vN2 READY only on a clean-tree bind.
- Item 5 merge: NOT exact for any group (fork report; epyc9 dkv99/merge/bind_m RC 1, 78 err). vN2 base strict bind RC 0 on old base: epyc9 dkv99/merge/bind_a. Recommended drop from vN2.
- Item 3 cut DONE: epyc4 dkv99/cut/pkgB/plan_c.json md5 149f0939 (L2075_2 window +1036.8 um, re-site hgi_v3 ft27 + pv_v8 ft0, 0 cycles, worst hop 401.8 unchanged); G0 27 -> 27 (hgi_EN_0 gone, hgi_WN_0 unmasked). Scripts scratchpad cut_move.py / segload.py.
- core_obs coverage checker (COORD approved (a)): fork on branch claude/kv99-coreobs-cov-1112 in epyc8 wt/die-kv-99(-obs); it posts its own READY.
- Item 7 W street fork still running (epyc4 dkv99/wstreet/).
- COORD 06:4x: insertion balance (REACH-FIX-2 generic clock tool) goes into vN2 at compose.
- Hub push was blocked by someone's dirty CODEX-HANDOFF.md (posted FINDING 07:05); my commits are local until it clears.
