# S82 retained-RD64 serial-path pricing

This is conditional analytical composition, not a measured full-token result or an adopted headline. S82 uses 328 rank dies plus 44 dedicated dies, 2388 pairs/rank (512 BF + 1876 q), and the retained NP4096/R128/RD64 return reservation 52.89758742528 mm2. The area screen is 856.5356341582075 mm2 against 858; physical containment and contextual timing remain pending. S69/S73 failures and the RD4 rejection stay unchanged.

The existing S58 PAIR1 graph baseline includes 57 board stage hops. Only 24 new stage hops are added: 11.56842105263158 us. Each hop retains 0.4070175438596491 us transport/control plus both 45-stage SerDes endpoint paths at 1.2 GHz (0.075 us); the 81-stage-boundary endpoint subtotal is 6.075 us. These are inherited source-model geometry constraints, not new routed S82 evidence. There are no PAR2 owner UCIe crossings; TP4 canonical-result multicast remains a separate priced boundary.

All 24 actual indexer projection multicast calls are serially charged from Arendt's S82 directory, with two CDC cycles and both wire endpoints included per call. Their cost is 29.480 us with independent destination ports or 85.37333333333332 us on one shared destination link. These port assumptions are unqualified. MTP exposes one- versus six-position repetition rather than pretending position-specific data can be shared. Draft time is 0.1173 times the newly composed AR path; tau=3.649 is an inherited acceptance assumption, not a measured quality result.

At 1M context the priced AR components total 435.448421–491.341754 us (2296.5–2035.2 tok/s). MTP step components span 1008.406–1497.723 us (3618.6–2436.4 tok/s). At 200K the corresponding AR components are 418.450–474.343 us (2389.8–2108.2 tok/s), and MTP components 924.188–1413.504 us (3948.3–2581.5 tok/s). These are conditional component estimates, not an uncertainty interval for a qualified design. Missing gather/auxiliary/access/arbitration/refresh costs are null, not zero; the actual S82 consumer calendar and physical endpoint geometry must be joined before a complete token rate exists. Old S73 7147 is not transferred. No power/saturation/stack adoption is inferred.

Replay:

```
python3 tools/dsrom_s82_token_pricing.py --verify
python3 tools/uarch_model.py --dsrom-s82 --out /tmp/s82.json
cmp /tmp/s82.json results/uarch/dsrom_s82_token_pricing_20261003/model.json
python3 -m pytest -q tests/test_dsrom_s82_token_pricing.py
```

Dependency: 717a32dcf35c09ccff432068691a3da40b610863 supplies the complete S82 source ownership directory. No RTL, simulator, physical flow or model inference is run here. Default unified model paths are unchanged; the new CLI is opt-in. The artifact pins every input, helper, and unified-model source.
