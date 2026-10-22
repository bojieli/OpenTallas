# Static DMA LOAD compiler and actual source inputs

The current compiler's `hb_dbk` target104 is the VM-to-HBM BACK engine. LOAD uses the existing `vmks` HBM read windows, a new static conversion consumer, and an explicit scheduled destination route. These helpers encode the candidate consumer's load62 command and vmfc W159 payload. No existing default compiler path or release source is changed.

The selected ABI keeps payload88:0, appends valid lanes96:89 and load62 at158:97. Format6 is UE8M0; format3 is rejected. Count zero with release1 releases unused source lanes without reading SRAM or writing dummy VM data. Source PC hash and burst-slot inversion are checked against the actual `vmks` address equation.

`dma_fixture_hbm_1021.py` reads only true producer inputs. `capture` copies small tensors from the pinned released snapshot. `hash-engram` uses the native golden, real token history and released tokenizer. `capture-engram` reads the actual24 selected checkpoint rows and builds the native eight-home host table. `emit` reconstructs native RoPE, ONE and the Engram q*k weight product, then refuses every source whose bytes/hash differ from its native fixture HBM operand. Fixture O arrays never supply source values.

The complete positive packet is `source_bytes_all22/`: all22 LOAD input streams at L0/L2/L14 match their actual native fixture input hashes. The earlier18 and19 packets are retained separately. This closes source-byte availability; it does not qualify the preceding on-chip Engram gather or any LOAD datapath execution.

The compiler test ran on the fleet:4102 source-address inversions, six formats with strided rows and unaligned destination tails, malformed fields, and release-only encoding. The actual q_norm replay vectors use the existing r010 SU physical preload map, actual released BF16 source bytes, and independent fixture O checks. They cover384/1280 words in48 packets/two source windows. Invalid data lanes are masked in comparisons. The original consumer-map SHA and source SHA are retained in `qnorm384.json`.

Reproduce source inputs using the published tool, selected fixture directories, released snapshot and repository native config:

```text
# Checkpoint reads only; capture does no model simulation.
python3 tools/hbm_layer_vehicle/dma_fixture_hbm_1021.py capture --snapshot SNAPSHOT --fixtures L00/records.json L02/records.json L14/records.json --out TENSORS
# Run the numeric generation steps on the fleet.
python3 tools/hbm_layer_vehicle/dma_fixture_hbm_1021.py hash-engram --fixtures L14/records.json --config CONFIG --tokenizer SNAPSHOT/tokenizer.json --history results/rtl/w17_v41_1m_reference_token.json --out IDS.json
python3 tools/hbm_layer_vehicle/dma_fixture_hbm_1021.py capture-engram --snapshot SNAPSHOT --fixtures L14/records.json --hashes IDS.json --out ENGRAM
python3 tools/hbm_layer_vehicle/dma_fixture_hbm_1021.py emit --tensors TENSORS --fixtures L00/records.json L02/records.json L14/records.json --config CONFIG --engram ENGRAM --out SOURCE_BYTES
```

Execution remains open until source bank/epoch ownership, actual window-ready edges, final releases, physical consumer placement, source-to-destination route ages/contention and VM write slots are composed. The independent backend owner reported a real SRAM/converter384-word PASS on source51f0c8d67, while a newer physical successor changes its pipeline; that successor requires its own replay. No layer, token, physical closure or throughput claim follows from this packet.
