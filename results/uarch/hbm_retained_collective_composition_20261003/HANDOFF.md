# Retained collective service and measured head debit

HA2 source045cc7411 is MEASURED REJECT: exact27648 snapshot packets, but last delivery2158.392/2278.488/2251.800ns. Whole reducer elaboration is incomplete; CDC, refresh, whole-system serial path and contextual route/timing remain unqualified. Snapshot timings are never applied as a universal all-reduce service. Neither459.166nsestimate nor550ns candidate benefit is eligible. No rescue/retuning/build is performed.

The active composition retains the entire original W19 collective subtotals, including fixed latency and payload serialization: AR240.46us, verify6 326.81us, draft23.89us. Fixed fits777.0224ns gather and823.620420ns all-reduce are already inside those subtotals and are never added twice. All R2/HA2 and dependent R3a savings are zero. Other unqualified ladder savings are not applied.

The existing R0c correction adds13.712us routed first-access plus1.143076923us ACK/fence/owner service to AR and each verify pass. The resulting1M conditional AR is456.995076923us; verify6 is715.695076923us; draft remains51.87us. These are inherited measured-fit/source-model prices, not a newly measured whole native token. Acceptance,200K scaling, refresh-first-access and service corrections remain the explicitly stated source assumptions. Accelerator adopted gain and published rate remain absent.

Laplace's independent registered-head resultd9b809411 is joined as a separate Qwen ROM clock-fix debit. Both actual single-user split cases cost126 counts of the slow-domain counter: sclk0.9GHz means140ns, not105ns. Source relocation is explicitly validated against raw record pins. The same reduced18-step context rate decreases0.0561708percent; no per-token division/fullshape extrapolation or async/clock gain is granted. Original prospective72-cycle sizing record and asyncsub1 rejection stay unchanged. Physical SS60/FF25 context is still required.

Replay:

```
python3 tools/hbm_retained_collective_composition.py --verify
python3 tools/qwen_headreg_measured_cost.py --verify
python3 tools/uarch_model.py --hbm-retained-collectives --out /tmp/retained.json
python3 tools/uarch_model.py --qwen-headreg-cost --out /tmp/head.json
python3 -m pytest -q tests/test_hbm_retained_collective_composition.py tests/test_qwen_headreg_measured_cost.py
```

16testsPASS. Both unified CLI outputs match their generated records byte-for-byte. Default calculation bodies are unchanged. Dependencies: mainb3537e174 terminal rejection plusd9b809411 measured registered-head records/source relocation. No rejected measured record, prior study, RTL or live job is edited.

S82 ROM serial-path composition is separately ready at254ab8d012c3fcc5b237aa103085c9675adf77e5, dependency717a32dcf. It includes retainedRD64, all stage endpoint wires, positive multicast/CDC/draft costs; physical fit and missing gather/provider/ready/arbitration costs remain pending. Its rates do not transfer the oldS73 headline. Parent owns coherent integration of these opt-in unified entrypoints and regeneration of merged-source hashes.
