Literal TP96 collective schedule reconciliation

This substantive endpoint-only calendar successor consumes the immutable snapshot of the actual96-endpoint normal receipt from source250dfa5a92575f77f5bdb98d60b65c27d3932a7f. It independently extracts all288 op/endpoint rows, verifies all96 landing/consumer counts, normal log hash, binary receipt identity, preflight bytes and producer git-source hashes. The live stalled campaign was not read for a verdict, duplicated, restarted or modified.

Normal receipt reconciliation:

|Case|Normal cycles|Retained preflight cycles|Verdict|
|---|---:|---:|---|
|w19_oreduce|12790|463462|Within normal scope only|
|expert_intermediate|8235|5001|FAIL: bound exceeded by3234|
|index_candidates|42861|64013|Within normal scope only|

The exact observed normal figures remain separate from the endpoint reservation inputs. No passing normal case proves the still-pending stalled bound.

All2213PC identities, reads/writes and families are checked against the canonical final native archive. All270 collective PCs have source-dependent literal64B word reservations:40 all-reduce,212 all-gather,10 topk merge transport and8 selected KV transport. Each run-length reservation repeats atomic allendpoint admission, route, everyconsumer acceptance, visibleACK and reverse release for each word. It holds one global collective credit, one service credit/rank and at most96 landing records/endpoint against128 capacity. Repeats do not overlap or reuse a word credit early. This constructive software component serializes endpoint work; unrelated native/provider phases retain their existing calendar owner, not zero cost.

The explicit positive endpoint cycle table is in endpoint_cycles.json. Gather1647route cycles/word comes from ceil(normalexpert8235/5); it is a provisional envelope, NOT a proven per-word or worst-case latency. Reduce906 derives from the retained preflight; admit/ACK/reverse are explicit provisional inputs. Consumer is one literal64B record/cycle. The sum21290258 endpoint-only provisional cycles is not a full-program latency and is not added to native software ticks or converted to ns.

All40 actual expert gathers include seven slots:32256B global =336B/rank =six64B words. The normal fixture includes six slots:288B/rank =five words with32B padding. Therefore8235 cannot replace actual expert-PC timing; source pack/view/refill/ACK and six-word execution remain unmeasured. For index512 raw gather,96*64 =6144 consumer cycles is an unavoidable floor at the declared64B endpoint width. Topk arithmetic, I64/value wire codec and selected-KV heads-only mapping remain separately unqualified.

The old w15_hbm_nvls.json is snapshotted and hashed, never overwritten. Its reading guide assumes approximately750.4B product slots, while exact hbm_p48_ss_prod field is749.7B at1200480192.0768306Hz. Its fitted index4096B/rank takes six assumed slots and1471cycles. This is a different geometry from64B words,0.9GHz serial bench and its allendpoint credit handshake. An implementable wideport, schedule and finite credit design is UNKNOWN. There is no42861-vs1471 direct headline delta, no bandwidth-slot compression as proof, and no physical-timing replacement.

The native/V1/provider summary from a67150839 is retained by sourcehash: V1 is not replaced again; I64/RMW,r22,64Bshared and bothRFmirror costs remain unchanged.189476DS shared-template calls and the full provider/RF calendar remain UNKNOWN. Actual HBM physical landing/VM/RF visibility is not qualified by the harness.

Reproduce in the source checkout with retained producer git objects:

```sh
python3 -m unittest discover -s tests -p test_h3_complete_native_calendar.py
python3 tools/h3_complete_native_calendar.py \
  --tp96-collective-inputs results/uarch/h3_complete_native_calendar_20261002/tp96_literal_collective_join_r1/inputs \
  --tp96-endpoint-cycles results/uarch/h3_complete_native_calendar_20261002/tp96_literal_collective_join_r1/endpoint_cycles.json \
  --out results/uarch/h3_complete_native_calendar_20261002/tp96_literal_collective_join_r1/final --verify
```

Fresh generation uses a new output path without --verify.50testsPASS; final three artifacts replay byte-identically. Metadata generation takes2.71s /1.39GiB peakRSS here; reserve2GiB and30seconds. No numerical oracle,payload regeneration,acceptance rerun orRTL build is called. Outputs and hashes are in inspection.json; inputs/source/tool pins are in final/manifest.json. A first source check rejected the newer local uarch_model against the old immutable producer; generation.log preserves that failure. Final verification reads historical git blobs explicitly without mutating newer sources.

Latest TASKS and parent DS complete-element/r33 reviews were read; hashes and scope are in latest_parent_checkpoint_read.json. r32 is historical failure/codec dependency only, not adopted. r33 reviewed127old+current window views and264RoPE bindings do not provide actual oldrow payloads or close407 auxiliary refs. Those remain the provider continuation. ROM mapping/WAKE failures provide no HBM endpoint credit. Main/publisher/frozenD1 remain untouched.
