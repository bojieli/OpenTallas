# Die-level composition regression (comp_regress)

Tool: `tools/comp_regress/regress.py`, registry `tools/comp_regress/runs.json`.
Purpose: keep the required per-layer composition runs of `results/rtl/die_sim_inventory_1012/README.md` green on main
without re-running all of them for every commit: each run is mapped to the repo files it reads, and only runs whose
files changed are re-run.

## Model

- **build** = one simulator binary (`hgi_*`: `tools/hgi_e2e/run.py script` with `--real` units / generics / a mutant define;
  `qrom_*`: `tools/qwen_missing/partition_token.py build`, split partition s22ml7, `--comp 1` / `0`).
- **vector** = one exported stimulus + golden (`tools/hgi_e2e/export.py`: DS-V4.1 layers 0/1/2/3/14/20/21/24/37 and head at
  P 1,048,575; Qwen3-8B L0 and LM head at P 8,191). Exports need the DS 1M refs / Qwen snapshot (fixture host ot-epyc1tb).
- **run** = build x vector (or build x stage) with the expected verdict: `pass`, or `fail` for a mutant
  (`IDX_MUT=2`, `DMA_MUT=5`, `OT_COLL_AMX_MUT_MIN`, `--comp 0`). A run is ok when verdict == expect.
- **coverage** (`coverage.json`): per build, the repo files its Verilator read (all `*__ver.d` in the build dir), plus the
  build's `cover_extra` globs (generators and the RTL they read as text, e.g. the Qwen ROM core emitters). Every vector
  run also depends on `vector_cover` (exporter, hgi_sim, goldens). A build with no recorded coverage is always re-run.

## Commands

    python3 tools/comp_regress/regress.py plan --base A --head B          # affected runs for the main range A..B
    python3 tools/comp_regress/regress.py launch --host ot-epyc1tb --sha S --root DIR --runs affected:A..B
    python3 tools/comp_regress/regress.py launch --host ot-epyc4 --sha S --root DIR --runs hgi_dsall \
        --vec-from ot-epyc1tb:/srv/.../vec                               # non-fixture host: vectors copied via localhost
    python3 tools/comp_regress/regress.py collect --host H --root DIR     # -> <sha>/summary_<host>.json, runs/, coverage.json

The host driver (`DIR/drive.sh`, status `DIR/STATUS.log`) packs builds into memory waves under `--mem-budget` GB
(each build in a `systemd-run --scope MemoryMax` cgroup, 4 h cap) and starts a build's runs as soon as it links
(6 h cap each). A host without `~/OpenTallas` gets the source as a `git archive` of `archive_paths` piped from localhost.

**Cron (documented, not installed)** — localhost, every 6 h; re-runs only what changed since `last_green.json`
(no green yet: everything; B2 and tput runs are in the same registry, so a unit edit re-runs its tput bench and every
die run whose build read the file), then collect on the next pass:

    17 */6 * * * cd $HOME/OpenTallas && git fetch -q origin && python3 tools/comp_regress/regress.py nightly --host ot-epyc1tb >> $HOME/comp_regress_cron.log 2>&1
    47 5-23/6 * * * cd $HOME/OpenTallas && python3 tools/comp_regress/regress.py collect --host ot-epyc1tb --root /srv/opentallas-scratch/claude/comp_regress/$(git rev-parse --short=9 origin/main) >> $HOME/comp_regress_cron.log 2>&1

## B2 harness (stream 10, 2026-10-12)

The HBM die is now B2 (4 clusters, one per HBM stack, each with a local VM slice; slice ring + collective broadcast;
results/arch/hbm_b2_1012/SPEC.md when it lands). `tb_hgi_e2e` carries it as parameters, `tools/hgi_e2e/b2.py` as the
placement / traffic model:

- `B2 1` **OLD-VM mode** (now, before the B2 RTL): the central VM model, 4 clusters x 65,536-word slices (word address
  high bits; >= 2^18 = the HC aperture, STRIPE4 by 8-word sector). `b2.py traffic VEC` places every record on its home
  cluster (the B2 exporter's `cluster` field; old vectors: owner-computes from the golden writes, SM/SU/COLL/ATT/SFU
  records whose writes span slices are split) and writes `VEC/b2.txt` (k, home mask, ring + broadcast cycles) and
  `b2_traffic.json` (per record and per op: remote words, broadcast words, cycles; total vs the per-layer budget).
  The DPI counts every VM word a REAL unit reads / writes as local or remote to its record's home (`B2` / `B2UNIT`
  lines in e2e_records.txt -> report `summary.b2`); `B2_RING 1` adds a stub record's ring cycles to its hold time.
- `B2 2` native cluster RTL: reserved (the bench refuses it) until the cluster units are bench-clean; units switch in
  one by one through `--real`.
- Ring constants (provisional, PHY study f6467cb82): 2 links across any cut x 2,048 b each way, 16 cycles a hop, 2x2 ring
  (<= 2 hops); broadcast tree 1,024 data bits, 2 hops. Budget per layer: DS 290 cycles (B2 worst +11.6k cycles / token,
  40 layers), Qwen 93 (>= 943 vs 945.5 tok/s, 36 layers). `results/arch/hbm_b2_1012/b2_params.json` overrides them.
- comp_regress builds `hgi_b2` (all stubs), `hgi_b2coll` / `hgi_b2collmut` (real collective, AMX_MUT_MIN must FAIL).

## Per-class unit throughput benches (kind `tput`)

Builds `tput_qdq`, `tput_qdq_wide`, `tput_hc`, `tput_idx`, `tput_iks`, `tput_idx_cf`, `tput_sm` run the existing
production-shape benches (tools/hgi_unit_tput/run_*.sh, rtl/hbm_accel/generic/adapters/tb/run_sm_tput.sh) into the
build dir, so their Verilator `__ver.d` files become the build's coverage and a unit change re-runs only its own bench.
A run is `pass` when the bench's gate says GATE PASS (PASS build exact AND every mutant FAILS); the record also carries
`ratio` = RTL service / simulator price (tools/hgi_unit_tput/report.py) and `qualified` = ratio <= 1.10 (AGENTS
throughput qualification). SM / IKS / IDX_CF report the gate only.

## Results

| src | host | runs | verdict |
|---|---|---|---|
| `ca7ca4fff` | ot-epyc1tb | qrom_pos L3 (L0-L2 chain @P8191, 17,120 cyc, 0 X / 0 K/V mismatches), qrom_neg L3 (COMP 0: 49,152 X / 6,046 K/V mismatches = FAIL as expected), qrom_pos head (token 24, logit 0x41962749, 3,055 cyc) | all ok (`ca7ca4fff/summary_epyc1tb.json`) |
| `d1e95d8d1` | ot-epyc4 | B2 OLD-VM harness `hgi_b2` (all stubs, B2 1 / B2_RING 1) x 12 targets: 11 PASS (final VM / HBM exact, every dispatch == golden); ds_L14 FAIL identically at B2 0 (CFG status err 1, golden token 0: vector / harness issue, not B2); `tput_qdq` GATE PASS (m0 exact, m1/m2 FAIL) after the run_qdq.sh MODMISSING fix, ratio 13.7 (packet path, not qualified) | `d1e95d8d1/`, `b2_traffic_1012/summary.json` |

### Cross-cluster exchange, B2 OLD-VM (`b2_traffic_1012/`, d1e95d8d1)

Exposed = cycles at B2 1 + B2_RING 1 minus the same stub build at B2 0; serial = sum of every record's ring + broadcast
cycles. Placement is the CURRENT allocator's addresses (owner computes), not the B2 allocator, so this proves the
harness and sizes what the B2 allocator must remove; it is not the B2 answer.

| target | B2 0 cycles | B2 1 cycles | exposed | serial | budget / layer | exposed / budget | top ring ops (serial cycles) |
|---|---:|---:|---:|---:|---:|---:|---|
| DS L0 | 11,641 | 14,723 | 3,082 | 4,040 | 290 | 10.6x | SM.MATVEC 1,836, COLL.ALL_GATHER 1,342, GROUP_REDUCE_MCAST 448 |
| DS L1 | 14,036 | 19,404 | 5,368 | 6,667 | 290 | 18.5x | ALL_GATHER 2,398, SM.MATVEC 1,836, SU.VOP 1,727 |
| DS L2 | 20,775 | 24,374 | 3,599 | 4,624 | 290 | 12.4x | SM.MATVEC 1,968, ALL_GATHER 1,599 |
| DS L3 / L21 / L37 | 16,422 | 19,822 | 3,400 | 4,040 | 290 | 11.7x | SM.MATVEC 1,836, ALL_GATHER 1,342 |
| DS L14 | 30,489 (FAIL) | 36,249 | 5,760 | 7,251 | 290 | 19.9x | ALL_GATHER 2,655, SM.MATVEC 1,968, SU.VOP 1,762 |
| DS L20 | 20,634 | 24,348 | 3,714 | 4,843 | 290 | 12.8x | SM.MATVEC 1,968, ALL_GATHER 1,583 |
| DS L24 | 20,577 | 24,129 | 3,552 | 4,464 | 290 | 12.2x | SM.MATVEC 1,872, ALL_GATHER 1,535 |
| DS head | 4,357 | 4,357 | 0 | 33 | 290 | 0 | ARGMAX_MERGE 33 |
| Qwen L0 P8191 | 32,839 | 39,353 | 6,514 | 6,674 | 93 | 70x | SU.VOP 5,357, ATT.PV 820, ALL_REDUCE_SUM 320 |
| Qwen head | 3,267 | 3,300 | 33 | 33 | 93 | 0.4x | ARGMAX_MERGE 33 |

Findings for the B2 lead / compiler stream:
- With today's addresses every DS layer is 10-20x over the 290-cycle budget and Qwen L0 is 70x. The B2 allocator has to
  make SM.MATVEC inputs slice-local or mirrored, and SU.VOP operands (Qwen: 5,357 serial cycles) slice-local.
- COLL.ALL_GATHER results must reach all 4 clusters: 17 records, 33k words a DS layer, about 1.3-2.7k cycles at
  32 words/cycle on the broadcast tree. That is bandwidth, not hop latency, and the study's +16 cycles a record does
  not include it. Either the gathered result streams into the mirror window while the gather is running (overlap), or
  the broadcast tree needs more width, or the budget goes up.

### B2 with the real collective, and the unit throughput benches (57fff655a, ot-epyc4, `57fff655a/`)

| run | verdict |
|---|---|
| `hgi_b2coll` x ds_head / qwen_head (real COLL, B2 1) | PASS, 4,357 / 3,271 cycles |
| `hgi_b2collmut` (OT_COLL_AMX_MUT_MIN) x ds_head / qwen_head | FAIL, as required |
| `tput_qdq_wide` | GATE PASS; default variant m0 ratio 2.99 (not within 10 %) |
| `tput_hc` | GATE PASS; ratio 29.1 (not within 10 %) |
| `tput_idx` | GATE PASS; default reader m0 ratio 1.65 (not within 10 %) |
| `tput_iks` | GATE PASS (no priced ratio) |
| `tput_sm`, `tput_idx_cf` | did not build: the staged source lacked `physical/hbm_accel_macros` and `results/arch/hgi_sim_20261009` (now in `archive_paths`); re-run pending |

The `hgi_b2` rows of this summary for DS L2 / L20 / L24 predate `CP_IKS_I 1` and are superseded by `d1e95d8d1`.
Ratios are the bench's default PASS variant over all its records; the qualified variants recorded in
`results/rtl/hgi_unit_tput_20261010/` (e.g. the IDX heap engine) are separate builds of the same script.
