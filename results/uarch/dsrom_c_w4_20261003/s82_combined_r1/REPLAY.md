This is one S82/PAIR1 scan-die construction, based directly on canonical717. It does not select another stage count or adopt failed R_cap0 timing. The retained 52.89758742528 mm² RD64 charge is subdivided into 8,064 storage nodes and 128 storage roots; this does not add a second storage charge. Ragged field regions bind through the explicit canonical return-pair formula; all 1,708 unused pairs remain charged.

The four e8p5 PHY abstracts are existing assumed licensed-IP connection views, not qualified silicon. Their 40.0249506816 mm² body is shown spatially; containment within inherited fixed debits is unproved, so it is neither removed from those debits nor presented as a newly proved free replacement. The 900 ps PHY clock cannot inherit an 833 ps claim.

Replay from the prerequisite W4 tree plus this additive commit:

```
python3 -m pytest -q tests/test_dsrom_c_w4_ledger.py tests/test_dsrom_c_s82_placement.py tests/test_dsrom_c_s82_combined.py
python3 tools/dsrom_c_s82_combined.py --out /tmp/S82-COMBINED-COLD.json.gz
cmp /tmp/S82-COMBINED-COLD.json.gz results/uarch/dsrom_c_w4_20261003/s82_combined_r1/model.json.gz
```

The source graph retains all 66-bit binary edges, 69-bit no-ready root outputs and worst-stage 72-bit configuration reads. Its centre/cut census is static geometry, not accepted runtime demand, legal native tracks, bandwidth or calibrated latency. Local word muxes, finite clock/reset distribution and actual PHY/controller traffic are not fully placed in this graph. Consequently combined native route and hardware admission remain false.

The actual retained R_cap0 ODB was opened read-only by OpenROAD 26Q3-1510-g6cb3f2b704. `routed_q/` contains its actual instance census and extracted LEF, original terminal/receipt, extraction script/log and immutable identity record. Its DRC0 but setup/hold/slew/cap/fanout failures remain failures. Its QPIPE/QP_CAP source context is not the selected full S82 context. Neither its smaller frame nor its cell census earns an area or timing credit.
