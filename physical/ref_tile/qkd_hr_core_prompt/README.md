# qkd_hr_core_prompt p8 (KV-HOST/PROMPT 10-19)

HOST root cluster child (KV / system die, MU release). p5 and p6 routes did not close, so every revision is a structural
rebuild against the SAFE-DESIGN checklist (owner 10-19), not a re-route. p7 (KV-RELAYGEN) fixed the four big reset relays
but its gate (37318d6a2, ot-epyc8 070702) still failed checklist items 3 and 6 and showed a CTS-stage setup class:

- item 3: `u_rank__u_control__u_packet__u_axi.u_rst_relay` drove 547 flops and `u_rank__u_program.u_rst_relay` 363 (> 256);
- item 6: the five SRAMs sat in one abutted column mid-die (7 channels of 0 um, std cells split on both sides);
- CTS wns -13.6 ps, tns -51: `u_host.u_m.u_core.cq_tail[0]` -> 16-bit increment -> `& cq_mask` -> `!= cq_head` -> 32-bit
  `c_cqfull` increment -> `c_cqfull[31]`.

p8 changes (all bit/cycle exact, 0 schedule cycles):

1. `tools/qwen_kv_die/host_cluster/gen_prompt_rr.py`: u_axi (`qkd_host_axi_packet`) gets 7 and u_program
   (`qkd_host_program_loader_target`) 5 KEPT identical relay copies. These members had one copy, so no pre-optimisation
   OT_RST_COPIES count existed; they are provisioned at the worst p7 pre/final ratio (records 1,929 / 671 = 2.87x):
   547 x 2.87 -> 1,600 loads (7 copies), 363 x 2.87 -> 1,100 (5 copies). `reset_relay_split {max_loads 256}` spreads the
   loads; release timing unchanged (+3 ck_core edges, every copy equal).
2. `tools/qwen_kv_die/host_cluster/gen_prompt_pd.py` -> `ot_host_if_pb2_observed_pd`: `cq_t1 == (cq_tail + 1) & cq_mask`
   is a register whose next value comes from the next-state cq_tail (advanced only at ev_pop, to cq_t1) and cq_log
   (written only by CQ_LOG); `cq_room` is one 16-bit compare `cq_t1 != cq_head`; `c_cqfull` is `ot_hkv_cnt_la` (32 / LO 16).
3. Floorplan: the 1024x256 SRAM against the N face (the lightest pin face: 669 of 5,439 pins) at (43.2, 172.8); the four
   256x64 SRAMs in a 2x2 below it at x 43.2 / 172.8, y 86.4 / 129.6. Every origin on the 43.2 um lattice; macro-macro
   channels 25.4 um (N/S, no pins) and 63.3 um between the 256x64 pin faces; edge channels W 41.0, N 35.4, E 39.5 / 60.7 um;
   a full-width 84 um std-cell band along the S face (clock entry ck_core at the S centre, S pins).

## Benches (fleet, Verilator 5.050)

| bench | result | evidence |
|---|---|---|
| cluster_lockstep (cluster_gate exact) | PASS 6/6, 20,000 core cycles | `results/arch/qwen_split_1014/host_root_cluster/benches/cg_exact_prompt_p8.log` |
| cluster_child_mutant (core_prompt reset inverted) | FAIL 0/6 | `.../cg_mutant_qkd_hr_core_prompt.log` |
| cluster_rr_mutant (QKD_HR_PR_RR_MUTANT) | FAIL 0/6 | `.../cg_rrmutant_qkd_hr_core_prompt.log` |
| prompt_pd_equiv (capture decode, cnt_la, **pb2 cq lockstep vs original, 2 shapes x 300k edges**) | PASS (pb2: 30.4k c_cqfull cycles, 5.5k CQ posts, 2.0k CQ_LOG changes with events pending, 0 mismatches) | `.../prompt_pd_pass_p8_v5050.log` |
| prompt_pd_mutant (QKD_HR_PD_MUTANT, OT_HKV_CNT_LA_MUTANT, OT_HKV_CQ_MUTANT) | FAIL 3/3 | `.../prompt_pd_mutant_p8_FAIL_v5050.log` |

Every file the benches read is in the job's `source.extra_paths` (spec `job.extra_paths`).

## MU

p8 is built at MU0. The MU context record port (claude/mu-kv-ctx-1019 @7eea9df20: `qkd_host_record_port_mu #(MU 1)`,
`_rr_mu`, MU core `qkd_hr_core_prompt.v`) is not on main and cannot be integrated into this child alone:

- its pair-phase check (`qkd_host_record_port_mu.sv` line 162, "1st edge without its 2nd") is a sticky fault on every
  token run of the MU0 single-slot d2d calendar, so it needs the KV die booted with the MU image (target 11 `_mu`,
  claude/kv-linkcfg-mu-bench-1019, not on main) in every KV die / token test;
- the cluster composition bench and the CRITICAL parent qkd_host_root build the ONE committed cluster
  (`rtl/qwen_sys/host_cluster_20261017` + `bench/flat_wraps.json`); switching `root__u_records` to `_rr_mu` there changes
  every sibling's bench and the parent's RTL, which is a cluster-level adoption (KV-HOST lead + MU-KV-CTX), not a leaf edit.

When that adoption lands, MU1 is an `rtl_change` reroute of this same kit (same ports, same geometry): regenerate the
record-port wrapper with the relay copies (gen_prompt_rr.py) binding `qkd_host_record_port_mu #(.MU(1))`.

## p8 CTS gate (source 8a04df728 staged, ot-epyc6 `ref_gate/qkd_hr_core_prompt-20261019-115518`)
PRE_ROUTE_GATE WARN (0 fail, 5 warn: 17,684-sink root guidance x3, insertion > 300 guidance, pin-bound fill). reg->reg
worst +43.0 ps, reg->macro +65.8 ps, hold +36.1 ps; TT/FF insertion 438.7/362.8 ps, pin-flop spread 45.8/42.0 ps;
trial GRT overflow 0 (M2 27.7 %); actual pin geometry 5,335/5,335 on track.  Yosys OT_RST_COPIES (canonicalize log):
every relay copy <= 230 loads (records 9x215, csr 6x229, host 3x230, pkg 10x152, axi 7x132, program 5x73).

## SAFE-DESIGN checklist (owner 10-19; KV-HOST2 review 10-19 17:00)

| # | item | result |
|---|------|--------|
| 1 | pins | PASS: pin regs on 41 in / 65 out data ports (+1 edge); por_n lands in 2 stages (reset_landing ok); no comb in->out |
| 2 | reach | PASS: 280.8 um square; pin-reg flops sit at the faces, logic spine centre-S (<= ~300 um single-cycle) |
| 3 | fanout | FIXED reset: all relay copies <= 230 loads (p7 had 547/363). Data nets: no failing cone (reg->reg +43 ps) |
| 4 | depth | PASS: textbook depth 525 ps; cq_tail->c_cqfull class removed (cq_t1 register, ot_hkv_cnt_la) |
| 5 | storage | PASS: prompt/program storage in 5 SRAMs (1x 1024x256, 4x 256x64) |
| 6 | floorplan | PASS, util WAIVED (pin-bound 5,439 pins, <= 5.8/um on every face): macros on the 43.2 lattice, channels 25.4-63.3 um (p7's 0-um abutted column gone), full-width S std-cell band |
| 7 | clock | PASS: ck_core at the S centre beside the logic spine; spread 45.8/42.0 ps TT/FF; insertion 438.7 > 300 is guidance (boundary matched by parent compensation, PL-KVHOST plan B) |
| 8 | schedule | PASS: 0 added schedule cycles (relay copies are equal-latency; cq_t1 is exact) |

Visual review: floorplan.png/density.png inspected -- 1024x256 SRAM near the N face, four 256x64 in a 2x2 below,
all on the lattice with open channels; std cells form one continuous spine from the S band up between the macros to
the big SRAM, plus thin pin-flop columns on W/E/N; densest bins only in the S-W pin-flop band; no islands.
