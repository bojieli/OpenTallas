Scenario C W4 attribution, model only.

Run from repository root:

```sh
python3 -m pytest -q tests/test_dsrom_c_w4_ledger.py
python3 tools/dsrom_c_w4_ledger.py > /tmp/dsrom-c-w4-replay.json
cmp /tmp/dsrom-c-w4-replay.json results/uarch/dsrom_c_w4_20261003/model.json
```

Exact source commits/paths/hashes are in origins.json; seven archived inputs are hashed in model.json. Historical PAR2 records are untouched. The 58.14742729288 mm² increment telescopes exactly; zero complement credit, no stage selection, route or rate admission. W2 must regenerate geometry/count-dependent terms; W3 must supply scan/non-scan HBM PHY/controller/shoreline rectangles. DFT, PG/clock/decap and unusable packing union remain explicit obligations before W7.
