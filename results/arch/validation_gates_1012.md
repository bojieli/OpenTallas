# Academic-validation gates (owner, 2026-10-12)

Final-evidence runs are GATED per design target. A target enters its final phase only when BOTH hold:
1. its RTL is frozen (all elements closed and throughput-qualified, no pending RTL change);
2. its die floorplan has converged (die GRT 0 overflow, die STA TT setup / FF hold >= 0 on real views).

Until then die-level work iterates in parallel with element closure (GRT / STA / CTS plan / IR per contract version), and per-layer runs are smoke tests, not evidence.

## Gated final tasks (per target: Qwen ROM+KV, DeepSeek ROM S81, HBM R25GQ)
| Task | Gate | Notes |
|---|---|---|
| Representative-region detailed route (worst congestion, longest links, IO edge, dense column) + GRT-vs-DRT error bar | RTL frozen + floorplan converged | ~4 regions per die; no flat full-die DRT |
| Composition at target context (one layer per type + head; Qwen P8191, DeepSeek P1048575) on final RTL | RTL frozen | evidence of record |
| One regression of the e2e vehicles (Qwen token, S81 per-layer vehicle, HBM native die e2e) | RTL frozen | |
| IR and CTS skew plan on final views | floorplan converged | |
| Array / multi-die tok/s: measured die cycles + RTL stage-bench link/collective latency, composed analytically; correctness from the functional array oracle + per-die exactness | per-die evidence done | no whole-array RTL simulation unless the owner asks |

## Status
| Target | RTL frozen | Floorplan converged | Final phase |
|---|---|---|---|
| Qwen ROM + KV | no | no | not started |
| DeepSeek ROM S81 | no | no | not started |
| HBM R25GQ | no | no | not started |
