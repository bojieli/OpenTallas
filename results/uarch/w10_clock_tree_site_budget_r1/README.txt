W10 fixed clock-buffer/site reserve r1. MODEL_SIZED_PHYSICAL_HOLD.

Base: e25b8548db86ca01b8fc60795e616d18cea04f24, isolated codex/w10-clock-site-budget.
No model generator, RTL, source pins, main/TASKS, wake owner or physical jobs changed.
Original c8 DRT-0255, FRONT_PAR FLW0024 and bankmap FAIL_model_mismatch remain failures.

Reproduce in a checkout containing the existing owner prerequisites:
  python3 tools/w10_clock_site_budget.py --output results/uarch/w10_clock_tree_site_budget_r1/receipt.json
  python3 -m pytest -q tests/test_w10_clock_site_budget.py tests/test_w10_fullmap_slot_fit.py tests/test_w10_conditional_interface_audit.py
Optional read-only raw-source corroboration (no synthesis or physical flow):
  python3 tools/w10_clock_site_budget.py --verify-netlist /home/ubuntu/w10-w18-recovery/baseline_wake/fullmap_r2/1_2_yosys.v --output /tmp/w10-clock-replay.json
All ordinary replay inputs are committed. Raw netlist is only needed for optional corroboration.

Prerequisites: owner fullmap_r2 structure/synth area; bc1cc capture_local_fit,
085ea91 conditional coordinates, fullmap_slot_fit and allport source inspection,
51e30 conditional PG/pin-union audit (parent 80f073). No replay over original RTL.
Model SHA remains 2da5b6d90adfbeb58ca9355db636835205bf6953328a247bf709c6ab93260c45.
receipt.json pins exact consumed inputs and the new tool. library_origin.json pins
the actual worker LEF and SS sequential library plus the read-only ORFS image
INVBUF library extraction. Image SEQ SS matches the worker bytes; INVBUF belongs
to that same library family, not a claim that an absent original worker INVBUF
archive was recovered. Included BUF cell and LEF retain source license/provenance.

One fixed hypothesis, not optimized CTS: BUFx12, 32 endpoint pins per leaf,
four buffer children per branch, seven buffer levels per tree, singleton pads.
Sorted mapped names define leaves and parent chunks deterministically.
Endpoint groups 10108/6161/5269/67762 and four macros yield eight gated trees;
2433 ungated flops plus eight ICG CLK inputs form the ninth source tree.
3873 buffers (424/262/224/2828/7/7/7/7/107), 16 sites each, 903.49344um2.
Capture mux/FF/AO21/NOR area stays in the already-counted 62705.9um2 base;
no duplicate capture charge. Existing eight ICG cells are also already in base.
No data mux, MAC or memory-byte traffic is added by this analytical clock tree.

SS BUF input cap 1.121fF, output max-cap 368.64fF. ICG CLK 2.0635fF,
GCLK max-cap 46.08fF; DFF caps come from source SS cells. Four logic trees
unbuffered exceed ICG max-cap and are retained as meaningful negative controls.
Fixed wire-sum bounds: 500um per buffer output net, 25um per ICG output net.
Nominal source clock RC C=.145426, interpreted fF/um in this library unit system,
guarded by 2x. Fixed load ceiling is half the source max-cap. This is conditional
nominal wire pricing, not extracted SS/FF RC, slew or max-length route evidence.
The source-root leaf worst case includes all eight ICG inputs plus 24 flops;
there cannot be 32 ICG pins. Additional wire bounds are explicit in each witness.
Total buffer-output wire upper allocation is 1,936,500um plus 200um ICG outputs.
It is a sum of allowed lengths, not a measurement or feasible routed topology.

Nine exclusive abstract clock strips: four demanded M5 tracks need six physical
48nm tracks under actual source routing-capacity adjustment0.25, rounded outward
to six 54nm site columns. 54 columns x625 rows=33750 sites (492.075um2)
charged outside macros, eight escape channels and existing halos. Per internal
branch four clock wires; leaf branches can need 32 terminal wires locally.
The four-usable-track spine budget is not permission to route all 32 terminal branches
through one shared cut, and no spatial endpoint grouping or channel location is
proved. A cut carrying all32 branches would need43 physical tracks under that
adjustment, not six. M5 pitch is validated against archived actual tracks.

Integer 50% density: original 617 rows cannot fit the priced reserve; 625 rows
can, with 39.46534um2 spare cell capacity. Without clock channels the buffer
reserve alone needs 623 rows. New outline 1002.89x173.07um, unchanged width,
height +2.16um. Existing conditional macro/capture coordinates still fit gross
boundaries; no relocation of them or new executable placement is proposed.
Unified model: 45 stages /224 dies remains sufficient; field requirement
454.145361mm2 vs457.965497mm2 usable, preceding 44-stage geometry fails.
No rate/headline change is emitted; LAT8 is retained solely for geometric pricing.

Clock protocol remains a blocker: ungated flops see seven buffers; gated sinks
see fourteen plus ICG delay. Equal depth within each separate tree is not equal
clock phase between those groups. Finite-table delay maxima sum to 2128.518ps
or4257.036ps for seven/fourteen buffers, excluding wire/ICG. These are not period
limits or actual insertion delay. Table output-transition maximum 478.147ps
exceeds the next input table domain maximum320ps; light singleton loads may be
below minimum load5.76fF. Actual slew/domain consistency is unresolved.
Added architectural cycles, phase compensation and wake/reset exactness are
UNKNOWN, not asserted zero. Constraints stay1.2GHz, SS60ps /FF25ps uncertainty.

Next admissible input is a source-bound spatial clock/PG interface proving the
charged strips and leaf branches coexist with conditional capture bins, then
protocol/phase and SS/FF timing evidence. No new P&R is admitted by this receipt;
tap/endcap, extracted RC, candidate PG/vias/IR and hold repair remain unpriced.
