# Existing Qwen native jobs: 2026-10-19 13:33 PT pickup

Read-only snapshot; no build, gate, restart, cancellation, submit, REVIEW.json,
source activation, or native qualification performed. Prior terminal SYSFACE
bc2/bc2c synthesis-timeout evidence and D2D native fanout failures remain in
`results/arch/qwen_gate_pickup2_1019` at ba3c19864.

| Existing run | Current actual progress | Source / eligibility |
|---|---|---|
| native59 safe3, ep7 | CTS setup repair iteration 700; WNS -1851.771 ps | 005f4ae7a; known landing-reset 45 loads, diagnostic |
| native59 safe3b, ep7 | CTS setup repair iteration 1471; WNS -792.302 ps | Same 005f source; diagnostic |
| native59 safe3c, ep6 | CTS setup repair iteration 540; WNS -124.651 ps | 3c51edcae; 56 landing copies, still unqualified |
| SYSFACE bc2l, ep8 | Yosys ABC per-module mapping around module 13188 | Original 14400-second cap; not a native fanout verdict |

All four original local clients remain live (clients.txt). Remote CTS/Yosys log
mtimes show progress. The three native59 `physical.json` files have intermediate
NOT_MET place-and-route status; this is not a terminal pre-route-gate verdict.
Repair-loop WNS is not final signoff timing or a new qualification claim.
The separate generic SYSFACE roundtrip PID 3282231 remains live at 2h35m,
83.9% CPU; it is not the native bc2l gate and must not be mistaken for it.

Each JSON records the remote directory, collection UTC, source/tool image hash
receipt, exact original log hashes and byte sizes, last 100 log lines, spec hash,
and final-artifact presence. Logs are progressing, so each hash identifies the
read snapshot only. The snapshot files are immutable committed evidence;
rerunning collect.py requires a new evidence directory to preserve this record.

No final `4_cts.odb` or gate-layout PNG exists in these four runs at pickup.
Consequently final TT setup, FF hold, TT/FF spread, full uncapped native logical
pin fanout through BUF/INV for every role, pin registration/reset ancestry,
405um stage reach, actual SRAM contact density/lattice, and final PG connectivity
are OPEN. A pin/name or existing net-only PSM check cannot certify PG: the next
collector must query actual master PG MTerms and final ODB ITerm connections for
every instance, including protected CTS buffers, and distinguish unbound or
wrong-net pins. Do not infer PASS from net membership alone.

SYSFACE remains CRITICAL: the first complete layout PNG and all checklist facts
must go to ROOT personally; no collector may submit it. Native59 safe3c also
needs complete actual native graph/current-rule/reset/readiness proof before
any submission; Q-ready age 20 remains uncertified. Preserve all original jobs.
