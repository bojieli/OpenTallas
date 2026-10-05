# DeepSeek attention numeric compilation boundary

## Objective and unchanged implementation

Compile the existing full geometry (H16, D512, TD32, NL4, TROWS640), not a
smaller substitute. Use Verilator reusable hierarchy as a simulation compilation
boundary. No additional architectural pipelines, no numerical substitution,
no scheduling model substitution.

This is 64 copies of the same H16/TD32 arithmetic tile and 64 copies of the
same PV merge. A hierarchy control file allows each parameter specialization
to compile once without flattening all copies through the optimizer.

## First bounded measurement

Source candidate: `/tmp/opentallas-publish-e2e-now` (dirty source hashes are
recorded explicitly; no claim this equals committed main).

`probe-full-hier/result.json` records all six input source hashes, control file
hash, command and failure. 8 GiB per-process address-space limit; serial compiler
jobs; 180-second process-group wall timeout. No C++ compiler launched.

* tile conversion: 1.926 seconds, 261.152 MB allocated, 28 C++ files generated;
* merge conversion: 0.108 seconds, 50.148 MB allocated;
* qadd conversion: 0.046 seconds, 43.148 MB allocated;
* top conversion: `std::bad_alloc`, failure after 26.061 seconds overall,
  max child RSS 8,378,008 KiB.

The arithmetic tile is now bounded. The unresolved compile cost resides in
the remaining top (staging, transposers, score tree, controller, testbench).
This does not establish a functional defect or achieved hardware timing.

## Next controlled steps

1. Add the existing staging module as a compilation boundary, same source and
   parameters, under the same cap. If it fails, the failure identifies that
   subsystem separately.
2. Compare lower compiler loop-unroll settings without changing RTL. Track
   generated-code count, max RSS and compile time as compiler metrics only.
3. Before accepting any numeric result from hierarchy: run flat and hierarchy
   on identical reduced fixtures and compare all exact score/PV outputs,
   issue/output cycles, errors, faults and source hashes. This control is
   explicitly not full-shape evidence.
4. Run the unchanged full geometry with T=128 window-only and T=640 mixed
   stored-format fixtures. Golden must check all QK/PV outputs; backpressure
   seeds must be replayed. This is standalone numeric attention, not softmax
   nor a full layer/token.
5. Compose with delayed-completion HBM producer gate from
   `/tmp/ds-layer-write-compose`: replace only KV test source with the source
   stream, preserving job/q/p and credit control. Then put actual SU softmax
   between QK/PV (separate owner/integration gate).

## Interface to HBM service owner

* `job_v/job_ready`, `job_t[15:0]` (<=640 rows).
* `q_v/q_ready`, `q_w[8191:0]`, one BF16 head vector each of 16 transfers.
* `kv_v/kv_ready`, `kv_m[3:0]`, `kv_w[16959:0]`, four packed rows per beat.
* score output `sc_v`, `sc_row[15:0]`, `sc_m[3:0]`, `sc_y[2047:0]`,
  `sc_f[63:0]`; return one score-beat credit using `sc_cr`.
* `p_v/p_ready`, `p_w[511:0]`, two rows x16 heads BF16 per word.
* PV output `pv_v`, `pv_c[7:0]`, `pv_y[32767:0]`, `pv_f[1023:0]`;
  tile k returns dimension `k*8+pv_c`; credit `pv_cr`.

Do not infer full-layer cycles by adding detached shard wall times. A
hierarchical simulator retains every RTL clock edge and handshake; detached
arithmetic replays need an independently verified shared-resource scheduler.

## Follow-up: explicit composition budget, September 29

The staging hierarchy plus `--unroll-count 1 --unroll-limit 131072` still
fails the top under8 GiB. Staging compiles in0.024s/37MB; therefore the
transposer/control/testbench composition remains the compile target. Setting
unroll-limit to1 was rejected during constant/generate-loop evaluation; that
negative command/log is retained. Do not use that flag combination.

### Real controller diagnostic (not numerical verification)

`tools/run_attention_cadence.py` uses the actual full-geometry controller and
staging, with explicitly named zero-arithmetic stubs and deterministic input
cadence. The control source is unmodified. This isolates issue/credit/fill
scheduling; it does not verify QK/PV arithmetic or connect real HBM/softmax.

Observed cycles are bench-relative; the synthetic probability producer waits
for all score valid events. Score timing depends on the declared stub latency.

| Rows | KV beat gap | QK first..last | PV first..last | KV starvation cycles |
|---|---:|---|---|---:|
|128|1|18..49|114..169|0|
|640|1|18..177|242..553|0|
|640|4|18..642|707..1018|465|

At full shape160 PV issue beats occupy312cycles. Each32-row block requires
16 probability input words on a1word/cycle port, but only8 compute beats.
Thus probability loading bounds sustained PV arithmetic issue utilization to
at most50% in this organization before other stalls. Additional MACs do not
remove that producer-port limit.

The service owner separately measured the real packed WINDOW merger emitting
one4-row beat every4cycles to an always-ready sink (1row/cycle), while QK can
consume one beat everycycle. Therefore the contracted source cannot support
the engine's ideal4rows/cycle; the gap4 diagnostic measures the controller's
reaction to that mismatch. Service refill latency remains separate and cannot
be hidden without an explicit overlap/lifetime design. Two adapter descriptors
currently refill the same WINDOW again; that duplication needs architectural
review rather than silently crediting retained data.

### Finite buffering explicitly visible in this full-geometry RTL

* Packed staging:640 rows ×16 groups ×265 bits =339,200 bytes,
  including1,280 bytes of per-group format flags beyond528bytes/row payload.
* Transpose double buffers:64 tiles ×2 halves ×32 rows ×8 dimensions
  ×18 bits =73,728 bytes.
* Stationary tile operands:64 tiles ×3 banks ×16 heads ×32 lanes ×16bits
  =196,608 bytes, separate from staging and transpose buffers.
* Initial score credits64; PV credits64. These credit counts must be matched
  to real consumer buffering, not replaced by infinite-ready sinks.

These quantities are RTL storage-bit accounting, not routed SRAM area. Other
pipeline registers and PV merge rings are additional. A338KB packed-row buffer
budget alone does not cover the complete attention engine's storage.
