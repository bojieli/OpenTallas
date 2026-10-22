# hbm_hc_tail_child_k6 -- HC Sinkhorn tail child (HBMc/HC-TAIL2 10-22)

MAIN (k4/k5 floorplan, pins and default CTS).

Successor of k5/k5b (k4 + Sinkhorn SC2, SKP 3, SDIV 17) with two changes:

1. Native netlist regenerated with yosys 0.68. The k3..k5 natives were mapped with /usr/bin/yosys 0.52. Its dfflibmap
   maps the ASAP7 async flop DFFASRHQNx1 (liberty ff IQN, next_state "!D", clear "!SETN", preset "!RESETN") with set and
   clear swapped, so every async-reset flop reset to the inverted value. The ot_rst_relay sync flops then never asserted
   the core reset, the core started from its power-up state, and the k5 native lockstep failed 5/48, depending on init.
   A 2-flop repro shows yosys 0.52 inverted and yosys 0.68 (the ORFS docker's) correct.
2. OPIPE 1 output pin stage. The k4b route (NEEDS_RTL, TT -201) had core -> result[224] at -487 ps in the ORFS finish
   STA, and 252 of 770 output ports were not anchored at their pins. The low 256 result bits come from final_result, a
   hold-mux register whose Q also feeds its own mux. result, result_v and fault now each land in a flop that drives only
   its pin. This adds 1 edge.

Latency: result_v at launch + L + 3 with L 989 (TR 271 + SDIV 17 + CAP 699 + 2). The child's offset over the tail unit
goes from 495 to 496. Root: TSKP 3, TSDIV 17, OPIPE 1, compiler --tail-x 494 (was 493), TE 2 unchanged.

The k4b bases[449] -> core min path (-341) is the ORFS finish report on the plain route SDC, with no IO clock reference
(clock insertion about 518 ps against a 167 ps external delay). The sign-off corner STA with the IO reference gives FF
input -> reg +25.08, so it is not an RTL item. The k4b reg2reg TT -201 (Sinkhorn) is the class that k5 SC2 fixes.

Source: rtl/hbm_accel/generic/peers/static_hc/native/ot_hbm_hc_tail_child_static_k6.v. Its recipe is
results/rtl/hbm_hc_root_safe_1020/tail_child_hc12/nl.sh, run as `OPIPE=1 nl.sh k6 17 1 3 496 1040`, which refuses
yosys < 0.68. The sha256 and the benches are in that directory.
