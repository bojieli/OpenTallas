PHY/STREET STRUCTURAL DIAGNOSIS

Baseline4 overreach cores are all SM last-column halves beside SPB PHY. Every103.68um internal SM gap needs100.04um of signal/clock/hold demand at every row; no compression slack. Rejectedtrials1(lastcol34.56shift):10bad;2(distributedgaps86.4):16bad;3(linkdigitalabstractonly34.56):4bad. Rootcause includes full SerDes PHY and63.64um PG margin/clock halo, clipped into SM type.

Trial4 c25c_phy_street.py moves completeSPB PHY tuple103.68um in its existing1745.28um slot, updates die.io, clock keepouts and PGdomain/dedicatedbump windows, removes old SM halo clip, leaves40.04um minimum boundary clearance. Actual demand-mode street check PASS0/1192cores; worst397.44um,296flows354076bits. No SM/core outline/interface/RTL/cycle change.

NOT ROUTE APPROVAL: visual review locates2 internal signal relay centres inside the full1050um PHY envelope (digitalhardcoreheight600.48). Exactsites in phy_relay_overlap.json. Resolve actual EP/LK port matching and place relay bays outside full physicalPHY before routing. Some legacy generic bidirectional conn names hide actual EP sd_rx E /sd_tx W faces; bind actualsource first, then structural re-pin/re-place or price added stages. PGmust re-solve after moving its domain/bump window; completeG0/G1 still owed on composedC25c.
