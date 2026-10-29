# HEAD LEP resized child: planned geometry review

Viewed `results/head_serdes_lep_0825/lep_child/child_plan.png` during the
2026-10-29 Codex takeover. Candidate is 777.6 x 492.48 um with the same 55
SRAM instances and unchanged RTL, ports, and cycles. The pin list comes from
the current RTL header and existing track planner: collective buses on W,
parent K buses on S, clock/reset at the centre.

FIFO and replay SRAMs for each 64-bit bank share a column; the corresponding
head SRAM is below them. No SRAM spans a channel. Minimum macro separation
is 14.808 um, all halos fit, and a wide centre channel remains clear for the
clock/reset and their branches. PG connections stay on the existing macro
and core grid. The wider S pin band lowers pin density; W bands remain in
order. The arrangement supplies channels across the entire outline rather
than placing a continuous macro wall between pins and logic.

Verdict: PASS-COND for plan composition and kit generation. The former
trial's H1.022/V1.595 demand scaled by available outline capacity gives
H0.896/V0.797, an estimate that motivates the trial rather than a route
claim. A fresh connected register placement must distribute the existing
pipeline stages along each macro/face path and keep every hop <=405 um.
No stale FIRM register placement may be stretched into this outline.
Review that actual register placement, clock taps and PG before routing.
