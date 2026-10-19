# Qwen forwarded clock candidate, 2026-10-19

The dv2f16 physical-clock diagnostic had all generator ports and entry sinks,
but its spine compensated the model insertion of 763 regional trees in one
die-wide DME construction. The observed spine had 677 levels and about 24k
seed pads; measured regional skew reached 9.6 ns. This is a topology failure,
not evidence that clock ports or a latency constraint should be removed.

`DC_SPINE_TOPOLOGY=forwarded` selects a distinct physical candidate. Recursive
spatial bisection creates a binary distribution tree whose repeaters feed local
regional roots. It applies no model-insertion compensation and creates zero
seed pads. Local region trees still compensate their own tile insertion;
measured TT/FF trim still matches only the explicit communicating-neighbour
pairs. Every physical arrival includes the source, delivery tree, and local
region tree. Non-stream periods retain a physically connected generator path.
The default DME topology is retained for existing runs and evidence.

The dv2f16 input has 765 regional trees, 763 at the stream period, no shared
balance groups, and 114 directed unlanded root pairs (one connected component
of 57 regions). A binary spine needs 762 branch nodes plus 763 leaf drivers
before routed repeaters; its pad count at construction is exactly zero.
Physical clock-cell area, wire reach, insertion, slew and TT/FF skew must come
from the measured diagnostic. Some original regional trees themselves have
model insertion above 6 ns, so this candidate does not establish that the
generator's region partition is physically adequate.

The candidate uses the strict obstacle router, with no 1.2-mm macro-escape
fallback. Every constructed delivery segment is checked against 405 um and
every distribution node has fanout at most two. An unreachable entry fails
with a corridor error and requires physical repartition or relay space.

Safe-design review for this diagnostic:

| Item | State |
|---|---|
| Registered interfaces/reset | Existing die/landed crossings retained; no RTL change |
| Reach | Delivery routes reject segments above 405 um; placement displacement still requires physical audit |
| Fanout | Forwarded delivery has at most two loads per node |
| Logic depth | Buffer-only delivery; measured insertion reported, no global skew target |
| Storage | No new storage arrays or delay-line RTL |
| Floorplan | Copies the placed dv2f16 ODB; new cells use existing legal-site placement outside macros |
| Clock | TT/FF measurement and all communicating-neighbour <=80 ps are required; pending |
| Schedule | No data-cycle change; existing landed window drift must pass before adoption |

Run on the fleet using a distinct copy of the prepared clock inputs:

```bash
python3 tools/die_clock/test_spine.py
DC_SPINE_TOPOLOGY=forwarded DC_SPINE_TRIM=1 DC_ITERS=4 \
  DC_REQUIRE_PASS=1 bash tools/die_clock/qwen_compute_dieclk.sh spine "$D" forward1
```

`DC_REQUIRE_PASS=1` rejects a failed/incomplete neighbour result, failed
intra-region classes, or unclaimed diagnostic sinks after preserving all
measurements and plots. A successful shell build alone is insufficient.
The diagnostic remains TT/FF pathfinding evidence until actual clock routing,
clock DRV, landed windows, SS/FF die timing and placement legality are qualified.

Original input is read-only evidence at
`ot-epyc4:/srv/opentallas-scratch/claude/qwen-split-compute/dv2f16/chain/dieclk`.
Candidate input and output are separate at
`/srv/opentallas-scratch/claude/codex-qwen-dieclk2-1019/forward1`.
The progressing dv2f18dh2 chain is untouched.
