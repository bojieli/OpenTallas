# ds-1010 lat-audit (2026-10-10): stationed request/response latency on the DS-ROM S81 dies

- head631 (`head631.opts`, generator src 6aac16222 = main for the head die): `tools/s81/hub_stage_count.py --check-mtp-rtt` gives the pin-to-pin stages capture->mtp 6, mtp->capture 7, vm->mtp 11, mtp->vm 11, mtp<->collective 8/8. These are the chain stations plus the hop-fix / pin-relay `g_hb_*` stations. The earlier chain-only count was 5/6/9/10, so dsfd_mtp_seq_rtt is now 6/7/11/11 (`head631_stages.json`, verdict PASS).
- `mtp_rtt_link_gate.log`: the real-chain receivers PASS. The legacy receiver, the short-RTT mutant and the stale 5/6 and 9/10 receivers on the real chains all FAIL, as required. A receiver one hop over-sized PASSes, as it should for a credit receiver.
- `mtp_rom_bench_rtt.log`: the system rtt_s0 cases PASS at the new chains, and neg_off1 FAILs as expected. The stale-RTT case was dropped: its traffic never stalls a receiver with flits in flight, so it passed. The receiver-depth negatives therefore live in the link gate.

## Field transaction age (x1b + rgap reach recipe), `--lane-equal`
- Gate `tools/s81/field_alignment.py` now checks go as well as x1 against x0. go runs cc lane -> slot stations -> pair sequencer lc -> combinational go_e -> go relays -> bank.
- Base rgap recipe (`field_fa_full_base_rgap.log`): FAIL. 256 x0/x1 mismatches (top-slot x0 got a relay that xb did not). go-x0 skew: -1 on 128 elements, 0 on 640, +1 on 1024 (sequencer -> element go_ column relays).
- `--lane-equal` makes two changes. (1) Column relays on xa/xb/cc of one slot segment take the max count of the three. (2) `_go_retap`: a sequencer whose go_ carries k relays taps lc k registers earlier on the cc chain.
- Result: layer1 and layer1e both PASS, 1792/1792 elements with x0 = x1 = go (`field_fa_full_le.log`, `field_fa_l1e_le.log`). The +1 go mutant FAILs on 1792/1792 (`field_fa_full_le_mut.log`).
- `check` on layer1 (`field_check_full_le.log`): SS reach_violations 0 and TT reach PASS. far_side_relays went from 3849 to 3977 (+128 lane-pad relays). That class already failed on the base recipe (exit 3 unchanged).

## collective <-> mtp receivers
- `rtl/dsrom_sys/mtp/dsfd_coll_mtp_ep.sv` is the collective's receivers for the sequencer's token return and seed. They are ot_dsrom_mtp_lrx_rtt sized to the real head631 stages, mtp -> collective 8 and back 8, depth 20. The chain record alone says 6 / 7.
- Link gate (`mtp_rtt_link_gate.log`): pass_c PASSes; fail_legacy_c and fail_stale_c (receiver sized for 6 / 7 on 8 / 8) FAIL as required.
- The receivers are not bound into dsfd_sp_collective yet, because that slab has no MTP port today.
