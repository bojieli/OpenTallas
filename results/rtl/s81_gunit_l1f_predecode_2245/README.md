# GUNIT forward ownership successor

The original smaller C gate overflowed routing by 341. The larger D route is terminal at TT -154.95 ps / FF +4.95 ps / DRC 0. Its internal row-to-forward path shares the ninth row/enable owner and one payload owner across all sixteen forward lanes. Exact original output files stay on gold2.

The opt-in source gives each forward lane its own same-edge row and enable registers and each four-lane quadrant its own payload registers. Separate reset leaves retain the original release age. New native admission and current-source functional tests remain required. No interface port or data edge changes.

The MAIN and fallback use larger clear logic planes, smaller CTS leaf groups and four real forward placement groups. Those groups include the actual forward row/enable and payload captures, forward decode, byte mux and s_val captures; they are dissolved after global placement before detailed placement. Generated pre_gpl and pre_dpl hooks bind them through supported spec fields. Actual group member counts and area are guarded in Tcl and must be checked in the real logs. Final TT / FF, 80 ps clock limits and native32 requirements remain unchanged.

The old rejected row-predecode idea was not selected: every existing raw input continues to capture directly in a register. These are successor candidates without closure credit.
