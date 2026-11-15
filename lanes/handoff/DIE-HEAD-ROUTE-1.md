# DIE-HEAD-ROUTE-1 handoff (2026-11-14 22:15 PST)
## Scope
First die-level routed DB for s81_head on plan rp21z16 (prep p16 staged epyc2 /srv/opentallas-scratch3/claude/die-head-route-1/p16/prep/source_plan.json; head-98 asset paths rewritten to p16/prep/assets, original kept as source_plan.json.orig). Re-run on rp21z20 when adopted. Shared flow with DIE-KV-ROUTE-1 (I write views/assemble/route/report on HEAD; they keep the clock kit).
## Layout (epyc2, scratch3)
- src/ = tools+physical/common_flow copy of kw45/src_head_rp21z_pgcaplec_c327 (git clone of hub into wt/ is stalled at 124K, hub slow; not used)
- proto_die.sh, mk_combo_kv.py (from die-proto-3), run_p16.sh -> head/p16/ (CHAIN.log, kit/, grt_*_*/, sta/)
- signed/<die>/<type>/6_final.odb rsync from rtx-pro mirror (log rtx-pro /tmp/claude-1000/rsync_odb.log); signed LEFs not yet generated
## Running
ot-run job (intel2 ~/tmp/dhr1_p16.ot) -> epyc2 run_p16.sh: plan-shape die_trial kit + die GRT (TT/FF/off) + die STA on rp21z16. Monitor on head/p16/CHAIN.log.
## Signed-view match vs rp21z16 (rtx-pro DEF DIEAREA/PINS vs plan outline + buses/ft_slots)
17 types checked: outline MATCH 16/17. hd_tile OUTLINE-DIFF: signed 708.48x1036.8 vs plan 717.12x1036.8 (plan 8.64 wider). All 17 have the same +1 data-bit on every bus/ft pin (e.g. link 565 plan vs 566 signed, 514->515, 64->65): systematic status/monitor bit convention, no missing/extra pin names. Cores he_epc 224.64x492.48, kp4_dchn 276.48x138.24, lep_pair 777.6x492.48 MATCH plan hard_core outlines. Die grew 17522->17712 wide (plan 17712x17556.48); partitions extend only to 17608x17453, so growth is outside partition extents (ring/margin), no signed type changes size except hd_tile.
Not in signed set (plan-shape abstracts, FLAGGED): hd_ctl, hd_host_e, hd_host_w, hd_mesh, hd_lep0N, hd_serdes, hd_ctl_n (see below), cores elemA/elemB (NO-DB).
## Notes
- hd_ctl_n: INDEX flags SHA-differs-from-record. AGIdock copy NOT reachable from here (/archive absent on rtx-pro, ot-pve hosts unreachable). Using the mirror copy flagged until COORD gives the AGIdock host.
- Duplicates: newest (last) INDEX row per type.
## Next
1 read GRT overflow/die STA when CHAIN_DONE; post. 2 write_abstract_lef from signed ODBs -> VIEWDIR/<type>/<module>.lef, rerun kit --views. 3 detailed_route die-top nets, DRC by class/location, RSS. 4 lv_extract on routed ODB.
