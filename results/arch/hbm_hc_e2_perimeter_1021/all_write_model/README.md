# E2 remaining write-root topology model

Actual rw11is full gate reproduced w0 37.4 and w1 17.7 ps TT, then failed w2 142.2; w3 and FF remained NOTRUN. The source-bound baseline prefix reproduces these three TT values (37.400635/17.685913/142.186036), and predicts w3 98.377930. Baseline FF w2/w3 are156.145691/111.054993.

The structural candidate preserves qualified w1 exactly and replaces both remaining w2/w3 paths with same-root equal-depth peripheral distributions. It retains all1035 w2 pins and all1052 w3 pins including17 actual flag landing cells,20 independent hard-child clock entries, ports/phases/data edges and the normal RC restoration. Platform after-repair candidate TT w0/w1/w2/w3 spreads are37.400635/17.685913/30.087586/32.551574; FF29.567047/15.466125/26.951721/29.447449. Full before/after platform/calibrated48-row data and per-pin arrivals are retained.

This is a source-bound prefix model, not physical closure or an all-roots full gate. The unchanged remaining production roots and child-boundary qualifications still require the normal full gate, actual clocks/native/PNG/SAFE review. No successor gate or submission has been launched.
