# Exact rwr[0] first authority: local convergence, parent HOLD

READ-ONLY SOURCE AUDIT. No new simulation, SAT, mapping or native job. This
covers only the thirteen physical-source rwr[0] FF owners, specifically copy4
(write-valid) and copy12 (sw_d[0] CTL override). It does not generalize to the
other added FF families or establish a parent/token reset contract.

`rwr_pin_contract.json` joins the actual generated graph to frozen mapped and
endpoint ledgers. All thirteen owners have the same D bit (the unchanged
_096952_ classifier root), same CLK and same RESETN expression from region0
copy13, with inversion1. Their SETN pins are separately distributed real
TIEHI owners, all logically high. Each is the exact DFFASRHQN master.
Consequently, a common rising clock samples identical D into every QN, whatever
those thirteen old QN values were. A common asserted RESETN also forces every
QN to1 (source rwr=0). There is no equal-power-up assumption. The arbitrary
SAT witness rwr copy12 !=copy4 cannot survive that first common sampling event.
This is a source/graph event argument, not a new executed timing/metastability
or whole-design induction proof.

The actual cc31 source captures E/W/V valid and payload at K. This-slice CTL
selection and target5/leaf0 publication register rwr at K+1; body is captured
on that same edge. At K+2 the sw_v and sw_d FFs consume that rwr/body. All
thirteen rwr owners have already sampled the shared classifier at K+1 before
this genuine CTL output is consumed. No previous send configuration is needed
for target5. The original CTL override over an active RD unpack remains the
source rule, including the existing sticky collision fault.

The reset boundaries must be kept distinct. The frozen high-level parent
`ot_s81sl_slice` directly supplies rst_n to its XR3 and VP children. The
357fb diagnostic hardening wrapper inserts two UNRESET face FFs before XR's
existing 2-sync+1-region relay. It is not evidence that the parent RTL contains
those face FFs or that the selected hardened views share a reset reference.

For the diagnostic wrapper, if A samples external reset low into face0,
A+1 propagates that zero through every parallel second-face owner. Their
common-zero assertion clears the inner synchronizers/regions and rwr owners
asynchronously after that edge. No arbitrary face power-up value is assumed.
If R first samples a subsequent high into face0, face1 samples high at R+1,
sync0 at R+2, sync1 at R+3 and regional release at R+4. The first unreset
input-valid capture is R+5, target5 classification R+6, and genuine CTL
output R+7. These are inherited edges, not additional data-programme edges.
With the unwrapped high-level reset boundary the analogous regional release
is R+2 and genuine CTL output R+5. Clock-stopped assertion and physical phase,
recovery/removal or skew qualification are not established.

The actual parent consumer path prevents a first-authority closure claim:

- Default DL is4. Parent u_dn transports sw_v and the exact address/mask/data
  together through ot_s81sl_rly, whose four storage stages have no reset.
- VP's swv_c input FF resets through its own 2-sync+1-region relay. Unreset
  swa_c/swm_c/swd_c capture the corresponding payload each edge. swv_c and
  nonzero word masks directly assert real bank SRAM write enables; there is
  no reset/config epoch fence in that write selection.
- Consider a reset assertion/release pulse containing no rising clock while
  the unreset u_dn stages contain an old valid word. XR and VP valid controls
  can clear asynchronously in the unwrapped source, but u_dn retains that old
  word. At the first three rising edges E0,E1,E2 after release, the VP reset
  relay advances; at E2 it releases. At E3 swv_c can capture the old r0 word
  which has just reached the D4 output at E2. The new XR zero reaches that
  output only after E3. A stale write request can therefore be presented to the real bank SRAM
  interface after E3 and sampled at E4, before a new XR-authored write
  traverses the path. The selected macro internal commit edge is not pinned
  by this bounded audit.

That recurrence is a source-level missing-contract witness, NOT an executed
RTL failure or proof that the released programme issues such a reset. One
sampled asserted edge can provide the missing initial zero in u_dn; together
with the inherited three release edges it can flush this particular path
before the first VP capture. It would be wrong to demand four extra held-reset
edges or quietly add them. An actual reset driver/accepted reset pulse and the
selected hardened parent/view phase binding are not pinned in this bounded
packet. They must establish the needed event if claiming actual earliest
consumer authority. No warmup, valid masking, source change or programme shift
was introduced to fill that gap.

Result: rwr copy4/12 local shared-D convergence is explicit; actual parent
first-use/reset/publication authority remains HOLD. Stop at that source gap.
