# VISLAYOUT3-KVHEAD lane handoff (refresh 2026-11-12 06:51 PST)

## 1 Scope
Per-type re-layouts (positions forms) for KV qwen_kvsys and HEAD s81_head, run in parallel with class fixes (OWNER 11-11).
KV is now owned by DIE-KV-99 (vN2 W-face pocket event). Ruling: no full sign-off on a form vN2 replaces.
- Not mine (owners): ring band (LAND-RING-2), kv3_hgi_v7 ft25 (STREET-RULE-1 pass 2), HEAD closure (HEAD-94), die proto (DIE-PROTO-1).
- Mine now:
  - F1 kv3_hgi FT-STREET: evidence plus an orthogonal delta for vN2. Stops after place; never route.
  - SD-GROW kv3_sys_SD_v1 form A: COORD-approved, die +0.94 %. Full sign-off, unless DIE-KV-99 says vN2 cannot carry the die-width change.

## 2 Worktree
- epyc8 /srv/opentallas-scratch2/claude/wt/vislayout3-kvhead, branch claude/vislayout3-kvhead.
- HEAD 3bfb92c1b1105b0053accaccc637057be06e5517 (pushed). Uncommitted: none.
- Content: tools/die_plan/vislayout/{ft_street,grow_type,ftover,ftposcheck,planview}.py and physical/die_plan/qwen_kvsys/deltas/vislayout3/ (ledgers, SD kit_rtl wrapper).
- Rule: only `git -C` on this worktree; never git in /home/ubuntu/OpenTallas.
- Work dir: /srv/opentallas-scratch2/claude/vislayout3-kvhead on epyc9 (master copies, tools/), epyc8 (kits) and epyc2 (binds). Subdirs: hgi_fts, hgi_fts_b, sd_grow, hgiv7_fts, hgiv7_f2b, base_vF, tools.

## 3 Running jobs
- F1 kv3_hgi: intel2 pid 2221253 (`kit_wave.py run-item /srv/opentallas-scratch2/claude/vislayout3-kvhead/jobs/kv3_hgi_fts/spec.json`).
  - Kit: epyc8 /srv/opentallas-scratch2/claude/vislayout3-kvhead/pilots/items/kv3_hgi/gen/kv3_hgi.
  - Log: intel2 .../jobs/kv3_hgi_fts/unit.log (KW_STAGE lines). Check with `grep -E 'KW_STAGE |AP_RC' unit.log | tail`.
  - Ends after place+GEOM, writing result.json in the job dir. run-item never routes.
- SD-GROW kv3_sys_SD_v1: intel2 pid 2592671 (run-item .../jobs/kv3_sys_SD_v1_grow/spec.json), in place.
  - Place service: systemd --user unit kwp-fd865b0e192131866171, log .../jobs/kv3_sys_SD_v1_grow/place.live.log.
  - Kit: epyc8 /srv/opentallas-scratch2/claude/vislayout3-kvhead/pilots_kv3_sys_SD_v1_grow/items/kv3_sys_SD_v1/gen/kv3_sys_SD_v1.
  - kit_rtl runs in script mode via sd_grow/kit_rtl_wrap.sh (SerDes PHY specialize).
- None on epyc9/epyc2. F1b failed at kit_rtl (plan only on epyc2, not epyc8) and is DROPPED: evidence only, vN2 replaces it. Do not relaunch.

## 4 Watchers (Claude background tasks; Codex re-arms as plain loops)
- Wait for AP_RC: `until grep -q AP_RC intel2:.../jobs/<job>/unit.log; do sleep 60; done` for jobs kv3_hgi_fts and kv3_sys_SD_v1_grow.
- Position proof right after kit gen (already PASS for F1): `python3 -I /srv/opentallas-scratch2/claude/vislayout3-kvhead/tools/ftposcheck.py PLAN TYPE KIT` (epyc8).

## 5 Results not yet posted
- kv3_io_cor_v1 RF1c (inherited, epyc9 /srv/opentallas-scratch2/claude/vislayout2/kv/iocor_rf1b_build): NOT SIGNED. setup TT -139.85 (51 endpoints), hold FF -32.97 (292), DRV slew TT 4675 / FF 3055. LEC EQUIVALENT. Worse setup than wave a11 (-121.8). Strike on RF1c, so it is evidence only.
- hd_host_w spread3 (inherited, epyc9 .../vislayout2/head/hd_host_w_spread3): LEC NOT EQUIVALENT, 298 compare points differ. First: bb:u_dut.u_core.u_lane0.u_ln.u.u_ep.g_rb_safe.u_m.g_bank[1].g_depth[0].g_256.u_m. FAIL_PREFLOOR; container stopped 12:35 UTC. This is an RTL/LEC class, so it goes to HEAD-94.
- F1 proof after kit gen: PASS (6,643/6,643 ft sites, 16/16 cores, flow-20261108-dv-kv, edge_outline, asap7lock-grtoff). Posted 06:24.

## 6 NEXT STEPS (in order)
1. When F1 place lands (unit.log shows KW_STAGE_RC place 0 or geom):
   - Copy epyc8 kit run/layout_review/place/{layout,density}.png and W/geom/auto_geom.png, then VIEW them.
   - Append a row to intel2 ~/coord/lanes/VISUAL-QUEUE.tsv (cols: die type family attempt state render_dir auto_geom host): `qwen_kvsys kv3_hgi kv3_hgi vl3_fts WAIT-VISUAL <kit>/run/layout_review/place <W>/geom/auto_geom.json epyc8`. Commit with coord-commit.sh lanes/VISUAL-QUEUE.tsv.
   - Post the verdict ask to GEOM-VIS-5.
   - Decision rule: NEVER route F1 (vN2 replaces it). If place shows the ft6 street congestion gone (no GRT hot column at x 650-880), post that as evidence to DIE-KV-99.
2. SD-GROW after place:
   - View place renders and post to WAIT-VISUAL the same way.
   - Route only after the GEOM-VIS-5 verdict is not BAD AND DIE-KV-99 has not said vN2 cannot carry the die-width change. Command: on epyc8, `ot-run-wave --mem 96 --threads 16 --dir <W> --hosts epyc8 -- bash <W>/gen/run_kit.sh <K> route 96 16`, with the kit's flow_tag/grt_transition_mode files present.
   - Before route, run ftposcheck (cores n/a; check flow_tag + mode).
   - If NOT SIGNED with reset recovery still worst: fallback = per-chunk reset copy RTL in ot_async_fifo g_sp (COORD-approved fallback, not built).
   - 2-strike rule applies.
3. Post section 5 results (io_cor_v1 to DIE-KV-99, hd_host_w LEC to HEAD-94).
4. Refresh this file at every milestone and at least every 60 min.

## 7 Open READY/ASK
- SD-GROW ASK: approved by COORD (form A; B dropped). Waiting on DIE-KV-99 to carry it in vN2: plan epyc8/epyc9 .../sd_grow/plan/plan_c.json, ledger sd_grow/ledA.json.
- F1 delta to DIE-KV-99 for vN2 adoption (post 06:24). DIE-KV-99 must answer adopt / supersede.
- kv3_hgi_v6 ft18_i/ft19_i band rects (sent to DIE-KV-98, now DIE-KV-99): ft18_i [239.76,95.04,268.92,110.16], ft19_i [17.28,282.96,43.2,300.24].
- hgi_v7 ft25 handed to STREET-RULE-1 (post 03:13). No answer needed from me.

## 8 Gotchas
- bind.py bind needs B/asbuilt.json seeded first (cp /srv/opentallas-scratch2/claude/dkv97/bind9/asbuilt.json), else FileNotFoundError.
- epyc2 lacks some bind inputs; copied dkv95/plan_p4/r8_kv95_phy3.json and kv-types-6/pv/{compose,pads}.
- Plan dirs need a census symlink (../census -> src physical/die_plan/qwen_kvsys/census) for G0.
- G0 schema rejects unknown keys (e.g. reset.note).
- Shifting die geometry: port window_um is a SPAN (x on N/S faces), not a point.
- run-item needs future_lec/ in the job dir (copy from land-ring-2/jobs_kv/kv3_hgi_v7/future_lec). Plans must exist on the gen host (epyc8).
- kv3_sys_SD_v1 kit_rtl must use script mode (kit_rtl.sh -> specialize_serdes_phy), not bind mode.
- epyc9 tail is a Rust tail: use `tail -n N` with one file. epyc8 queue ~130 waiters, so kit_rtl waits 10-30 min.
- route_supply caps core OBS at M5, so it cannot see ft legs over cores. Use ftover.py.
