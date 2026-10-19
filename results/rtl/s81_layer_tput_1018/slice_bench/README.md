# S81 slice bench (LAYERBENCH-S81, TOK.DS.BENCH.3, 2026-10-18)

**Status: the bench works end to end on the real p4l RTL. The L0 smoke FAILS on a die gap (G1) that the bench found.**

The bench runs on die p4l (`origin/claude/s81-die6-1018` 3923ae6de, bind9 `die.v.gz`). Its pieces:

| Step | Tool | What it does |
|---|---|---|
| RTL kit | `tools/s81_dv/dv_rtl_kit.py` | Builds a variant-correct source closure from the git ref. See below. |
| Cut | `tools/s81_dv/dv_slice_cut.py` | Copies the chosen die instances verbatim from die.v and makes every cut net a top port. See below. |
| Bench | `tools/s81_dv/dv_slice_tb.py` | Generates the replay bench. See below. |
| Replay | `tools/s81_dv/dv_slice_replay.py` | Turns the compiler's `schedule.json` + `ctl_templates.json` into the replay and check files. |
| Runner and test | `tools/s81_dv/run_dv_slice.sh`, `tools/s81_dv/test_dv_slice_cut.py` | Fleet runner on Verilator 5.050, and the cutter self-test (PASS). |

### RTL kit

`dv_rtl_kit.py` resolves every module as follows:

- A module name defined twice is resolved by the hardened tiles' `physical/ref_tile/*/spec.json` sources and by the bench lists `frame_bench.f` and `svc_rs/rs_files.sh`.
- Memory macros come from `asap7_memory_macros_v2`, then `asap7_memory_macros`.
- The bind's `rtl_extra` files come from their own commits.
- Every module of every chosen file is linked.
- An unresolved child, or a duplicate module whose text differs, FAILS the kit.

### Cut

`dv_slice_cut.py` copies the instance set verbatim from die.v. It keeps the masters, the straps and the net names, and adds no ties. It then grows the set:

- **fan-in:** relay, landing, reset-station and clock-forward drivers back to the die roots;
- **fan-out:** outgoing lanes up to the neighbour's landing.

Every cut net bit becomes a top port. `slice_ports.json` records, per port, the die net, its peer instances and its kind (clock, reset, boundary).

### Bench

`dv_slice_tb.py` generates the replay bench. It drives:

- one bench clock to every region clock and forwarded-root port;
- rst_n through the real reset tree;
- the input ports from `+IN` events, at their scheduled cycles.

It checks:

- `+OUT` masked words at their scheduled cycles;
- the sticky `land_fault` bits.

It writes `+TRACE`, a record of every boundary output change.

## Slice `cut_3S` (L0 smoke)

**Contents:** `u_s_3S` (sid 6) plus its 6 frames `u_f_3[LR]0[1-3]`. After growth this is 563 instances:

- 1 slice;
- 6 frames;
- 25 landings;
- 157 lane relays;
- 366 reset stations;
- 8 clock-forward cells.

The cut has 115 ports.

**Why this slice:** u_s_3S is an interior slice, where every inbound lane has a landing. The end slices do not (gap G3).

**Cost:**

| Item | Value |
|---|---|
| Verilator 5.050 build | 43 min, 47.6 GB, 6,380 C++ files |
| Simulation rate | 57 cycles/s |
| L0 price | 15,475 cycles, about 4.5 min per run |
| Whole die (probe_v2) | Out of memory above 400 GB, so the slice is the vehicle |

## Results (`runs/`)

| Run | Verdict | What |
|---|---|---|
| `idle` | FAIL | 17 of the 25 landings raise `land_fault` from cycle 37 with no traffic: every one with K ≥ D. The 8 with K ≤ 3 stay clean. |
| `replay_L0_s3S` | FAIL | The 8 compiled L0 smoke CTL beats (prog_L0_s3S) are replayed at u_s_4S ro_w at their scheduled cycles. The real ring stop of u_s_3S forwards each beat exactly (payload, hops 4→3), but each one lands at u_s_2S 10 edges early: 130 instead of 140. 0/8 beats arrive on schedule. |
| `diag_L0_s3S` | 0/32 mismatches | Same run, with the checks moved to the measured cycle (schedule − 10; DIAGNOSTIC, not a schedule verdict). Payload and hops are exact. `land_fault` still fails. |
| `diag_mut_shift1` / `diag_mut_hops` | FAIL 8/32 | Mutants: the replay one cycle late, and the neighbour sending a wrong hops field. These are the committed fail witnesses that the checks are sensitive. |
| `lane_debug` | FAIL | Three lanes alone, at 65,700 cycles/s. The K5 lane `ld_xrW_3S_l0` runs its write counter in lockstep with its read counter (wc = rc + 1) from the receiver's reset release, faults at warm-up, and delivers the source-register word 6 edges later; the plan says 10. The K2 lane is clean. |
| `*_flighttime_tt` | not used | Back-annotating the lane flight time (−S1) as a transport delay does not work: Verilator 5.050 drops the delayed pulses, and the rate falls to 5.9 cycles/s. The idea was dropped. Without the hop-0 gate (G1), the flight time cannot reach the epoch anyway. |

**Composition:** under the fixed schedule, the layer takes as long as its slowest (critical) slice. Every slice runs the same calendar, shifted by its CTL arrival. The L0 critical slice is an end slice: it has the latest CTL arrival (u_s_0S at 56.5 edges, against 27 for u_s_3S) and it owns the TP all-reduce edge links. That slice is blocked on G3 (`set_0S_L0.txt`).

## Gaps (`gaps.json`; precise module / port / missing)

- **G1: no hop-0 clock gate.** The landing contract anchors the write epoch on a clock gate at the source, opened at edge G by the source's released reset. die.v has none: 140 `BUFx8` forward cells plus the slices' `ck_line`/`ck_v`/`ck_xc = {N{clk}}`.
  - Effect: every landing with K ≥ D aliases its ring. It raises `land_fault` and the word leaves about 4 edges early.
- **G2: sid convention mismatch.** die.v straps `sid = 2·col + tier`, and `ot_s81sl_xr` and the compiler use the same convention. `ot_s81sl_rstop` decodes `sid` as `{tier, col}` instead.
  - Effect: u_s_4S is decoded as column 0, tier N, so it skips the westward CTL re-inject. The NX snake ends are also wrong.
- **G3: end slices lack inbound landings.** 52 inbound lanes to the end slices have a land-plan E but no landing tile in die.v.
- **G4: no per-frame ROM INSTANCE.** die.v passes no per-frame ROM `INSTANCE`, so in RTL every frame of a master loads the same ROM image. The cutter's `--rom-instance` binds the die instance name and records it.
- **G5: HB on parameter-free masters.** die.v passes `#(.HB(0))` to parameter-free `lep*` masters. The kit strips it, and records that it did.
- **G6: die_port_bind closure bugs.** `die_port_bind.py` has three: it picks the first definition of a duplicated module name, its `instantiated()` misses an instance after a generate label, and it does not index macros outside `rtl/`.
- **G7: pinned-copy preference conflicts.** Tile specs prefer differing pinned copies of the same modules (recorded in `kit.json`).

## Reproduce

```
python3 tools/s81_dv/dv_rtl_kit.py --ref origin/claude/s81-die6-1018 --port-bind <bind9 port_bind.json> --top-v die.v --top dv_die --out KD \
    --strip-param ot_s81sl_slice_lepw:HB:0 --strip-param ot_s81sl_slice_lepe:HB:0 --strip-param ot_s81sl_slice_lepe_nh:HB:0
python3 tools/s81_dv/dv_slice_cut.py --die-v die.v --kit KD --insts cut_3S/set.txt --out C --rom-instance
python3 tools/s81_dv/dv_slice_tb.py --ports C/slice_ports.json --out C
python3 tools/s81_dv/dv_rtl_kit.py --ref origin/claude/s81-die6-1018 --port-bind <port_bind.json> --top-v C/slice_top.sv --top slice_top --out K
mkdir K/tb && cp C/tb_slice_top.sv K/tb/
python3 tools/s81_dv/dv_slice_replay.py --prog prog_L0_s3S --ports C/tb_ports.json --die-v die.v --slice u_s_3S --out R
ot-run --mem 140 --dir <fleet dir> -- env J=16 bash K/run_dv_slice.sh K OUT +IN=R/in.txt +OUT=R/out.txt +NCYC=255 +TRACE=OUT/trace.txt
```
