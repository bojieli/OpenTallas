# HA9 actual service composition

Source base e3258c0c6f2afaacaac3510483800f66703b7503. Input snapshots and SHA256 origins are in inputs/origins.json; RF_service_home.json is the retained Goodall owner mapping report. Each input is hashed again in model.json. No P&R, RTL edits, stage-count study, adoption or rate credit.

```sh
python3 -m pytest -q tests/test_hbm_ha9_service_composition.py
python3 tools/hbm_ha9_service_composition.py --out /tmp/fresh-service-composition.json
```

The RF128/W4/W6/FMAX/FMIN mapped body is one component. Its macro plus standard-cell area is not a placed footprint. Do not debit W4/W6 again, or add this whole body to a die budget without replacing its original matched debit. HA1 storage is only a new storage proxy; codec, mux, clock and routing remain additional unresolved costs. Bus sums are local unshielded track floors, not global links or proven corridor capacity.

HA6 retains a source-bound ratio-FIFO inventory as a reference only; HBM caller, replication and crossing contracts remain missing. No 1.091GHz adoption or free CDC claim. HA8 forwarded sources are pinned; native-engine-installed=false is preserved. SRAM bank/port and actual caller boundary/clock inventory must be joined before physical admission.

DS KV binds the current W2 S82 map with RD64. Allocation 456 remains provisional because scan-service homes are expressly unbound in W2. No transfer of S73 capacity assumptions, 420-stack claim or inherited token rates. Claude owns refit; W3 needs actual state/reserve, provider ownership and per-stage demand against head bounds, not a new stage sweep.
