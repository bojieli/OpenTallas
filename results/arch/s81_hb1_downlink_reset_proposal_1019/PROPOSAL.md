# HB1 all-stage downlink authority reset: bounded source proposal

**Full parent first-authority HOLD. No implementation is admissible yet.**
The selected 120 existing authority FFs can share five genuine existing VP
regional reset owners at 31 logical loads per owner. This removes the need to
invent another release tree for those120 pins. The complete selected parent's
upstream reset distribution, actual hardened clock phases, native owner/polarity
join, physical reach and first genuine publication are still NULL. These are
required inputs to a structurally complete source implementation.

This packet changes no RTL and launches no RTL execution, compilation, synthesis,
OpenROAD or gate. `proposal.py` only enumerates finite source endpoints, checks
frozen source identities, and performs pinned Liberty arithmetic. It retains
`e99b83c04`/`edd84d4c3` source, analytic failure history and their nonexecuted
zero-clock witness. The arbitrary-state SAT counterexample is not a
production-reachable failure. `5975a35d7` supplies capacity methodology only;
its diagnostic face2 and841-copy reset assignments are not parent evidence.

## Exact boundary and all120 endpoints

Selected source is `ceaed19c4`, `ot_s81sl_slice`, HB1/DL4/DR6/DX6/VQ_XMEM2.
Parent SHA526a95589c304844c5757b257c37b08a8546586ce8ec713a3f50d9eb5eebe28b;
XR SHA cc31c2d1607af9e0ac41357d3afaf19e6665b4f94ce4911e2dcaf078ec1167c3.
Eight exact source snapshots and full hashes accompany the proposal. Parent
`lf[k].u_dn.gd.r[j][b]`, k=0..4/j=0..3, has authority bits:

| Role | Packed bit | Actual source | Actual registered consumer |
|---|---:|---|---|
| c_v |593| XR c_v[k] | u_lf.u_vp.cv_c |
| sw_v |432| XR sw_v[k] | u_lf.u_vp.swv_c |
| cw_v[0] |156| CAP cw_s/cw_n bit2k | u_lf.u_vp.cwv_c[0] |
| cw_v[1] |157| CAP cw_s/cw_n bit2k+1 | u_lf.u_vp.cwv_c[1] |
| rb_v |67| XR rb_v | u_lf.u_vn.rb_v_c |
| g_v |34| XR g_v | u_lf.u_vs.gv_c |

`proposal.json.authority_endpoints` names each of the120 individual states,
D predecessor, proposed RESETN/SETN owners and actual source consumer. The
unmodified source relay is an unreset594-bit shift register; the proposed
private valid/payload split would convert only these120 FFs from HQN to ASR.
The11,760 other FFs, payload bits, D equations and four data stages remain.
There is no RTL split in this packet. Native instance/master/polarity fields
are explicitly NULL because no selected parent mapped inventory was supplied.
Naming an RTL bit is not a native source-equivalence measurement.

## Five existing owners and finite local load expansion

For each leaf k, use the existing
`lf[k].u_lf.u_vp.u_rr.relay_q[0][0]` (`rs_c`) as the candidate
RESETN owner. VP source lines73–83 bind this state and every existing load.
The existing output drives ONLY seven source FF RESETNs: cv_c, swv_c,
cwv_c[0], cwv_c[1], hqv_c, xrv_c, xwv_c. No D or SETN consumer is hidden on
this output. The proposed addition is that leaf's24 authority RESETNs.
Therefore total logical output demand is31, including all preexisting loads.
BUF/INV trees are not counted as repaired fanout. No new release FF or raw
reset input is added by this local connection.

The actual existing VP relay equations are unchanged:

- sync0.D=1; sync1.D=sync0; each of four region.D=sync1.
- All six relay FF RESETNs are the parent's rst_n, all SETNs tie high.
- sync0 Q drives one D; sync1 Q drives four D; none expands in this proposal.
- regional0 Q drives the seven original plus24 new RESETNs; regions1..3 and
  their complete downstream internal cones stay unchanged and unqualified.

The packet lists all65 preexisting local state input assignments: five leaves
×(six existing relay states + seven existing input-authority states). This is
an exhaustive **local changed-owner** D/RESETN/SETN construction. It is not a
claim to enumerate the entire parent's reset tree. Only source-equivalent ASR
masters are priced; actual Yosys polarity/native master joins are required.

Ten dedicated real TIEHI owners make constant ownership finite without
assuming an existing global tie has spare capacity. Per leaf: one owner drives
24 new SETNs; another drives the six relay SETNs, seven original pin-authority
SETNs and sync0.D, totaling14. All190 constant terminals are enumerated, with
maximum24 loads. Old shared tie area receives no removal credit. No live output
or data field is tied. The 32-load combinational/tie rule remains mandatory
for all other parent nets.

The source parent connects raw rst_n to XR and all children directly. Just XR
plus five VP/VN/VS groups already implies6 +5×3×6 =96 relay RESETN loads,
before VE/VQ/VSW/RX or CAP/XFIN/XG descendants and parent's own state. This
lower bound alone exceeds32 for a single raw owner. Existing regional outputs
are not permission to ignore that upstream expansion. There is no identified
native parent reset driver, complete terminal ledger or accepted root pulse
contract in this packet. `upstream_root_terminal_expansion=NULL`; do not claim
whole-parent fanout closure or quietly attach the120 terminals to raw rst_n.
A later proposal needs the real parent reset-source/native inventory to
assign every preexisting upstream D/RESETN/SETN load. Genuine existing same-age
parallel owners may be used only with that full assignment and cold
independent-state proof; no new release age, pulse stretcher or handshake is
part of this grant.

## Actual source equations and first-observable contract

The selected source high-level parent directly binds XR, u_dn and all five
leaves to the same clk/rst_n. Each VP/VN/VS/XR regional reset is the actual
2-sync +1-region relay. Define E0/E1/E2 as the three release edges; regional
reset rises after E2 and its consumer first executes the nonreset branch at
E3. Reset assertion asynchronously clears the relay owner and all120 selected
ASR states even with zero relay clocks. The source D recurrence on a qualified
edge is exactly q0'=source_valid, qj'=q(j−1); the pin consumer samples old q3.
Payload movement is unaltered. Each owner is the actual regional state,
not an independently initialized duplicate. Cold owner assertion, reassert,
release recovery/removal and distinct stopped clocks still require proof.

The five leaf clocks are individually recorded in `calendar`: each source
connection is `clk`, and each selected hardened clock/phase binding is NULL.
VP's reset state also controls rb/g relay bits consumed by VN/VS; that is
permissible only after their real relative reset/clock contracts are bound.
It must not be inferred from a single common module-port name.

Source-specific publication equations matter:

- c_v[k]' = tg[0] ? lmask[k] :0 under XR rs_o. Input capture at E3,
  classification E4, earliest genuine local CTL publication E5; u_dn captures
  no earlier than E6, stage3 publishes E9 and VP samples at E10.
- sw_v[k]' is0 by default, becomes1 for old ub[k] or rwr[k], under rs_r.
  Genuine CTL rwr is classified at E4, so local publication can be E5; real RD
  packet/unpacker publication can be later. Same local lower dates E6/E9/E10.
- rb_v'=rbv under XR rs_o, with rbv'=actual x_rbv under rs_c.
  g_v'=egv_c under rs_o, with egv_c'=actual eg_v under rs_c. Local pipelines
  can publish no earlier than E4, followed by relay E5/E8 and VN/VS capture E9.
  Actual XFIN/EG producers require their own upstream work; E4 is a local
  lower bound, not an observed complete-source first word.
- Both cw_v bits come from CAP, not XR. CAP wires the actual u_rt outputs:
  root cw_v is cleared under its own rs_o; its3-edge relay makes E3 a lower
  bound for a nonreset output branch. Genuine complete-row d2/d3 decode,
  input return/calendar and SRAM pairing data determine the later actual
  publication. Its exact genuine first date is NULL here, not E5 borrowed
  from CTL. `ot_s81sl_cap_rt.sv` lines307–343 preserve that actual equation.

On the common-source-clock calendar all these source publication lower bounds
follow VP rs_c release; the proposed reset cannot discard an earlier genuine
word in that calendar. No additional warmup or data edge is introduced there.
The exact physical source publication, reset recovery/removal, macro internal
write/commit edge, VN/VS relative phase and compiler date remain NULL. This
source argument is not a native timing or execution receipt.

For independent clock release the same conclusion does not follow. A running
XR/CAP and u_dn may publish a genuine one-edge word while VP's clock is
stopped and its regional reset remains low. All-stage clearing then suppresses
that word instead of letting it advance. A later-running consumer can likewise
be held in reset past a genuine relay word. Stale-word exclusion and
first-word preservation are separate obligations. Root has not bound these
clock calendars or a static valid-publication schedule to the selected native
views; a stopped-clock analytic witness is not a production fault claim.
The source proposal therefore remains HOLD even though local fanout fits.

Before implementation, require for every one of the six roles in all five
leaves: each genuine source publication is sampled only after the chosen
owner is high, all required relay edges occur, and the correct consumer reset
is high when it samples old q3. Bind that predicate to actual regional clocks,
source epochs/configuration, inherited assertion/release and compiler dates.
No quiet boot, all-streams-from-XR assumption, warmup mask or delayed valid can
stand in for this first-observable contract. The reverse80-authority uplink,
DR/DX, registered parent boundaries and841-copy retention remain separate HOLD.

## Full bill and outstanding qualifications

Using the pinned actual TT/FF ASR versus HQN primitive library values:

| Cost | Value |
|---|---:|
| Converted existing FF |120; added state/data edges0|
| FF area delta |10.49760um²|
| Dedicated ten TIEHI area, no old-area credit |0.43740um²|
| Primitive plus dedicated ties area delta |10.93500um²|
| CLK capacitance delta TT/FF |−1.420440/−2.262960fF|
| New RESETN capacitance per VP owner TT/FF |17.754960/19.269816fF|
| All31 RESETNs per VP owner if mapped ASR TT/FF |22.933490/24.890179fF|
| New120 SETN capacitance TT/FF |129.534000/139.735200fF|
| Additional tie PG terminals |20|
| Converted FF PG terminals retained |240; PG count delta0|
| Local185 ASR +10tie expected PG terminal universe |390|

The negative CLK delta is an actual master difference, not a claimed clock
power benefit. New dedicated old-constant owners also carry65 existing SETN
loads and five actual constant-D loads; SETN and actual primitive D caps are recorded; native
mapping and output electrical legality remain NULL. Tie outputs have no
Liberty max-cap characterization here; ≤32 load count does not establish slew.
Every expected VDD/VSS terminal must be audited against its real connected
ITerm/net after any future implementation, including ties, ECO cells, CTS and
all parent descendants; no net-only PG PASS is sufficient.

10.93500um² is a complete priced local primitive/tie construction, **not the
full structural bill**. Actual upstream reset distribution, cell polarity,
retention, physical reset-wire capacitance/slew/405um reach, recovery/removal,
clock tree changes, PG routing, outline/band, native mapping and parent
terminal universe are unknown. Their cost and whole structural cost are NULL.
ROOT should keep implementation/native admission held until the parent reset
inventory and publication/phase contract are supplied; no new hardware is
silently authorized by this proposal. Afterwards a minimal default-off private
valid/payload split needs exact dated full-width behavior, cold arbitrary
payload, between-edge assertion/reassert, independently stopped source/relay/
consumer calendars, all six authority bits, and causal omitted-stage,
misbound-owner, first-word-loss and reset/age mutants before any separate native
admission. No broad841-copy source transformation is implied.
