# L0 PC24 diagnosis: how to replay

The run re-executes the original w17 L0 TP-4 die-group configuration. That is source commit
4e38326d6f361bc85e660f48c59c355e2bb95274, the r4 compiled models and the r3 images with program sha256 e3d93b7b...
It adds a read-only observer.

## Observer

`rtl/test/dsrom_sys/l0diag/l0diag_die_rt.cpp` is a copy of `rtl/test/v41_runtime/w17_current_fastpp_die_rt.cpp`
(sha256 8d1b7a55...).

- **Default off.** Without `-DL0DIAG`, `g++ -E -P` of the copy is byte-identical to the original. Both hash to
  64c7dd37...
- **With `-DL0DIAG`.** After every host cycle the observer reads the original compiled Verilator models' internal
  state through their `rootp` members. It never writes to a model member, and no model or RTL file is recompiled.
  Only the host driver is re-linked against the unchanged r4 `.a` archives.
- **This is a SIM-ONLY observer, not RTL successor ports.**

## Build

Link time is about 2 minutes. `link.sh` is recorded in `launch_manifest.json`:

    g++ -DL0DIAG=1 -std=c++20 -O2 -pthread -DROM_PHW=6 -DCL_PW_BITS=547 <r4 include dirs> l0diag_die_rt.cpp \
        -Wl,--start-group <r4 build/*/V*__ALL.a + attn libs> -Wl,--end-group verilated{,_threads,_dpi}.cpp

## Run

    RT_WATCHDOG=100000 L0DIAG_EVERY=200 L0DIAG_STOP=20000 L0DIAG_SKIP_VM=1 \
      v41_die_rt_l0diag <images r3 copy> <out> 400000

Outputs:

- `progress.log`: the original's PC trace, for the identity check.
- `diag.log`, with three kinds of line:
  - `# ST/# CT` headers that name the fields;
  - `CH <cyc> d<k> field=hex...` lines, change-only;
  - `SN` snapshots every 200 cycles, which also carry the decimal counters.

## Record

    python3 tools/dsrom_l0_diag_record.py --run-dir <out> \
      --orig-progress /home/ubuntu/w17-current-L0-fastpp-20261001-r4/L0_output/progress.log \
      --meta launch_manifest.json --out l0_diag.json

## Cost

- The original's own measurement was 1.28 CPU-s per cycle and 12.8 GB RSS.
- On 2026-10-03, ot-pve1 had a load of about 87 on 28 cores. It sustained about 6 s per cycle at about 1.1 cores,
  which is about 20 h to reach PC24 at cycle 12,400.
- On a host with 4 free cores, the run takes about 72 minutes to reach PC24.
