Native-pin placement diagnostic

qc_cp_place.py --native-pins accepts the immutable native endpoint plan. For each physical child pair, it enumerates every paired data/flag bit and computes the maximum local-pin offset for each of four Manhattan sign combinations. Four linear inequalities then require every bit to fit405um at selected macro origins. This replaces the center surrogate for known child pairs, including ordinary written flags. Native asset hashes and one-coordinate-per-pin are checked before constructing the model.

A0/boundary endpoints still lack measured pin snapshots and retain the historical center diagnostic; thus this remains a partially bound model. Obstacle-avoiding routes, actual clock references, legal reset composition, and timing windows remain separate requirements. No new hardware stage or exception is implied. Positions use1nm integer precision.

The separate paired-sibling narrow search at3153.6x5227.2 completed INFEASIBLE after1471.7s. It fixes sibling adjacency, so it is not an impossibility proof for unrestricted packing. Exact solver receipt is cp_place_pair_777.json.
