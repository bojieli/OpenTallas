# HB1 selected parent valid-reset structural model

This is a bounded source/equation model requested after edd84d4c3. No RTL was
changed, executed, compiled, synthesized, routed or qualified. The old arbitrary
state SAT witness and the nonexecuted parent reset-gap witness remain intact.
Neither witness proves a production-reachable fault. This packet does not
qualify all 841 added HB1 copies.

Selected source is ceaed19c4, `ot_s81sl_slice`, HB=1, DL=4, DR=6,
DX=6, VQ_XMEM=2, VS_MUT=0. The parent directly connects rst_n and clk to
XR3 and its five leaves. Exact XR SHA is cc31c2d...1167c3 and parent SHA is
526a9558...eebe28b; full source hashes are in model.json. The 357fb wrapper's
two UNRESET reset-face FFs are a different boundary; they are not present in
this selected parent. No claim binds the selected hardened views to these
high-level clock/reset ports.

Each downlink packs 594 bits into four unreset stages. From the LSB, authority
bits are g_v[34], rb_v[67], cw_v[1:0][157:156], sw_v[432], c_v[593]. There
are 5 leaves × 4 stages × 6 authority bits = 120 existing valid FFs, and
11,760 other FFs that remain unreset. c_v, sw_v and cw_v terminate in VP's
cv_c, swv_c, cwv_c; rb_v terminates in VN's rb_v_c; g_v terminates in VS's
gv_c. Each consumer uses the actual 2-sync + 1-regional reset relay. VP data,
address and mask pin FFs stay unreset. swv_c plus masks enables actual SRAM
writes. Clearing c_v/cw_v/rb_v/g_v also avoids treating a sw-only repair as a
whole-downlink contract. These are finite static streams, with no ready/credit.

The reverse four-stage u_up link is separately inventoried: width667, authority
lo_v, p_v, xf_v and e_v; xf_s is a mode sideband, not another valid. It has
80 existing authority FFs across five leaves/four stages. It is outside this
minimal XR→VP write-authority repair, and is not qualified by a 120-FF proposal.
Other DR/DX/capture/fault/clock paths are likewise unchanged and unqualified.

## Exact recurrence and stopped-clock boundary

Let q0..q3 be valid relay states before an edge. The inherited recurrence is
q0'=source_valid, q1'=q0, q2'=q1, q3'=q2. Consumer pin FF samples old q3.
During an async assertion all selected ASR stages become zero without a clock;
other stage values remain arbitrary. Payload recurrence is unchanged.

With one common root clock, after release E0/E1/E2 advance the actual consumer
reset relay, and E3 is its first capture. Resetting only stage0 makes its zero
reach q3 after E2. Exhausting all16 initial states and all16 stage-reset masks
shows stage0 is necessary and sufficient for this particular source-invalid
prefix and common-root calendar. sw-only5/all-authority30 conversions are
therefore PHASE-CONDITIONAL sensitivities, not the selected safe repair.
The script preserves the original no-reset stale-valid trace at E3.

The required stopped-clock case invalidates that minimum: VP may receive its
release edges while u_dn is stopped. If u_dn starts at E3, old q1..q3 are still
eligible. Resetting only the last stage also fails as old earlier stages later
arrive. Exhausting all16 states/masks across a stopped relay and four restart
edges shows all four valid stages must clear to exclude every old relay word
independently of the downstream release calendar. For sw this is20 conversions;
for all six downlink authorities it is120. Reassertion while stopped has the
same clearing equation. An omitted stage is a causal analytic counterexample.
This is a local old-relay-state result, conditional on a genuinely reset and
correctly published source; it is not a complete asynchronous-domain protocol.

For the selected unwrapped common-clock source, release E0→E2 releases XR and
VP regional resets. Earliest genuine target5 input capture E3, classification
E4, XR sw_v/body publication E5, downlink capture E6→E9, VP capture E10,
SRAM interface eligibility after E10/sample E11. All dates are pre-/post-edge
explicit and no extra warmup or data edge is proposed. The macro's internal
commit edge remains unbound. Diagnostic face2 instead shifts the source's
regional release by two inherited edges; these calendars must not be mixed.
The rwr[0]13-copy common-D event is before E5 genuine publication, only after
its actual clock/reset authority is established. No other copy family inherits
that local proof.

## Cost and reset-distribution obligation

model.json prices actual native ASAP7 DFFHQNx1→DFFASRHQNx1 master conversion
using pinned TT/FF Liberty, not an assumed parent synthesis census. The 120
conversions add 10.49760um² primitive FF area, change CLK pin capacitance by
−1.420440fF TT/−2.262960fF FF, and add RESETN load88.774800/96.349080fF and
SETN tie load129.534000/139.735200fF. State count, payload storage, arithmetic
and data-stage count are unchanged. Negative CLK delta is the library's actual
master difference, not a system clock-power benefit. The 20/30/5 sensitivities
are in model.json. A mapped parent conversion, hold/timing, PG and physical
area are NOT measured.

This is a primitive lower bound, NOT the full structural bill. Directly adding
120 reset terminals to one raw rst_n violates the <=32 logical fanout rule;
BUF/INV trees do not repair that rule. At least four genuine authority drivers
are needed for these120 reset endpoints, plus existing reset loads. SETN also
requires at least four physical TIEHI owners for120 terminals, plus any new
reset-state SETN/D loads. Their exact finite assignment, source-driver copies,
area, CLK/reset caps, placement, root pulse reach and PG remain NULL. Inserting
a new synchronous reset-release tree without proving the earliest real source
publication can discard first words or add effective startup edges. It cannot
be priced as zero latency by assumption. Copying an existing parent reset
source is permissible only after its actual owner/age/phase is identified.
The root waveform authority and final selected hardened-parent phase binding
are therefore explicit prerequisites to a complete minimal source proposal.

## Root pulse-authority alternative

No actual reset driver or accepted pulse-width/clock-running contract was found
in the selected slice boundary or edd84 packet. The root-pulse alternative is
an obligation, not an observed feature or a zero-cost adopted policy. In the
common-root unwrapped equation, one asserted clock edge after XR valid has
cleared plus the inherited three release edges flushes the old downlink before
VP's first capture. Four extra held-reset edges are NOT necessary there.

With independently stopped clocks, elapsed pulse time alone proves nothing.
A real root authority must guarantee (1) every source child actually receives
async assertion, including any unreset-face wrapper's required low captures;
(2) each u_dn clock receives enough source-invalid shifts before its consumer
is eligible; (3) reset reassert cancels the same epoch; (4) publication follows
actual reset release/phase at each selected domain. One sufficient stronger
condition is four actual u_dn invalid shifts after source-clear before consumer
eligibility; the exact minimum depends on selected phase and is NULL. An
unbound always-running assumption or an invented startup delay is unacceptable.
If an existing external authority guarantees those events it may need zero
new local FFs, but its owner, hardware cost and compiler/boot timing are NOT
established. A new pulse stretcher/handshake is outside this grant and cannot
be silently inserted into a static schedule.

## Review outcome and proposed next boundary

Retain parent first-authority HOLD. Prefer the all-stage valid-only clearing
candidate for robustness to stopped relay clocks; it still needs the genuine
reset-driver distribution and selected source-publication binding above.
Stage0-only variants are sensitivity results. Root may instead select an
actual pulse/flush authority after it supplies a pinned driver and calendar.
A subsequent private implementation grant should name only the selected
parent and a dedicated valid/payload split relay, default off, leaving the
shared generic relay, payload bits, DR/DX, arithmetic and production defaults
unchanged. It must first freeze all120 reset endpoint owners and source clocks,
then prove zero-clock assertion/reassert, independent stop/restart, genuine
first-publication/all-output dated behavior and causal omitted-stage/reset
mutants. No implementation, simulation or physical engine is granted here.
