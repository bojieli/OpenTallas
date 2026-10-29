# TOK-HBM-6 prep (2026-10-28, waiting for DIE-HBM-10 C25c + strict bind 0)

All numbers below are DRYRUN on C25b plan 4180334c (refreshed 23:04; the 6b3a80cd plan of TOK-HBM-5 is gone). They are not a programme.

## host_write_interval = 5 edges [CHECKED own sim]
tb_host_write_interval.sv drives the real rtl/hbm_accel/host_static_20261015/ot_hbm_host_static_ingress.sv at max AXI rate
(AW+W together, bready=1). Log host_write_interval.log: bvalid-to-bvalid 5 edges; cfg_v every 40 edges (8 F24 writes per 256-b payload).
rtl_constants_hwi5.json = TOK-HBM-4 rtl_constants + host_write_interval 5 with this source.

## host_to_provider = 4 cycles (COORD 23:23: declared static boot path, multicycle in die STA; DIE-HBM-10 owns the plan entry)
c25b_side.dryrun_h2p4.json = DIE-HBM-10 c25b_side.json (4180334c) + provider_legs.host_to_provider.cycles 4 (DRYRUN only).
Estimate: 6929 um x 0.3659 ps/um = 2.54 ns < 4 x 0.833 = 3.33 ns (UNCHECKED shared wire model, DIE-HBM-10 number).
Note for the multicycle declaration: the ingress payload (cfg_target/addr/data, desc) changes at most every 40 edges
(once per 8 writes) [CHECKED sim], so payload multicycle setup 4 / hold 3 holds by construction. The valids
(cfg_v/desc_v/launch_v) are 1-edge pulses: a multicycle path cannot carry them. They must ride a 4-flop registered
chain (3 bits) on the same lane, so payload and valid both arrive at +4 edges.

## Calendar dry run
bound_from_plan.py on 4180334c + dryrun side: down/up NW 53/44, NE 53/45, resets 50 (q0/q1 x NW/NE), root 17, h2p 4, p<->root 0/0; missing 0.
four_role_calendar.py (real MTP6 jobs f0b93231, 161 records): only MISSING = source_plan_commit (plan not committed).
With a placeholder commit: HC_PRE_NORM n=6 at rgap 0 FAULTS (r round trip 267 > x-slot 174) -> compiler must emit rgap >= 24
(was 18 on 6b3a80cd at RT 73/74; the 23:04 refresh added hub stations). At rgap 24: wsc 146, pk5 1, pb5 0,
boot offsets 119 (4 roles) / 86 (root), preload 13013, commit 13063, START 13064, 161 records span 182,985 cycles
(FUSED back-to-back upper bound). rgap cost ~81 x 24 x 5 = 9,720 cycles ~8.1 us per MTP pass (ESTIMATE, same formula as TOK-HBM-4 7,290).

## Vehicle plan (after strict 0)
bound (C25c plan + commit) -> calendar -> fold_s_roles.py --map (binder instance map) -> fused_job217_emit --calendar -> programme
-> fused_host_boot_emit -> epyc2 ot-run Verilator vehicle on the bound composed top. Bench rule: no intra-assignment delays
(`x <= #d`), [CHECKED grep: none in tools/hbm_layer_vehicle, tools/hbm_next, rtl/hbm_next on origin/main].
Checks: per-record bit-exact vs golden; latency of record = completion_cycle - launch_cycle measured vs calendar; tok/s vs composer
(> ~5% cost vs 1906 tok/s -> owner).

## Mutants (each must FAIL)
- M1 pk5 0 instead of 1 (NW/NE pad off by one) -> merge mismatch / fault. PRIMARY.
- M2 one job217 bit flipped (A base of record 0) -> output mismatch.
- M3 HC_PRE rgap 23 -> calendar fails closed and lane x-slot FAULT in RTL.
- M4 START one edge early (resets + 5) -> provider fault.
- M5 roles NWq0<->NWq1 swapped -> mismatch.
- M6 SM attn gin/qin tied 0 (the C25b binder state) -> mismatch (proves the bench sees the SM inputs).
