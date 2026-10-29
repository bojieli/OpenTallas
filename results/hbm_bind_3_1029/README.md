# HBM SFU drain-only interface candidate

The actual SFU output-store instance uses only lane writes and two sector drains; its unused lane-read, stage-write and single-word landing inputs were tied to zeros at the parent. The drain-only wrapper applies those same constants internally and removes those inputs from its public interface. This preserves every retained cycle and bit, and avoids presenting 2,048 live tied input bits as die interfaces. No latency change.

The actual shape (16 banks, 16 lane writes, two 8-word drains, 32,768 words) passed 12,304 cycle-exact lockstep checks, including 6,145 nonzero drain observations, all rows, three reset interruptions and write/read conflict fault cases. The seeded candidate write-data mutant was caught at check 2,052. This tests the wrapper mechanism with behavioral SRAM; physical sign-off is not claimed. Logs and bench are adjacent. Inherited strict bind using the wrapper (intel1 hbm-bind-3-1029/b1) reports zero tied bits, 158 unplanned partition pairs and the unresolved native128 reset EMIT; that run does not qualify the whole die.

The wrapper is a candidate for the SFU parent output-store specialization, not a relaxation of R7. Source assembly substitution must require the removed ports to equal their declared zero values, as the existing substitute_inst mechanism does.
