# Positive range-pipeline critical-path attribution

Fresh STA on the attributed mapped netlist identifies mul_lower.running/busy
as the launch and mul_lower.b_work[1] as the endpoint. This is a multiplier
control-to-payload path after range reduction pipelining, not a claim that the
range arithmetic remains critical. analyze.py verifies cell types, pins and
bijective net-bit correspondence before recovering pre-ABC register names.

Reproduce synth.ys with pinned Yosys, normalize mapped.raw.v using
run_abi3_physical.normalise_netlist, run sta.tcl with pinned OpenSTA, then run
analyze.py. Saving JSON can change aliases; the analysis always uses fresh STA
on this same mapped netlist. Large build JSON files are hashed, not committed.
This is prelayout evidence only. The active range pipeline route is unchanged.
