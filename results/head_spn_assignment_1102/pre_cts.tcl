# Clear only the pre-CTS LOCAL network estimate; preserve early core source latencies.
unset_clock_latency -clock clk [get_ports {clk clk_t1 clk_t2 clk_t3 clk_t4 clk_t5 clk_t6 clk_t7 clk_t8 clk_t9 clk_t10 clk_t11 clk_t12 clk_t13 clk_t14 clk_t15 clk_t16 clk_t17 clk_t18 clk_t19 clk_t20 clk_t21 clk_t22 clk_t23 clk_t24 clk_t25 clk_t26 clk_t27 clk_t28 clk_t29 clk_t30 clk_t31 clk_t32 clk_t33 clk_t34 clk_t35 clk_t36 clk_t37 clk_t38 clk_t39 clk_t40 clk_t41}]
# plan clock.tap_window: restore the golden per-tap window before the tree (propagated + CRPR)
set_clock_latency -source -early -clock clk -70.0000 [get_ports {clk clk_t1 clk_t2 clk_t3 clk_t4 clk_t5 clk_t6 clk_t7 clk_t8 clk_t9 clk_t10 clk_t11 clk_t12 clk_t13 clk_t14 clk_t15 clk_t16 clk_t17 clk_t18 clk_t19 clk_t20 clk_t21 clk_t22 clk_t23 clk_t24 clk_t25 clk_t26 clk_t27 clk_t28 clk_t29 clk_t30 clk_t31 clk_t32 clk_t33 clk_t34 clk_t35 clk_t36 clk_t37 clk_t38 clk_t39 clk_t40 clk_t41}]
set_clock_latency -source -late -clock clk 0.0000 [get_ports {clk clk_t1 clk_t2 clk_t3 clk_t4 clk_t5 clk_t6 clk_t7 clk_t8 clk_t9 clk_t10 clk_t11 clk_t12 clk_t13 clk_t14 clk_t15 clk_t16 clk_t17 clk_t18 clk_t19 clk_t20 clk_t21 clk_t22 clk_t23 clk_t24 clk_t25 clk_t26 clk_t27 clk_t28 clk_t29 clk_t30 clk_t31 clk_t32 clk_t33 clk_t34 clk_t35 clk_t36 clk_t37 clk_t38 clk_t39 clk_t40 clk_t41}]
source /work/clock_taps.tcl

set rt_postplace 1
set rt_leaf_reach_um 405
source /work/reset_taps.tcl
unset rt_postplace
