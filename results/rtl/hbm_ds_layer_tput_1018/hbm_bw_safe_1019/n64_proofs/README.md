# SAFE n64 (source bc42f77a8 = cc723735d + 27x 128x64 macros) component proofs, LH-BW 10-19, ep8/ep5, Verilator 5.050
- aq64 (WQ64, ROW_REGIONS8, BANK_REGIONS8): positive AQ_EQ_PASS 23968 checks/2385 push/1873 col/1258 row; HEAD/ACT/REFRESH/WRROW and the new BANKREG (wrong region-0 bank copy) mutants all AQ_EQ_MISMATCH (fail witnesses *.log).
- aq32 (default): positive 23968/2238/1982/1677 PASS; HEAD/ACT/REFRESH mutants caught. This is the first proof of cc723735d (BANK_REGIONS wired in the bench).
- txn: 6000 req BW_SAFE_TXN_DATA_PASS 12944 beats/759 writes, cycles 166919 identical to pre-n64 (strict-rate FAIL vs h9b 88783 retained, the json FAIL verdict); identity mutant FAIL as required.
- controller_rate.log: DS seeds 91.62/92.74/92.94, packed 103.89 B/edge: identical to the 877c9e27d final controller (n64 is cycle-neutral).
