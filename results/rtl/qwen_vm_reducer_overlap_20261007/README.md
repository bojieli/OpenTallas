# Captured delayed reducer / ME overlap through actual protected service

**Four-state full-aperture component PASS.** This gate uses the immutable composed PC19/20 calendar's parent edge160, not an invented overlap. The frame contains2048 ME VX reads and one delayed reducer write to scalar16160. All source seats are retained: NR2256, NW865, VX0=208, NVX2048, reducer writer seat848. It contains no SU/ME arithmetic engine or whole-array/die simulation.

Prerequisites are the composed-calendar patch and canonical default-off direct-readback successor. This bench explicitly selects DIRECT_READBACK=1 and uses the exact pinned canonical three-module sources. Original predecessor files/defaults remain untouched. Full16 backing geometry remains256 data SRAM macros plus32 check macros. The candidate repairs the earlier four-state output-expression propagation failure; old failed evidence remains separate.

The actual frame has128 distinct scalar reads in64 aligned four-word windows, each reused across the2048 source seats. The existing adapter caches only its last window, so source-order walking issues1024 real checked reads. It does not implement global64-window broadcast deduplication.

Actual measured parent160 cost is **14419 physical service edges**: `4 + 2256 + 865 + 11*1024 + 30*1`. The underlying checked provider returns reads9 edges after acceptance and writes28 edges after acceptance. All reads complete before the reducer store; its actual raw commit, readback, decode, verify and checkedACK complete before exactly one native clock edge is admitted. Every checked read and postverify data payload is explicitly checked for unknown bits.

The original desired ME participation is an independent input, held enabled for the captured frame. Real XVM1 semantics are retained: its2048 responses become observable only at the following admitted ME-enabled native event. Every returned VX seat is checked against the physically installed source fixture. Reducer scalar16160 reads back its new payload; scalar16161 retains its old value. The actual frame has different-word reads and reducer write, so it demonstrates simultaneous service obligations, not a same-address old/new collision or competing writer priority. Those are separate earlier component obligations.

Initialization physically writes4096 authorized HEAD initial fixture scalars through the adapter and establishes the reducer word through the same checked service. These values are opaque protocol payloads, not claimed actual L20 arithmetic outputs. There is no host memory oracle, forced ACK, raw-array preload or arithmetic shortcut on the positive path. Five bulk initialization frames require260 checked writes because four chunk boundaries split words; reducer-word initialization and the captured reducer write bring the total to262. Including readback and initialization, the run has1025 checked reads,262 raw/checked write ACKs,44127 held edges and9 native edges.

Three negatives replay the same full-aperture frame and fail with their expected assertions: foreign reducer ACK ownership; native admission driven by rawACK before postverify; and native admission driven by write acceptance. The first faults with the source held; the latter two are detected as unpaid native advancement. Native advancement is observed through the actual ICG, not a modeled latency counter.

Prebuild sizing and source inventory precede compilation. Local headroom was72GiB available RAM/175GiB disk. Icarus compile took0.72s and126720KiB peak; positive simulation took94.44s and55296KiB peak. Three independent negatives each used55296KiB and about92s. The source-derived deadlock bound is a protocol assertion; no wall-time, CPU-time or guessed process-memory cap was applied.

Reproduce after prerequisite integration:

```sh
python3 tools/qwen_vm_reducer_overlap_gate.py --root . --out /tmp/qwen-reducer-overlap-new
```

An explicit `--calendar` can select the same SHA-pinned calendar at another location. The runner checks all source hashes, snapshots sources and fixtures, records current resource headroom, and verifies all four outcomes. Gate cost is measured in this component's physical clock edges, not converted into a token-rate claim or assumed cross-domain clock period.

Full parent core/sequencer binding, remaining writer families, source-issue calendar coverage, actual numerical reducer values, mutable-state fault campaigns, ingress/epoch ownership, physical closure and composed token latency remain open. This result closes the requested actual delayed-reducer overlap mechanism, not those broader gates.
