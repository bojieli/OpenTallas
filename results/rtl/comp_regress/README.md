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
(no green yet: everything), then collect on the next pass:

    17 */6 * * * cd $HOME/OpenTallas && git fetch -q origin && python3 tools/comp_regress/regress.py nightly --host ot-epyc1tb >> $HOME/comp_regress_cron.log 2>&1
    47 5-23/6 * * * cd $HOME/OpenTallas && python3 tools/comp_regress/regress.py collect --host ot-epyc1tb --root /srv/opentallas-scratch/claude/comp_regress/$(git rev-parse --short=9 origin/main) >> $HOME/comp_regress_cron.log 2>&1

## Results

| src | host | runs | verdict |
|---|---|---|---|
| `ca7ca4fff` | ot-epyc1tb | qrom_pos L3 (L0-L2 chain @P8191, 17,120 cyc, 0 X / 0 K/V mismatches), qrom_neg L3 (COMP 0: 49,152 X / 6,046 K/V mismatches = FAIL as expected), qrom_pos head (token 24, logit 0x41962749, 3,055 cyc) | all ok (`ca7ca4fff/summary_epyc1tb.json`) |
