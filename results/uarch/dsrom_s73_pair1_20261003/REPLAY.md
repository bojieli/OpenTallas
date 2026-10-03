W2 successor partition and ownership records. All new figures are MODEL_UNVALIDATED.
No RTL, synthesis, P&R, or inference is launched by these commands. Original source
records are unchanged. The baseline is main `4a18e3cc0`; W4 is `d1b6dd52a`, W3 is
`7c5b6a79b`, and the rejected W1 RD4 measurement is `046bf5026`.

The current candidate is `baseline_s82_successor_r1/model.json`. It keeps the full
existing NP4096/R128/RD64/ROOTD128 return reservation, 52.89758742528 mm² at the
historical FF50 accounting scope. It does not claim RD4 area <=7 mm² or a credit
gain. The measured 9-cycle reuse and 582/267-cycle fixture are preserved; they are
not an actual program-loss measurement. Unused return inputs create no padding
weight macros or element frames, and receive no return-area credit.

S73/2682 and S69/2837 screen at 897.5583 and 919.1787 mm² with this return baseline.
The first source-classified baseline-return area screen is S82/2388/BF512/q1876,
856.5356 mm². This is an area proxy, not an adopted partition or physical fit.
The 287.02185 mm² complement and 47.20801 mm² residual remain charged. Only the
4.31826736128 mm² PAR2 corridor is removed. W4's 58.14742729288 mm² attribution
and the complete 64.55495794136 mm² screen increment telescope in area_ledger.json.

Generate a fresh map and compose new records (never reuse an existing attempt):

```sh
python3 tools/dsrom_s73_pair1.py --stages 82 --pairs 2388 --bf 512 --out /tmp/W2-s82-replay/map
python3 tools/dsrom_s73_pair1_records.py --map-dir /tmp/W2-s82-replay/map --out /tmp/W2-s82-replay/records
python3 -m unittest discover -s tests -p test_dsrom_s73_pair1.py -v
```

The compiler uses the pinned full 96,085-tensor header directory, original ordered
K segments, source row-tree packing, and provider-first allocation. Output rows
split only at complete 128-superrow boundaries. Matrix source-code coordinate
coverage is independently checked across rank slices and row fragments. Twenty
replicated indexer matrices receive canonical source owners, with positive,
unqualified result-multicast costs instead of duplicated source payloads; all
reserved frames remain charged. This multicast needs actual schedule/port and
exact RTL gates before adoption. Source scales, conversion boundaries and native
provider/rank delivery still need the full payload-address gate.

Every shipped source key, including scales, constants, MTP, vision and aligner,
has a directory entry. Auxiliary raw payloads map byte-for-byte into empty q-only
sites, with disjoint bounded physical macro-word spans. Their execution ABI and
latency are unqualified; zero added dies does not mean zero delivery cost.
`physically_placed_exactonce_PASS` stays false: no payload execution or physical
placement has been performed. Header/source coverage must not be promoted to it.

Historical successor attempts are retained:

- `attempt_r1`: unsplit allocation FAIL at layer-1 Engram. Reproduce with
  `--reference-unsplit`, default S73/2682/BF576, to a fresh output directory.
- `attempt_r2`: S73 decoder packing with balanced raw reservations and row splits.
- Root composition: source-coordinate audit FAIL on 20 replicated indexer matrices.
- `successor_r3`: canonical source-owner correction, rejected RD4 still historical.
- `successor_r4_baseline_return`: S73 binding to the retained return; area FAIL.
- `composition_failure_r1.json`: new-ledger missing capture-proxy assertion FAIL,
  fixed by retaining the 0.0761399676 mm² proxy before its enclosure replacement.

Pinned peer/input commits and hashes are in each model's source_pins. The final
validation manifest pins the new tools, original local inputs and every new
artifact. W3 gets actual matrix stages, immutable homes and auxiliary locations;
its historical 420-stack allocation is not transferred to S82. W4 gets counts,
BF masks and PHW requirements; no complement, PHY, halo or return savings are
credited without the composed gates. No documents under docs/ were edited.
