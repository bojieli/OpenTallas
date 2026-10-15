Source-pinned PR ring quarter unit proof

Source: `3acb6219e55a6163f01eff8acf98035aedbd8750`.

Replay all 24 cases from the repository root:

```sh
python3 tools/qwen_coll_ring_quarter_bench.py --ref 3acb6219e --out /tmp/qcoll-ring-quarter-replay --jobs 3
```

The bench instantiates the original `ot_coll_static_ring` and its original registered bank-selection helper, extracted literally from the source reference, beside five actual `ot_coll_local_ring_quarter` helpers (128/128/128/128/34 bits). Both sides instantiate their actual SRAM Verilog models: original 32x546 and candidate 32x128. No behavioral SRAM stub or modeled golden payload drives the candidate.

Each offset 2, 20, 32, 33, 55, and 64 receives 6,144 full-rate cycles, mid-run reset, repeated address-counter wrap, and patterns covering both values of every logical bit. Full 546-bit comparisons include metadata and 6,006 strictly known read samples per case. The two-bank bank mutant reverses the registered one-hot selection; the offset mutant changes the actual read address; the metadata mutant flips the actual 34-bit-quarter payload. The bank mutant is deliberately insensitive for offsets at most 32, where no bank selector exists.

All clock ports use the same compiled edge. This proves zero added data edges at the component boundary under that clock profile; it does not qualify physical clock delivery, routed timing, or an eight-die/native full build. It does not inherit phase4 qualification. No core or generator source was edited for this proof.

The complete receipt combines the separately executed first positive_55 run with the subsequent 23-case run. Their six source pins must match exactly. Per-case receipts retain numerical outcomes, executable hashes, and hashes of the exact retained compiled helper source. Compile and run logs are retained. Executables themselves were temporary. The complete matrix is independently reproducible with the single command above.
