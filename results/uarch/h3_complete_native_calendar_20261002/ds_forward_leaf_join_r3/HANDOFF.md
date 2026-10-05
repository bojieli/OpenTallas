This milestone consumes reviewed C0 static lowering and Sagan's ten source-order
movement templates, plus the actual retained DS forward builders and bounded
Qwen export. It compiles source instruction demand and provisional finite
service costs. It does not execute a released checkpoint token or qualify RTL.
The result remains PARTIAL_KNOWN_SERVICE_COST_WITH_EXPLICIT_SHARED_UNKNOWNS.

Run in an isolated checkout of this consumer commit, with all immutable source
commits available in the shared repository. The canonical DS artifact and C0 /
movement producer blobs are read from git; no duplicate 14 MiB native artifact
is introduced. Parent owns integration.

```sh
python3 -m unittest discover -s tests -p test_h3_complete_native_calendar.py
python3 tools/h3_complete_native_calendar.py \
  --ds-full-program-cost results/uarch/h3_complete_native_calendar_20261002/bounded_provider_milestone/ds/forward_dispatch_milestone.json.gz \
  --ds-full-native-source results/uarch/h3_deepseek_complete_native_20261002/program_final.json.gz \
  --ds-native-source-commit 91e3b8cc2791fa3fe1322df3d72b3f76dbd184f6 \
  --ds-forward-leaves \
  --c0-source-commit 54a0a36642332eb76fc114e606d59a0c8cbee719 \
  --ds-shared-bridge results/uarch/h4_c0_ordered_movement_20261002/source_order_bridge.json.gz \
  --ds-shared-bridge-source tools/h4_c0_ordered_movement.py \
  --ds-shared-bridge-commit a100243c45f7f4b5254e253d5ad776bb3a982046 \
  --out results/uarch/h3_complete_native_calendar_20261002/ds_forward_leaf_join_r3/review \
  --verify
```

For regeneration, remove `--verify` and choose a new, absent output directory.
Generation of the reviewed movement composition took about 88 seconds and
5.7 GiB peak RSS; allow 2 minutes / 7 GiB RSS and about 20 MiB output. This is
compiler metadata work, with no arithmetic/provider rerun or hardware build.
The replay compares every artifact byte, including deterministic gzip bytes.

The C0 source join validates all 1737 Qwen PCs / 21 families and 2213 DS PCs /
30 families: PC/dependencies/version references, actual ordered Qwen kernel
instructions/counts, DS rank/template calls and retained template code hashes.
DS forward catalog has 1127 templates and 958 distinct source leaves; source
loop counts match every retained scalar projection. C0 uses 26060358782 source
128-lane batch obligations rather than charging a scalar as a C0 command.
Original native scalar service upper is retained separately and charged once.
The source catalog is instruction demand, not an ordered full-program dynamic
transport trace or an RTL decoder qualification.

Sagan's ten whole-value templates are validated by the existing strict importer.
Known software movement subtotals are 307953600 read64 and 148443072 write64-ACK
transactions. The mandatory shared beat is 64 B. Source-resolved C0 cost and
this movement subtotal compose with existing provider costs once. Shared UNKNOWN
calls are 189476 (previously 211428); complete shared totals and complete latency
remain null. Known partial subtotal is 589388306802 software ticks. No token
rate, hardware frequency, parallel-SM speedup or measured endpoint claim follows.

`forward_parent_provider_interface.json.gz` covers 1323 forward PCs, resolves
native parent provider declarations and retains 136784 canonical source-home
references for 2002 versions. `resolve_ds_forward_parent_home` checks actual
PC/version/rank/SM and source lifetime. Four requested versions have no home
record in this archive: DeepSeek.121.index_keys.L2.226,
DeepSeek.449.index_keys.L8.690, DeepSeek.782.index_keys.L14.1160 and
DeepSeek.1110.index_keys.L20.1624. These are missing residence-archive bindings;
a separate persistent-provider binding cannot be inferred. Their consumers
still need concrete typed provider/home/lease proof.

`resolve_ds_forward_leaf_reference` accepts structured parent-template,
call/iteration, exact source opcode/attrs/shape/operand/span references. Dynamic
index rows additionally bind `first=invocation_index` and the actual rank,
regenerating the original source builder constants. Stage instructions retain
the canonical original resolver. Sagan can use this hook without a duplicate
shared movement importer. The existing eleven-leaf observer is CPU fixture
scope only: it supplies no full-parent invocation order or parent refill,
writeback, visibility ACK and reverse-grant receipt. It is not multiplied into
a whole-program movement proof.

`G0_both_program_interface.json.gz` pins capability classification and C0 source
ABI, exports every PC's integer/bit/convert/predicate demand, forward source
operand widths and instruction references, and actual RF 2R/1W 4096-bit ports,
I64 paired words, 32 workspace vectors, 512 logical vectors, two physical write
mirrors and 32 SMs/rank. Qwen demand is 77701000 G0 commands; DS is 11654090224
source G0 128-lane obligations. Provisional native service is explicit; measured
opcode cycles, mux/fanout/routing fit and area remain unknown. Popper's source
semantics/model gate must replace the existing native term once, not add another
I64/r22 charge. Hardware binding is not inferred from CPU fixture results.

Remaining software composition gates are the 1117 other template movement
bindings (including 228 forward template continuations), actual ordered parent
refill/writeback/ACK/reverse events, released-checkpoint traffic/collective route
costs, and the 96 DS rank workspace physical bases/provider leases. The precise
extent successor demand is 32 MiB per rank, 512 B aligned, address width 27,
base <=100663296, disjoint from all retained homes/checkpoint/persistent leases.
The bounded source allocation remains valid as software shape evidence; an
unbound physical lease does not become an admitted scratch or HBM address.

Validation includes source count/format/rounding/rank mutation controls;
dynamic index-constant and opcode/operand/span resolution; C0 instruction,
version, dependency and source-hash controls; concrete home lifetime/missing-home
controls; finite scratch/RF alias, visibility, credit, and retirement controls.
This milestone adds no numerical test of a full released checkpoint. Earlier
Qwen evidence is two reduced 36-layer bit-exact fixtures; DS family fixtures and
the new eleven-leaf observer do not establish full-token quality. Prior logs
and failures are preserved; `tests.log` is the early fixture-metadata failure.
Authoritative artifacts are under `review/`; earlier untracked metadata runs
are intermediate and are not offered for intake.
