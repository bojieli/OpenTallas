# Replay: HBM accelerator study (2026-10-03)

Model only: no RTL, no P&R, no inference. The run is deterministic and takes under a second on any host.

    python3 results/uarch/hbm_accelerator_study_20261003/ladder_model.py --out results/uarch/hbm_accelerator_study_20261003/ladder.json

- **In-tree inputs:** the sha256 of each is pinned in `ladder.json` `inputs_sha256`.
- **Branch inputs:** these are constants in `ladder_model.py`, each with its branch and commit (`branch_inputs`).
  - W19 composed token: `claude/w19-hbm-token 71b3ffc52`, sha256 785b2a30…
  - DSpark verify by P: `claude/v41-hbm-speculation-20261003 d2aff19ef`
  - C1/C5hc link fits: `4ec2eef0e`
  - Async collective: `839bab031` / `d79a2089c`
  - Streaming HBM: `52ce3e9c1`
  - Service term: `results/uarch/v41_hbm_service_term_20261003`
- **ASSUMED constants** are labelled in the source:
  - DRAM mm² per stack
  - shared-expert hide window
  - serial share of local time (0.75)
  - 1.091 GHz serial clock
  - optimistic switch latency
  - Qwen3.8-27B configuration
