Physical preflight prototype; NO gate authorization or physical qualification.

Sealed RTL/bench/native source remains d1846d61e / source91d1b58f1.
This next branch merges current main8608a236c first. Native cell fence is the
unchanged main helper. Native all-cell ownership and stage birth bookkeeping
are scoped to LEP. All original/new/fixed standard cells must remain in one
full-width band, with no clock/timing/reach/PG exemption.

Actual 10.8um macro halo invalidates old 2.16um analytical halo assumptions.
Correct row band: x2.16..473.04,y259.2..291.6 (120 rows). Keep full core for
macro PG coverage, delete native rows outside band before tapcell, and fence
ALL non-macro cells. Data source is untouched. Native floorplan/pdn construction
and exact canonical pin planning run without GPL/CTS/route. All row/group/birth
APIs have been exercised on copied native DBs; ownership missing negative and
new-birth bookkeeping positive pass. The unconnected birth fixture is ONLY a
helper regression, never functional source evidence.

First analytic site-legal packing uses exact native graph/Liberty transparency,
all current cell identities and macro/top pin boxes. It found provisional
endpoint spans>405; those are retained failures of this packing, not proven
source impossibility. Conservative full-band-y coordinate intervals narrow
standard failures to38HOST/7NH, but reject one MU control cell only because
its coordinate interval is required to support EVERY y in the band. A precise
2D/per-row constraint model is next. No RTL change is justified by this coarse
interval refusal. Actual modeled cut ratios are<=0.47 after macro/PG obstacles
and actual25% routing layer reduction. Clock/PG geometry qualification remains
open. Native PG binding snapshots are electrical-net binding, not final routed
metal connectivity or unplaced standard-cell pin contact.
