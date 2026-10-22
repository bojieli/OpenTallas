# Explicit archive binding proposal; no full generator launched

The two SV files are immutable bench-composition overlays for ROOT review. They explicitly bind eight outer datapath instances to five existing genuine DPI library specializations. The original arithmetic RTL and all 35 child archives remain unchanged. The PV alias contains wires and a constant generate choice only; unsupported parameters fail elaboration. The source diff changes module bindings, not arithmetic, pipeline registers, clocks or the supplied stimulus/checks.

`proposal.json` pins the selected r17 source, existing source/tool/child-command readset, five binding choices and parameters, original/overlay SHA256 values and all final implementation archives. Reference module defaults and explicit specialization commands were checked against the retained original source. This is a change in elaboration/DPI scheduling, so current-vehicle numerical and timing equivalence is not assumed.

The tiny real-archive probe uses original N=32 RTL, an actual compiled DPI library, direct-original comparison, two resets, 120 rising edges / 240 half-cycle comparisons and nontrivial retained state. It passes; a changed input at one bound edge is caught after the retained-state delay. This proves a tool mechanism only.

The prior 384 GiB attempt failed in the Verilator top frontend before new C++ generation or make. Its log lacks pass-level tracing, so the exact optimizer pass is unknown. The selected predecessor top aggregations include full native QK/PV arithmetic despite the implicit hierarchy map; a tiny run reproduces that retained implementation state. Explicitly naming the real protected modules targets that expansion. C++ output splitting is not offered as a remedy for frontend memory.

After ROOT review, the proposed next attempt is one top-only frontend at 64 GiB with normal unpinned scheduling, using these overlays and the unchanged implementation archives. A completed binary, archive verification, all real-layer/group handoffs and numerical/timing/causal replays remain mandatory. No rate, full current-die, physical or functional-stub credit is claimed.
