R25 GUNIT CW station: PRIVATE source/plan/transport candidate, not adopted

Existing R25 event117e37566c explicitly intended NEW unit_i0+1 CW configuration stage. The current event3 source has only u_bin_unit_i0, with no pad or u_ist stage, and lane unit__seqhost__gunit has fixed_cycles0/default. This packet supplies the missing intended stage and prices it rather than silently changing a kit.

prepare.py takes the current event3 plan, genuine native bound gunit wrapper, output directory and --tools pointing to tools/die_plan. It changes ONLY that lane fixed_cycles0→1, preserves every other plan value, uses the existing intended station coordinate[1440.08,328.32], and invokes the real kit_istations IN materializer. It intentionally selects ONLY unit_i0, so the separate R25 xtier_o0 proposal is not implicitly changed. Source helper snapshot used here: e7c2de2b57b8d597901eafc2213c2a7e026facb2. Original wrapper came from intel1 die-s81-34/ev3bind/out/rtl/s81p_gunit__t1.sv; originals were never edited.

Schema composition before/after:72=52crossedFT+2boundary+18landing+fixed0,pad0;73 adds fixed1. Exactly one lane changes; all others, including reverse lanes and R8 group padding, remain identical. The private full candidate plan is generated, not checked into this packet; receipt.json identifies its exact source. Canonical unit bus capacity remains267 payload bits. Genuine bound source has265 live payload bits plus epoch; the materialization excerpt explicitly normalizes to that actual265 and does not invent capture for the two unused capacity bits. Parent ABI reconciliation remains an obligation.

The actual full native wrapper source diff adds one ot_dp_st(W265), retargets exactly the three native L2 CW readers(cw_a/cw_d/cw_v), and updates its lane header73. Logical resource cost is265 reset-less data FF plus one asynchronously cleared epoch FF; full mapped count/clock load has NOT been measured. Existing parent rst_n alias and all child reset connections are unchanged.

Functional cut proof uses the real extracted ot_dp_st and actual u_bin/new-u_ist source lines plus the actual native three-reader word ordering. It observes only this transport cut, with no emulated L2 logic or fake black box, and does NOT assert full GUNIT/BoundDie equivalence. At833ps,12000edges, cold64 and two warm64 resets, four-state data,48192 checks pass with zero errors. The old CW data delayed one edge matches the new source. Genuine wrong-depth bypass control catches11997, stage-D payload mutation11997, and stage-reset-disconnected mutant3 (including both warm asynchronous assertions). Initial asynchronous check setup had one testbench time-zero reset-event race; the failed bench is retained and corrected stimulus explicitly drives1→0 after1ps. No RTL reset contract or64-edge duration changed.

Reproduce the cut proof:
python3 make_cw_miter.py
iverilog -g2012 -s tb -o /tmp/cw.vvp ot_dp_st_native.sv cw_native_cuts.sv tb_cw.sv
vvp /tmp/cw.vvp

Physical CW per-bit sites, timed reset/clock admission, current parent cell cap, complete programme/calendar exposure and full source/event coherence remain required. No old BoundDie EQ, parent view, SIGNED count or G5 credit is claimed. A generic composer that ignores this CW lane cannot establish zero cost; DS token worker owns the exact admission/programme price.

Preparation correction retained: first recipe inferred the module name from the snapshot filename original.sv, yielding a wrong manifest module name even though generated RTL text was correct. prepare.py now parses the actual module declaration and writes the matching filename/manifest. Final published gunit_candidate.sv matches receipt candidate SHA; its extracted native cut is byte-identical to the exercised miter cut.
