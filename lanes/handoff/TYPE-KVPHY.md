# TYPE-KVPHY (kv3_phy_v1) handoff
- Routed DB: epyc10 /srv/opentallas-scratch2/claude/kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/kv101ns_3465fe9/items/kv3_phy_v1/attempt_2/gen/kv3_phy_v1 (job 7f58f065501a, RECORDED STRUCTURAL 11-14 00:28).
- Hold split (signoff.json FF): 297 viol, WNS -204.04 = input-port-start (11 port starts). 274 endpoints are OUTPUT-port (o_phy_Q__sN_piN_d2/d3/rhN vs vclk out_min 55) = port-only advisory. INTERNAL non-port: 12 reg->reg endpoints, core_wns -10.94 ps (nonport_n 286 incl output ports, wns -18.3). TT setup -34.25 (3 ep) passes >= -42. io_hold_parent NEEDS_PARENT is advisory/parent receipt.
- So the type is a small internal hold miss (-11 ps, 12 ep): ECO eligible, not structural.
- Form A (late ECO): epyc10 /srv/opentallas-scratch2/claude/type-kvphy/eco_a (eco_loop.py run --from grt --hold-margin 20 --owner-override), log intel2 /srv/opentallas-scratch2/claude/type-kvphy/eco_a.log, ot-run waiting on epyc10 load gate.
- Form B (pre-GRT hold rebuild): epyc10 /srv/opentallas-scratch2/claude/type-kvphy/pg/kv3_phy_v1, resume start=grt from 4_cts.odb with OT_PREGRT_FF_HOLD=1 (+guard 45, NONPORT_HOLD already 1), log intel2 /tmp/pg_kvphy.log.
- On pass: add AUTO-RESIGN row (qwen_kvsys kv3_phy_v1 epyc10 <dir with signoff/signoff.json> - TYPE-KVPHY) and post RESULT.
