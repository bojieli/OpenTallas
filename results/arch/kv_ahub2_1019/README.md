# KV-AHUB2 (10-19): grouped AHUB transport collected, four-state bench fixed, mapped fanout proven

Lane KV-AHUB2 (LEAD2-KV, tree K.STA.AHUB). Inputs: Codex grouped source c72d6df86 / frozen bench 9e14f6a9d
(codex/kv-ahub-grouped-transport-source-1019 @ bda2803c9), model 143642b6b. The source file here is byte-identical to the
reviewed one (sha256 f8211325ebd9...b25, attempt1 manifest).

## 1. attempt1 collected (ep8 unit oth-ubuntu-2326353-1792452071, /srv/opentallas-scratch/claude/kv-ahub-grouped-transport-source-1019/attempt1)
- suite.rc 0 and "GROUP_SUITE_PASS", but that line was **false**: all 8 Icarus four-state runs (iv_w268_i0..3, iv_w68_i0..3)
  exit 1 with `GROUP_FAIL predecessor_frontier cycle=0`.
- Runner bug: `[[ $rc == 0 ]] && grep ...` as the last line of the loop body. A failing non-final `&&` member does not trip
  `set -e`, so the failure was dropped.
- Bench bug: `reg tx_rst_n=0, rx_rst_n=0` is a declaration initialiser. Icarus gives it no negedge event, so the frozen
  4415 predecessor's async `ot_rst` faces stayed X and its accept was X at cycle 0. Verilator's 2-state random init hid this.
  The DUT was not involved: it is written with old-Q by `old_q_injection.svh`.
- Verilator 5.050 results were genuine: 1 default + 18 positives PASS, and all 33 causal mutant runs FAIL with the expected
  class (accept_frontier 12, valid_frontier 12, raw_authority 6, payload 3).
- Attempt1 is left unmodified (historical).

## 2. Fix at source, attempt2 PASS (ep8 unit oth-ubuntu-2346792-1792452559, .../claude/kv-ahub2-1019/attempt2)
- `bench/tb_grouped_transport.sv`: the resets start HIGH and fall at 0.2 ns. Every async flop sees a real negedge in both
  simulators. There is no clock edge before 5 ns, and the old-Q injection is still at 0.5 ns, after reset propagation.
- `bench/run_fleet_reviewed.sh`: four-state and default Icarus failures are now counted in `logs/four_state_failures.log`.
  The suite exits 1 on any failure, so a false PASS can no longer be printed.
- Result: suite.rc 0. Verilator: default + 18 positives PASS, 33 mutants FAIL with the expected regex. Icarus: default + 8
  four-state positives PASS, including INIT_CASE 3 (X old Q). Every positive run gives first_accept 21 (predecessor 19:
  exactly +2), first_output 25 (+4), accepted 244 / observed 240 / discarded 4 / txdrain 4.
- Logs and witnesses: `attempt2_logs/` (fail witnesses for every mutant, frozen_inputs.sha256, tool versions).

## 3. Synth/map on ASAP7 RVT TT (fleet, docker orfs:asap7lock, `tools/qwen_kv_die/ahub2/synth_map.sh`)
Top: `qkd_ahub_grouped_zh_transport_private` with ENABLE=1 (268-bit command and 68-bit return). Census:
`tools/qwen_kv_die/ahub2/mapped_census.py`, an uncapped every-driver logical-pin count through INV/BUF.

| run | synthesis | FF | max FF load | max comb load | verdict |
|---|---|---|---|---|---|
| map1 | plain `synth -flatten` | 2710 | 136 | 553 | FAIL (witness) |
| map2 | kit-standard `ot_keep_regs.tcl` (ORFS SYNTH_CANONICALIZE, the kit default) | **3075** | **32** | **22** | **PASS** |

- **map1:** `(* keep *)` alone puts the attribute only on the wire, so opt_merge folds every per-bank reset leaf, `phase`
  and `ingress_valid` copy. One `!active` OR2 then drives 553 loads, and one ingress_valid FF drives 136. This is the
  yosys-keep memory again.
- **map2, flops:** the FF count equals the model's 3075 (2832 DFFHQN + 243 DFFASRHQN). The five 32-load roots are the
  designed maxima.
- **map2, non-clock inputs:** child_rst_n 27, core_rst_n 26, command_valid 5.
- **map2, constants:** 343 loads on literal 1. The kit realises these as per-load TIEHI (kit_netlist.sh hilomap). They are
  not a logic root.
- **map2, area:** 1416.77 um2 per ZH transport, of which 917.93 um2 sequential.
- Summaries: `map/map{1,2}_mapped_census_summary.json`; netlist hashes: `map/mapped_netlists.sha256`.
- **Consequence for the kit:** any AHUB kit with this transport must synthesise with OT_KEEP_REGS on (the default). The
  gate's mapped census must show 3075 FF per ZH instance. Never use a plain flatten.

## 4. Safe-design checklist (component; the hub kit is not built yet, see 5)
1. Pins: PASS (component). ingress, landing and landing_valid are registered. Reset lands in 2 group-root stages and then
   2 leaf stages (raw AND authority).
2. Reach: OPEN. This is decided by placement inside the hub. The ring sits at the ZH face and its ingress at the core face.
3. Fanout: **PASS on the mapped netlist** (max 32, kept copies, map2).
4. Depth: PASS by construction: one-hot slot decode, 4:1 AND-OR read, no arbitration. Not timed yet.
5. Storage: 1344 bits per ZH are indexed 4-slot flops: 33+1 cmd banks and 8+1 ret banks of at most 8 bits x 4. Each bank
   is 32 bits or less, far under 2 kb, so flops are correct; no SRAM.
6. Floorplan: OPEN (hub kit).
7. Clock: common clock today. A two-clock landing (write on the tx region, read on the rx region) is needed for regional
   roots. See 5.
8. Schedule: static. The cost is +4 command edges and +4 return edges per ZH crossing (ZW_RLY = ZR_RLY = 0 today), plus 2
   startup edges once per reset release. KV-GEN9 has been told (lanes/KV-GEN9.md).

## 5. AHUB kit: what is still needed (precise next steps)
The hub (`qkd_ahub_static_dw_safe`, 734.4 x 540 um, 4 ot_nhb_zh + ot_qkh_recip_leaf) failed both gates on the clock rule:
- sfa: pin-flop spread 86.5 TT / 97.3 FF.
- sfb: 116.3 / 123.2.

Root cause: the spine pads every flop to the child insertion. Both gates are terminal (12:48), so there was nothing to
cancel. A structurally safe successor needs, in order:
- **a. Two-clock landing.** Make the grouped transport a true two-clock landing (lanes/LANDING-CONTRACT.md L1-L3). ingress,
  payload, slot_valid and the write pointer go on the tx-region clock. ring_q, landing, landing_valid and a free-running
  read pointer go on the rx-region clock. Both pointer epochs come from the existing grouped reset roots (D=4, read offset
  E=2). Today's single `phase` drives both write and read, so it must split into two pointers. Re-run this bench (both
  clocks tied gives the same results) plus a skewed-clock bench over the L5 window.
- **b. Hub RTL variant.** Write `qkd_ahub_static_dw_g2`: the transport replaces u_ri/u_ro on each ZH, the ZH region roots
  are ck_z0..3, and the core/io/recip region root is ck_c. Generate the regions through tools/landed_parent/lp.py so the
  landed_record exists. The kit spec uses clock multiple_cts_roots with clock_data_paths related_same_frequency.
- **c. Calendar.** Z_IN and root return move +8 edges per pass, and the RECIP and HUB_PUB laws stay unchanged. Lockstep the
  bench `tb_qkd_ahub_static_dw_safe` against the sealed hub with the shifted calendar on all 7 HKV-DIE3 calendars, plus the
  existing m1-m12 mutants.
- **d. Face copies and gates.** Re-apply the 105 per-port face copies (distribute_faces.py) to the new native netlist. Then
  gate the main kit and a centre-fed fallback (common-clock transport as relay only, landed=false) in parallel with
  `--cts --remote auto`.
