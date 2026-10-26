Host native ingest loop-scope fix, 2026-10-26

qkd_host_native_engine's module-scope gi was assigned by both the combinational
granule walk and the clocked QPIPE=0 bank-write loop. Yosys proc/check therefore
reported a 32-bit $adff driver conflicting with the combinational constant 4,
even in the production QPIPE=2 core. ob/oh/l also inferred artificial loop-index
latches in combinational blocks. Declare each loop variable inside its loop.
No data, control, pipeline, pin, or reset cycle changes; model delta = 0 cycles.

Actual qkd_hr_ingest_eng wrapper at production HD128/KVH2/QPIPE2: Yosys proc/check
reports zero problems (formerly two constant-driver conflicts). Smallest engine
lockstep uses immutable old RTL at 1d85ca644 against the candidate, HD128/KVH2,
QPIPE2/NATIVE_ROWS1, all core clocks at 833 ps. Eight real QKV descriptors, 2048
BF16 input beats and 2048 emitted sectors pass edge-by-edge output/handshake,
completion, and counter comparison in 2772 cycles, with write backpressure.
QMUT1 lane-retag control is caught on w_data at cycle267.

Admitted job epyc2 oth-ubuntu-1512715-1793007887, run root
/srv/opentallas-scratch2/claude/codex-kvhr-ingest-lint3. Two setup failures retained
at sibling -lint and -lint2: non-deferred default-shape elaboration hit the
intentional unsupported QPIPE2/BB1024 $fatal; hierarchy -chparam hit Yosys's
module-name assertion. Using the actual parameterized wrapper fixes both.

Reproduce engine lockstep: run prepare.py WT OUT, generate the 2-head price
fixture with tools/qwen_host/native_fixture.py OUT 2 price, copy run.sh into OUT,
then execute it through ot-run. prepare.py pins the original engine source and
emits a parameterized lint top rather than relying on hierarchy -chparam.
The actual recorded lint used the current core wrapper's identical parameters.

No P&R/STA/SIGNED claim. The host ingest core's separate raw-cut boundary
obligations (324 unregistered outputs,256 dropped inputs,772 multi-capture bits)
remain with PATH-KV; this closes its source-lint blocker only.

Exact clock receipt: nominal833.log/mutant833.log supersede the initial logs for
the clock label. The initial test's 1ps precision rounded 416.5ps half-cycles to
417ps. The corrected helper uses 1fs precision and asserts every clock period
is exactly833ps. Re-run epyc2 unit1585257-1793008816 (codex-kvhr-ingest-833)
passes the same2772cycles/2048beats/2048sectors, and catches QMUT1 at cycle267.
Original functional-cycle logs remain as history; physical constraints and RTL
never changed. No timing closure is claimed by this simulation.
