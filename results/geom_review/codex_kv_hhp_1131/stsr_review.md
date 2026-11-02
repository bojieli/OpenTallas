# HHP existing st_sr residual constraints

Read-only extraction from the already completed HHPclean A/B geom.tsv dumps, with no new audit/container/P&R. All non-clock combinational cones are followed through BLK cells and stopped at the first native sequential endpoint or boundary pin. Multi-driver sources are retained. Data and reset incidence are both included; this TSV has only a clock/non-clock terminal flag, so no ungrounded per-terminal reset classification is claimed.

Each existing st_sr[0/1] has exactly one incoming boundary pin, pc__cfg_stack[0/1] M5 at(234.216,362.784)/(233.832,362.784), and two outgoing native FFs, the corresponding u_cdc.stack_q[bit] and u_chain.sst[bit]. All are buffer-only paths. There are no other first-sequential neighbors or direct output pins. The JSON retains exact instance names, endpoint coordinates and all incidence.

A worst outgoing distances407.565/410.157µm and B407.187/392.337µm explain the four/two residual captures. A model moving only the existing st_sr cells5.4µm W and keepingY unchanged yields worst404.757µm across A/B, with direct input reach below12µm. This is a geometric feasibility model only: actual row/site occupancy, DPL legality, clock placement/timing and source integration remain owner work. No new flop, clone, pin, cycle or physical adoption is proposed here.
