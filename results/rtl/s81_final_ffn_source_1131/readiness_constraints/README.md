The selected native64 receipt measures SRAM read pair `i` at registered CV+3+i,
native output at CV+5+i, public output at CV+6+i. Readiness now has an exact
integer-edge constraint: CV+3+i must be strictly later than every word commit
for that pair. Same-edge same-address read/write is excluded.

`readiness_constraints.py` attaches these conditional bounds to the two existing
actual producer-ledger pairs. It emits alternatives for each possible n8 burst
position; it does not assign a production burst or manufacture source epochs.
Every source word keeps its phase-specific unknown epoch. This is the selected
functional native leaf timing profile; other native/physical profiles and global
source/destination leases still require their own qualification. No RTL cycles
or source defaults change.

Replaying the retained native pin logs, without rerunning Verilator, derives
minimum CV=180. Actual issue24/CV180 passes; issue23/CV179 fails exactly the two
bank reads of row119 word3 (read=write=189), and early issue0 fails62 word bounds.
This diagnoses the previous unsafe boundary and validates the strict inequality.
The three focused tests also refuse a missing bank and check that conditional
source epochs survive the join. Prior verdict files are unchanged.
