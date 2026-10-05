S82 dependent placement preview; model-only, no hardened abstract or timing transfer.

```sh
python3 -m pytest -q tests/test_dsrom_c_s82_placement.py tests/test_dsrom_c_w4_ledger.py
python3 tools/dsrom_c_s82_placement.py > /tmp/dsrom-S82-placement-replay.json
cmp /tmp/dsrom-S82-placement-replay.json results/uarch/dsrom_c_w4_20261003/s82_placement_r1.json
```

S82 exact W2 inventory at717a32dcf; full RD64 NP4096 return52.8975874mm2 retained, inactive-node area credit0. Source origins/hashes in s82_origins.json and model source_sha256. All2388 sites incl512BF,9552 weightmacros,16716 maximum cfgmacros charged. Two128-root-region groups per placement row; ordered site IDs unchanged. Retained selector/c9 obstacles are skipped deterministically, no parameter sweep. Capture320/256 templates co-located with4.32um gap, total576; common/control/read/clock timing NOT admitted. Source frames are mapped reservations, NOT hardened SSFF-qualified element abstracts. Known rectangle union/no-overlap is only a subset; no complement/native residual or return-control pruning. W3 PHY/controller/IO/halos, PG/clock/DFT/decap and full macro abstracts still required before contextual job. Added9stagehop4.338us is only inherited positive hop screen, not full MTP delta; Peirce must compose pipeline/drafter/verify/commit and movement. S69/S73FAIL unchanged.
