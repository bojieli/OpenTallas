SVGR_OWN RF1 head/tail candidate

Implementation source: 40139073ec3ce4fa4fca4f81d16ee5192d4f245c.
Optional trailing parameter SKID_HEAD defaults to 0 in the RF1-selected
ot_svgr_own. The non-RF1 preprocessor branch and all canonical recipes remain
unchanged. The dormant ot_svgr_own__headtail recipe selects SKID_HEAD=1 and
explicitly includes ot_svgr_rf1_skid_head.sv at the pinned implementation.
No source/profile adoption, new physical job, or main merge is authorized here.

The failed RF1A path starts at pc_owner[3].sk_rp and reaches a wide landing
FIFO capture through the indexed payload/ok read and metadata/arbiter logic.
The candidate changes only the two-entry response skid representation:
head/tail payload+ok registers replace sk_m[0:1], sk_ok[2], wp and rp. The
external decoder, arbiter, credits, FIFO clocks, handshakes, resets, and all
existing RF1 pipeline stages retain their source logic and edge schedule.

Pre-edge transition rules:

| Occupancy | Admitted events | Data movement |
| --- | --- | --- |
| 0 | push | Incoming payload/verdict becomes head |
| 1 | push only | Incoming payload/verdict becomes tail |
| 1 | pop only | Queue becomes empty; stale payload is not observable |
| 1 | push and pop | Old head is consumed; incoming word becomes new head |
| 2 | pop | Tail is promoted to head |
| 2 | requested push and pop | Push remains blocked by the original full test; tail is promoted |

An unapproved head (head_ok=0) remains in place and suppresses response_ok;
no lookahead push admission or refusal bypass is introduced. Output payload
and verdict come directly from head registers. The wide selection moves to
register inputs, instead of remaining on the read-pointer-to-arbiter path.
Payloads retain their original no-reset behavior; occupancy and verdicts reset.

The physical candidate has zero additional edges and the same two-entry
capacity and payload storage. For production LB=2, each PC stores two285-bit
payloads plus two ok bits and a two-bit count; two pointer flops disappear.
Across four PCs the expected flip-flop delta is -8. No TOK cycles are added.
This is a structural estimate, not mapped area or timing closure evidence.

Standalone full-width old-ring/new-head refinement passed1,592,864 comparisons:
all262,144 length-six sequences of push request/pop request/input verdict,
followed by20,000 randomized cycles and repeated resets. Coverage includes
20,586 full-queue simultaneous-pop/push cases that reject push,676,462 refused
head checks,58,809 push/pop edges,575,806 accepted pushes,158,788 accepted pops.
Tail-promotion loss, dropped accepted push and held-head overwrite mutants
were caught. Exact inputs and logs are under results/rtl/svgr_head_1106/standalone.

The existing whole native RF1 SMB accepted-stream proof is a separate admitted
job with the candidate as its actual path, an old-ring owner shadow on the
same face inputs, and targeted mutant shadows. Ordinary traffic, landing
stalls and replay after reset use the same binary. Its verdict is pending;
no whole-unit exactness or physical closure is claimed by the standalone gate.
TT/FF timing, DRV/DRC, and a netlist equivalence gate remain unmeasured for this
candidate. Parent owns physical source/geometry adoption and actual-image review.
