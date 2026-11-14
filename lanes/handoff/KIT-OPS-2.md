# KIT-OPS-2 handoff (kit-wave ops lane; COORD is the coordinator) -- 2026-11-12 23:52 PST. DONE, stopped.

## Result (RESULT posted to the queue; it holds the full detail)
- kit_wave.json 9e586a4304b (23:33), on origin. epyc4 is in hosts and first in place_prefer (top level + every die). It is first in gen_hosts for qwen_compute only. epyc7 is in s81 hosts/place_prefer. intel2 sits after the big epyc hosts and before epyc2/intel1, and has no gen.
  Revert: <key> <- <key>_prev_kitops2_e4. Backup: kit_wave.json.bak-kitops2-e4-1112. Script: intel2 /tmp/kitops2_e4_add.py (scratchpad kitops2/e4_add.py).
- intel2 ot-run cap: HOST_RESERVE localhost (16, 207) = 96 threads / about 800 GB, in 3 ot-run files under ~/.local/lib/fleet/{rehost1-kw38-spill-99d7dfcd, kw43-rootreal, isolate-1-kw46m-590d7d62e7}. Backups: .bak-kitops2-intel2cap-1112. Tick wall time did not grow (7.4-7.9 min); if it does, restore (48, 400).
- epyc4 staged on nvme scratch2 (about 9 GB): kit-ops-1/* inputs, hbm t39w/p37 sources, qc src_sw2, the 97 lfcs files. QC src s28 verified (FLEET-2 copy).
- The 4 big src trees (KV/S81/HEAD/HBM) were on the md0 ROOT disk (scratch3 = bind of /home/ubuntu/scratch-root). I removed them per COORD; root is at 513 GB free. They need about 200 GB of nvme (scratch2 has 238 GB at 94%, floor 150), so gen for those dies stays off epyc4 until COORD rules.
- Nothing in the configs lists epyc4 as retired. The ap-e5438a810146 "no host qualifies" happened because its kit dir is gone on every host.
## Open
- COORD: nvme room for 4 src trees on epyc4, or allow root.
- Not yet seen: a QC gen on epyc4 (no QC launch in the first tick).
- epyc8 tools/die_plan/gen_phys.py changed in the 4 kw45 trees during my copy (someone patched it there); this is not mine.

## 2026-11-13 17:50 PST KIT-OPS-2 (successor, took Codex handback 17:18)
- R-MINIMAL live in the wave by config only (coord/state 6c70bd65274, cdc08bf4837). wait_visual/form_gate/hold_unchanged/flow_repeat_gate are false. route_hold_items are cleared on s81/s81_head/kv/qc. Released holds: RCAP-SPLIT, QC st_b visual, coll_ucie, sle_fw_v3, coll_core, hd_tile. 51 R-FLOW retries (retry_fix "R-MINIMAL auto retry"). Hosts lead with intel1/epyc4/epyc8; host_share epyc9 1.0, intel1/epyc8 2.0. Revert: *_prev_kitops2_rmin keys or autopilot/kit_wave.json.bak-kitops2-rmin-1113 / .bak-kitops2-hosts-1113. Scripts are in intel2 /srv/opentallas-scratch2/claude/kit-ops-2 (rmin.py, hosts.py, elig.py, plan/unchanged dry runs).
- First tick 17:42-17:5x: 25 LAUNCH (kv 17, s81 7, head 1) + 9 route SUBMIT (s81 5, kv 3, head 1). The tick was still running at handoff.
- Still held, each waiting on its die owner's plan swap: QC "*" (HF-1c), S81 DRT73-AOR/SVC-MACRO/r12bA leaf/col_h, KV hg/hgi, HEAD hd_ctl/hd_lep0N. HBM is PARKED. 17 WAIT-PARENT queue rows belong to PROFILE-1 (io_hold_parent gate).
- Standing order (COORD/OWNER 17:4x): when a die owner (DIE-S81-90, DIE-QC-101, KV-101, HEAD-98) asks with bind + LATCHECK PASS, back up kit_wave.json, swap event/plan/src/bind for that die and relaunch every type on intel1/epyc4/epyc8 (+epyc10 once onboarded; not resolvable at 17:50). epyc4 lacks the s81/head/kv src (kw45): stage it or epyc4 only places.
- Watch list: GUNIT E8 user scope oth-ubuntu-1897702 is in GRT extra iteration 20/30. H2 LEC I1 2478837 is live. S81 t30 (epyc8) and t50 (epyc8) post-GRT repair_design logs went silent at 11:48 and 15:00 while CPU stays busy; t42 GRT epyc2. HBM q_b002__physical_v1 GRT epyc7 has run 2d23h and KV kv3_pv_v5n GRT epyc7 2d07h; I recommended COORD stop both (not my PIDs). Nothing killed.
- epyc2 admits fine (578 GB). The wave lanes there already resolve to scratch3; no change was needed.
- PROFILE-1 file split ACKed: KIT-OPS-2 owns kit_wave.json and the runtime wave only.
