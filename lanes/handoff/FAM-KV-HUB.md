# FAM-KV-HUB handoff (Sonnet 5.5 lane, 11-20 PST night)
Family: kv3_hub_{C,Ei,Eo,Wi,Wo}, kv3_hroot, kv3_sys_c, kv3_sys_SD_v1 (routed, hold<=30 ps per HARVEST-ECO-2350). Plan-event owner: KV-PLAN-R3 (D26/D27c/D28). hg/hgi/pv/pc belong to other lanes.

## Census (OWNERS-SWEEP)
- hub_Wi: FAILED gen/place (stale 16 h), fix rides D26 R3f (bind oth-ubuntu-2521925-1795240795 epyc7; d26_chain.sh auto-applies). Confirm on first D26 gen.
- hub_Eo, hub_Wo, sys_c: placed, route held (geom) -> D27c rows (hub_Eo reset row, sys_c reach). D27c strict bind rc1 R8_STALE x30; being made type-uniform by KV-PLAN-R3.
- hub_C: held, WAIT-BIND (views re-frozen CLAND-MACRO-1, rows in D27c).
- hub_Ei: running route since 11-20 19:15.
- hroot: REPRESENTATIVE. Running route, KV-D25d attempt_5, unit oth-ubuntu-2785028-1795181222 on epyc2 (dear-crayfish), work /srv/opentallas-scratch3/claude/ot-jobs/kv3_hroot-route-dear-crayfish-2828315-1795181254/work.

## hroot findings (read-only, no job touched)
- GRT finished (5 h 30, 30 extra iterations): final congestion Max H 20 / V 7, total 2178, usage 2.86 pct; now in post-GRT repair/DPL (DPL converged 00:0x). Next: detail route, then signoff. Do not cancel: GRT overflow fell, setup not measured < -300.
- Port-in hold -303 (post-hook): kit constraint.sdc lines 274-295 carry set_input_delay -min -385 on ring inputs (plan clock.ring_hold.sender_ps placeholder). signoff.py (KW-FIX-24, STD_MIN_START port/other/reg) classifies a hold miss started only at a non-clock input port as LOCAL_PASS_NEEDS_PARENT, so it does NOT block local sign-off of hroot; it becomes the parent die-level obligation. Fix remains structural/plan: measured sender_ps_types row (about -50 as io_cor/sys_SD_v1 have) for D27/D28, owner KV-PLAN-R3, after pc CTS fix measures the senders. Needs reg count = 0 and other = 0 in the hroot signoff to pass.
- Watch at route end: STD_MIN_START other/reg must be 0; if reg > 0 treat as internal hold -> shared-tap/CTS balance, not buffers.

## Next
1. When the epyc2 unit ends: read signoff.json (DRC, TT setup >= -42, hold STD_MIN_START, LEC); if signed, carry (nothing to carry for sdc) and hand sender_ps row to KV-PLAN-R3 for D28.
2. Siblings: take D26 (hub_Wi) and D27c (hub_Eo, hub_Wo, sys_c, hub_C) results from KV-PLAN-R3; no duplicate builds. sys_SD_v1 hold<=30 ECO lives in HARVEST-ECO-2350.
3. Successor not needed yet; stand down text: lane has launched nothing.
