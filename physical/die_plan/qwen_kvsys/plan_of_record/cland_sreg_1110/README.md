# cland_sreg_1110 (DIE-KV-97, 2026-11-10): STATUS-REG-1 on the KV status-copy ring types

COORD 11-10 class fix for kv3_io_cor 817517ba2672 (routed TT -480.4 / FF -73.1, NOT SIGNED).

Class (routed sign-off STA): the landing-ring status crossing and half-cycle guard, not io ports.
- kv3_io_cor a8: TT -480.4 status copy lap_q -> rv (fclk -> clk, max_delay 416.5, 7 levels); TT -253.6 / FF -82.1 oh -> ghi0 (clk rise -> fall)
- kv3_io_cor_v1 a9: TT -50.7 oh -> ghi0, status written -> lap_ok
- kv3_sys_SD_v1: TT -212.1 status copy -> lap_ok
All three were built with STATUS_REG 0.

Form: `partition_types.<T>.landing_status_reg = true`. The generator switch is already on main (clock_landings.py STATUS-REG-1,
default absent = byte-same, test_landing_status_reg.py). This event only turns it on for the KV types that carry
landing_control_status_copy and no landing_status_reg: kv3_io_cor, kv3_io_cor_v1, kv3_sys_SD_v1, kv3_io_ft, kv3_sys_SD
(kv3_io_ft_v1 already has it from kvcls_1108).

Cycles: data q / ready +0 (lane_added_cycles unchanged); rv / lap fault seen +1 clk (status_reg_added_fault_cycles 1).
Fault reporting is not on the token schedule, so there is nothing for TOK-VERIFY-1 to re-schedule.

Proof
- EQ: rtl/test/meso/status_reg/run.sh on main RTL and on the kv3_io_cor a8 kit RTL: 8/8 phases lock-step, 4/4 mutants caught
  (covers CONTROL_STATUS_COPY 1, WREG 1, WFALL 1 = the kv3_io_cor ring form).
- Timing form on the kv3_io_cor ring (u_cland_ft13_i: W3 DEPTH4 CSC1 WFALL1 WREG1), yosys + OpenSTA, ASAP7 RVT TT, unplaced:
  STATUS_REG 0: worst fclk -> clk status path 9 levels (lap_q -> u_lap -> rv), clk rise -> fall guard path 4 levels present.
  STATUS_REG 1: status crossings are flop -> flop (0 levels, 63 ps); worst crossing is the untouched data select (2 levels);
  no clk rise -> fall path left. +24 rise / +6 fall flops per ring.
- Generator: test_landing_status_reg.py + test_cland_ring_fanout.py 20/20; test_event.py 2/2.

Build (repo root): `python3 -I physical/die_plan/qwen_kvsys/plan_of_record/cland_sreg_1110/event.py PLAN_IN PLAN_OUT [--types a,b]`
Wave plans: kvr2 92370701 -> 17d06742; kvrs 8ca41a6b -> 54758474 (epyc7 + epyc2 /srv/opentallas-scratch2/claude/dkv97/sreg_plan/).

Other dies (routed-not-signed sweep, 11-10): QC sle_*/slw_* types hit the same ctl_w/ctl_lap -> glo0/ghi0/lap_ok/rv paths with
STATUS_REG 0; the QC knob is DIE-QC-97's die-wide clock.landing_ring_status_reg (same generator switch). S81, HEAD, HBM: no
routed-not-signed row has a worst path through these ring status/guard paths.

## Step 2 (hold half): ringhold_event.py, on top of step 1

COORD 11-10: each type relaunches once with both fixes. PLAN-GEN-RULES rule A (and AT) on these types is a no-op
(plan_event.sh qwen_kvsys on the step-1 plan: 0 types, 0 cores, bytes unchanged), because ring ports are timed against
the forwarded fclk, not vclk. The FF hold misses are ring input ports into the falling-edge writer: ring_hold
sender_ps -385 puts the input min 31.5 ps after the capture fall, and the receiver fclk_in tree adds 87-120 ps
(io_cor ft17_i -68.9, io_cor_v1 ft23_i -119.1). Form = KV-PLAN-2 form A, clock.ring_hold.sender_ps_types
{kv3_io_cor, kv3_io_cor_v1, kv3_sys_SD_v1: -50} (tool 17002ccba5e on main; KV-PLAN-2 measured sender worst +10.55 FF
minus a 60 ps tap-skew allowance). The wave src needs the 17002ccba5e tool files (landing_contract.py, schema.py,
sdc_lint) or the key is rejected. Not covered: the clk tap-to-tap hold (io_cor bin -> ist -73.1, rrl -> eq RESETN
-47.9; io_cor_v1 rrl -> eq -66.4, arst_n -> rst_in -90.1), which stays with post-route hold repair.
Plans: kvr2_rh 6e1ad24c, kvrs_rh 4afd5f88 (epyc7 + epyc2 /srv/opentallas-scratch2/claude/dkv97/sreg_plan/).
