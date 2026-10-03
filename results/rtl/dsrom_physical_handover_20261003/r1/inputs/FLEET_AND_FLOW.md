# Fleet roles and flow rules (user directive, 2026-10-03)

## Keep ALL hosts busy, matched to job type
| Host | Cores / RAM | Use it for |
|---|---|---|
| ot-epyc1tb (EPYC, 5.199.165.104) | 128 threads / 1.1 TB, 2x2.9 TB NVMe | LARGEST work: die-level floorplans/global routes/PDN, full-die feasibility, big Verilator builds (>20 GB), parallel die-level variants, the DS full-token sims |
| ot-agidock128 (EPYC VM) | 64 cores / 125 GB | CPU-intensive, LOW-memory work: single-thread Verilator sims (e.g. Qwen layer-parallel jobs ~1.5 GB each), Icarus/benches, synth+STA screens, element-level ORFS with <=16 threads, campaigns of many small jobs |
| ot-pve1 | 28 cores / 235 GB, ~220 GB disk free | medium-memory sims (DS die runtimes ~13 GB), a few ORFS element runs, Codex's oracles |
| local | 32 cores / 188 GB + RTX PRO 6000 GPU | GPU work (MTP acceptance), light builds, coordination |
Rules: cap every ORFS run at NUM_CORES 16-24 (never the nproc default); check free RAM/CPU before launching; launch long jobs DETACHED with manifest + exit file and chain follow-ons (3-4 h queued); keep STATUS.md current. Spread work: do not pile everything on one host while another idles.

## Hierarchical flow: correctness and performance BEFORE element closure
Do not spend P&R iterations closing an element before (1) its RTL is functionally correct (bit-exact vs golden) and (2) its cycle/latency contribution shows the design meets the token-rate specification. Order:
1. Functional correctness (bit-exact) and measured cycles in the system context.
2. Performance check against the specification target (token time), using measured numbers.
3. Floorplan + abstracts (black boxes) and die-level feasibility in parallel.
4. Element closure only for elements whose function and performance are settled; then hierarchical composition with abstracts — no flat full-die runs.

## Disaster-class risks are cleared first
See the risk list in codex_notes.txt; checks are running: Qwen reticle fit (corridor gate), DS 1M-context memory feasibility, control-loop clock ceiling, measured-performance-vs-spec ledger, DS full-token verification at scale.
