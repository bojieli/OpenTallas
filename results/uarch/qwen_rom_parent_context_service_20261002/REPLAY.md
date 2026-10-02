This submission is based on main `28d01b35ac5c82595e5c8a96200cd1f6ecb4269f`.
The final authority is `model-r7.json` and `admission-r2.json`. Earlier draft
prices and the initial arithmetic test failure are retained as history, not
the current candidate. No RTL, physical build, numerical position or live-job
change was made. Parent owns integration and push.

The single candidate is a finite tagged owner pipeline against the existing
32 actual 1R1W context RAM banks per stack. It retains 12-edge bank read
ownership and immutable context capture, with 32 leased final-output credits,
32 flight records, 32 output storage entries, in-flight beat masks, joint
allocation/retirement accounting and consumed-grant/read-drain quarantine.
Software fixtures construct II1 only on an interleaved eligible-PC stream;
they also test same-bank stalls and finite backpressure. These fixtures do not
qualify actual source readiness or a sustainable production service rate.

The unchanged source has one global owner lookup (II14) and a seven-edge
shared return scan. The modeled successor separately prices the finite owner
pipeline, eligible read/write arbiter, native held-route replacement, producer
CDC, window ownership, complete extra operand stage and per-domain collectors.
The 14-owner screen is a historical comparison, with no selected owner/RAM
replication. Current command339 fits the abstract344 port without a widened
tag; validate native16 upper4zero and preserve full192 identity.

At context8192, the conditional tail/V-forward candidate replaces the existing
KV read charge once: 150690816 offchip read bytes and 156672 closing write bytes
per rank/token. Four one-command stack ports, four shared data/grant buses and
one global64B/stream-edge fill remain distinct from 1536 physical tile sinks.
Even with perfect compute overlap and new II1 arbitration, the shared response
slots require at least2.356992ms; the fill requires1.96224ms. The transport
bound exceeds the333.333us 3k budget by7.070976x. This is an explicit candidate
deficit, not a final target prediction or selected production bandwidth.
The pre-existing 50owner/6fill/4command requirement is referenced, not duplicated.

The complete sequential36-layer production calendar is still gated by actual
producer/state and demand receipts, PHY row/bank/refresh/turnaround service,
current-source arithmetic timing and legal slots. Two54row windows fit the
current128 rows only as proposed leases; no persistent state is erased on a
layer hop, no full-layer refill independent of demand is invented, and no full
36-layer residency is assumed. The original capture contains no KV state or
program images. Do not turn the full cold correctness calendar into production
latency evidence.

The known service delta includes existing context banks once, the additional
finite pipeline/arbiter/CDC/operand/window cells and replicated collectors.
The baseline ledger conditionally debits four PHY footprints only if absent
from the named747.652mm2 allocation. It is not complete slot admission: actual
controller/protection/PG/OBS/routes and named baseline credits remain open.
The shared tile cut needs1685 tracks versus1360 nominal capacity, deficit325.
Existing physical reset/collector failures and original numerical evidence
remain unchanged.

Exact independent replay from a clean worktree containing this commit:

```bash
python3 -m unittest discover -s tests -p 'test_qwen_rom_kv*.py' -v
python3 -m unittest discover -s tests -p 'test_qwen_rom_persistent_kv*.py' -v
python3 -m pytest tests/test_qwen_rom_local_parent_composition.py tests/test_qwen_rom_owned_ready_context.py tests/test_qwen_rom_parallel_owner_screen.py -q
python3 tools/verify_qwen_parent_context_evidence.py
replay_dir=$(mktemp -d /tmp/qrom-parent-replay.XXXXXX)
python3 tools/uarch_model_qwen_parent_context.py --parent-ref 28d01b35ac5c82595e5c8a96200cd1f6ecb4269f --result "$replay_dir/model.json"
cmp "$replay_dir/model.json" results/uarch/qwen_rom_parent_context_service_20261002/model-r7.json
```

Expected: 58 KV tests (16 new), 15 persistent-source tests, 14 peer pytest
tests; pin preservation PASS for48 source pins and28 immutable originals;
byte-identical model replay. The earlier zero-test unittest discovery for
pytest files is retained and excluded from validation. The capture hash is
`d71d6d8a6d724b8f48c77ec90dd9027935d5d8f90d50b54be3a941b680f9beab`.

Next necessary receipts are addressed in Popper dependencyr1 and
Kepler/Euclid/Ampere/Maxwell dependencyr2. No callable peer messaging transport
is exposed; these contracts are ready for parent relay, not claimed delivered.
Build admission remains FAIL until command, owner, fill, PHY, producer/state,
current36-layer calendar and baseline-slot contracts compose.
