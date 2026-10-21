# L20 split tree bench, TX arrays random-initialised (stale-memory proof) -- receipt copied by S81-L20TOK 10-20
Source: Codex T3 S81-MU-LINKS (codex/s81-mu-links-takeover3-1019 b5a62c6dc; DUT 2a74f347f unchanged), ep5 unit
oth-ubuntu-671838-1792456747, XINIT on the TX arrays only (random before the first clock). Log tree_array_random.log:
k3 TREE_RD PASS (0 mismatches), k6 TREE_RD PASS (0 mismatches), k6 corruption mutant TREE_RD FAIL (16 mismatches) = expected
(write-before-use holds; a stale/corrupt TX word is caught). The unit's exit 1 is the mutant leg. Files copied unchanged.
