# T41 mixed-owner forwarded exports: real consumer gap, no one-tap gate

Mixed ownership is not itself an electrical/timing failure. The actual Anear
SDC creates one clk with78 real input sources at833ps and a per-source
[-140,0]ps early/late latency window. That explicitly prices different taps;
GROUP_RE stays OFF. Actual post-hook Anear cap1500/0empty/radius189.579um is
retained. Personally LOOKED /home/ubuntu/coord/tmp/t41_actual_1101/Anear.png;
raw whole geometry failures remain, no CTS/GRT/route PASS is inferred.

Actual bound RTL s81p_slice_station__t41_bound.sv lines80/81/83 forwards ft0,
ft10,ft12 from clk_t8,clk_t68,clk_t69. The SDC generated clocks use those same
sources. landing_exports.tcl physically connects each through one BUFx24 at
its declared source. Mixed final-stage owners are actual: ft0 has957t8,
147t74,1t21; ft10 has461t68/52t69; ft12 also mixes owners. No ownership metadata
may replace an actual per-bit clock path or force a GROUP_RE change.

The existing standard data outputs are constrained against virtual vclk,
not their fclk_out. Internal pair_skew enumerates register captures; its PASS
is not an output-data/K qualification. The concrete downstream gap is
ca_ring_fn in tools/die_plan/die_sta_related.py: its fn(A,B), using one
type-level fwd_out_ps, defines writer=A(data-launch tap)+forwarded delay.
That assumes the actual forwarded root F equals launch root L. For mixed
L!=F, reusing this calculation assigns the wrong writer phase even though
all78 sources are declared correctly. The helper cannot identify distinct
exports of one part or their declared source roots.

Minimal consumer/API contract: per output bit/connection retain (L,F,R),
where L is the actual launch FF clock/source, F the named fclk_out and real
source_clock_port, R the actual receiver local-read root. Qualify separately:
- data versus forwarded K using L<->F and actual data path/forwarded path;
- receiver writer/read/count phase using F<->R, the actual forwarded wire,
  ring write-clock path and declared falling write edge.
Keep actual source/root/edge tags, per-bit startpoint/endpoints and path
identities. Credit only a measured common path of the relevant pair; never
reuse L/R credit for L/F or F/R or silently cancel the140ps cross-root window.

ONE baseline Anear normal CTS plus read-only TT/FF witness is the recommended
next DIAGNOSTIC once a thin observer exists. It must record every exported
bit's true data Dmin/Dmax path/startpoint/root and declared F's propagated
rising/falling early/late K path, under the original SDC before zero_unc or
forwarded-clock exporter clock deletion/constraint mutation. A conservative
Dmin-Kmax / Dmax-Kmin result may be labelled an uncredited BOUND, not native
forwarded STD slack. Native vclk STD slack stays separately labelled.
Existing ring_hold sender80ps/falling-write and all source/layout constraints
remain unchanged. Positive all-bit bounds can support a sender guarantee;
a failed conservative bound is not a waiver or proof that grouping is needed.
Actual receiving-link budgets/phase and caller/source gates remain required.

No CAD was run by this reviewer. No complete forwarded consumer currently
exists in the examined deck, so no qualification/route claim is granted by
this review. Keep the real API gap explicit and use the baseline measurement
to supply evidence, rather than inventing an all-bits-one-tap rule.

Exact actual kit: Intel2 /srv/opentallas-scratch2/claude/codex-s81-bound-landing-r2-1131/Anear_corrected/gen/slice_station__t41.
Post-hook ODB/ownership: Intel2 /srv/opentallas-scratch2/claude/codex-s81-t41-ownership-r3-1546/Anear.
Private plan: Intel2 codex-s81-t41-proto-1131/Anear/plan_t41_Anear.json.
