# smh_rp4ahs_r4sp

Bounded MAIN same-clock structural repair for the actual r3 half. Source RTL, eight hard-child views (including prior PVM s4a), ports, parameters, outline and relay stations are identical to dab853bf3 r3a. No added functional cycles. Parent and die STA remain mandatory. Root authorized this bounded diagnostic after the actual model; it is not geometry approval or a timing waiver.

Actual model: results/arch/codex_smh_clock_1021/actual_clock_model.json records exact LEF clock-pin geometry, immutable insertion-reference SHA256, boundary and internal TT/FF spreads. K64 physical clustering did not create independent regions and failed aggregate244.8TT/218.3FF. Those failures remain preserved. Replacement is a centre-bbox symmetric bisection tree, separate hard-child insertion leaves and150um clock-wire segments; leaf partitions 60um with at most8 sinks. No SDC or phase change, generated clock, or region relabel.

SAFE checklist:
1. Pins: unchanged registered RTL boundaries and existing two-stage reset landing. Same-region interface exception retained from r3; no new interface edge.
2. Reach: unchanged LR2/XB2/gather FIRM relay stations with existing approximately330/390um data-hop plan. Clock segments150um. Actual route timing decides.
3. Fanout: unchanged kept per-slice valid/control copies. Prior r3 README reported mapped max24/28; new actual mapped native census MUST run and admit <=32 before any layout. No new native PASS inferred.
4. Depth: only clock buffers change. Functional combinational graph unchanged.
5. Storage: unchanged hard SRAM views and small publication/tag pipelines; no added functional flops or arrays.
6. Floorplan: unchanged eight children on43.2um lattice, W channel172.8um, E channel43.2um, full cell bands and existing relay plan. Actual PNG/census/fill/channel review required before submission.
7. Clock: single clk, real child refs112.9..485.5TT/94..393.9FF; insertion-aware symmetric topology. ALL measured childBOUNDARY refs across all actual clusters must meet <=80ps TT/FF under existing export rule. No selected subset. PVM intrinsic full-internal111.6/109.9 and XS123/89 retained as facts; actual leaf/parent/die STA decides internal paths. io_hold_margin0.03. Gate result pending.
8. Schedule: static. Zero added cycles vs r3a. South gout remains existing+8, other priced r3 edges retained. No schedule adoption before CLOSED and die binding.

Exact prior behavioural source witnesses at results/arch/hbm_smatt10_1020/bench_r3gs2: MUT0 PASS12796, MUT1/2/3/5/6 FAIL, Verilator5.050. RTL/params unchanged; closure daemon reruns the exact declared benches. No new behavioural PASS claimed.
