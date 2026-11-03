DISABLED T48 CB cycle repair candidate, not a canonical plan or kit.

The selected native source/consumer witness b6ce71c32 establishes a conditional
slot collision for independent adjacent ca/cb packets on current59/58 cycles.
Their first eight feedthrough counts match; the last bridge, s_4N_x06 /
slice_station__t48, has ca ft0=7 and cb ft1=6. This proposal changes only ft1 to7.

The existing RowAllocator generates one277-cell bank (276 payload +1 epoch),
inserted as internal stage2. All previous bit sites are retained and only their
logical later-stage indices advance. The stage0 pin bank is unchanged. The
source plan digest7bf83d029cc5ffb7 becomes candidate1e1ad09b27c4ca58.
No canonical plan, physical view, live kit or source default was edited.

Model and impact:

- One changed type, one instance s_4N_x06 (MY); no hard children. Immediate CB
  path peers are s_3N_x06 upstream and bk_sel downstream. All pin geometry,
  neighbouring types, other four FT slots and source/RX protocol stay fixed.
- Only cb__s_0N_LP__bk_sel changes58→59. ca stays59; this pair's maximum stays59,
  and the whole plan's maximum stays107. One full packet and its epoch arrive
  one edge later (+833ps); same one-packet/cycle capacity, no new arithmetic.
- No source release epoch changes. The CB destination publication and epoch
  fill must be priced+1. The historical token DAG lacks an explicit ca/cb term,
  so an unchanged mapped maximum does not establish zero mission latency cost.
  Actual source/global epochs and production slot admission remain unqualified.
- Added clock sinks277: planned total7210→7487. Existing clk_t8 load554→831,
  radius143.0142/150um;20 clock pins unchanged. No new clock domain, source,
  forwarded-clock export coordinate or per-tap latency offset is introduced.
- Added one epoch reset load, no payload reset. Existing planner reset root,
  relays, tap depths and neighbour release contract remain unchanged. CB epoch
  propagation/fill gains one edge; no boot/START qualification is borrowed.
- New allocation envelope area105.00516um² (1.404×0.27×277). Data neighbour hops
  ≤265.95um. The midpoint and three nearer candidates fail clock reach and are
  preserved in report.json; the chosen candidate passes the frozen budgets.

Written change-control/re-sign list: regenerate/re-kit T48 exactly once with
actual clock/reset inventory, then independent geometry review, normal P&R,
signoff and equivalence. Re-bind the die once after the approved batched event,
regenerate latency JSON/SV, carry CB+1 to compiler/token slot admission and
re-qualify affected ca/cb seam timing/clock counts and parent composition.
Unchanged source and destination cores do not need RTL changes; their parent
interfaces still require composed timing. Existing in-flight jobs are preserved.
The proposal does not authorize any of those launches or make a mission claim.

Reproduce privately:

python3 tools/s81_dv/tokfunc/prepare_t48_cb_candidate.py \
  --plan physical/die_plan/s81/plan_h2_2249.json --out /SCRATCH/FRESH_CANDIDATE

The helper rejects output under canonical physical/ and existing output dirs.
It writes a private full candidate and report, never runs CAD. The committed
disabled_delta.json carries only the explicit three-field FT insertion, while
report.json carries the exact277 new sites, budgets and failed attempts.
The inspected picture/review is results/geom_review/s81_t48_cb_cycle_2138.

Reset precision from actual native bind_cells.sv: ot_dp_st(W276) has
276 packet flops on posedge clk only (including the in-band packet valid),
and one external epoch eq flop on posedge clk or negedge existing rst_n.
The proposal therefore adds one async-reset control-flop PIN load to the
existing delivered reset. It adds no independent async source, synchronizer,
reset tap or domain. Native recovery/removal and load still require the normal
new kit; planner topology equality is not a zero-load or reset-timing claim.
