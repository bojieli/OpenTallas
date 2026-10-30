# Coherent HH candidate with mandatory seam pins

Actual unadopted plan: intel1 `/srv/opentallas-scratch2/claude/codex-hbm-1030/hh_seams2/die_plan.json`, based on d32q. Constructor shrinks L4/L4m2816→2784 without moving their windows or old Northern/prHCOL timing. It preserves width+1 payload/epoch bit sites, adds two detours2807/2762bits using ordered pin-aware routing, and groups the existing22bit L96/m with the corresponding new lane for R8.

L700 NE→NW18cycles, L701 reverse21cycles. L96m6pad→18, L969pad→21;330control FFs, not global2816bit padding. Actual native allocation differs from the initial hypothesis: the full Southern2224bit VMS words are entirely on L700/L701; L96 contains22HCOL bits, reverse L96m22obs bits. Explicit groups align every actual cross-hub landing. Northern VMS2224 and old prHCOL280+280 stay at11cycles.

Actual strict all-gap bind on unchanged current cached source:81→79UNPLANNED pairs,57312→51807unboundbits, no new EMIT/tied/undriven/multiply-bound. This is partial bind progress, not full source closure. Supplementary mandatory LOAD provider/physical Engram mapping gaps remain independent. Native_summary contains actual per-sink bit counts and bound depths. G0C remains exactly8inherited core_face errors and128pending views,0new.

Crucial correction: the first owner-only DP result passed G0 but failed actual geometry because it ignored intermediate pin windows. seam_guard_control contains the measured negative and positive controls. New first/last FFs are within30um and via-seam hops within364.5um at the slot-centre level. No per-bit or physical signoff claim; see results/geom_review/codex_hbm_hh_seams.md.

Mapped generic NW glue after this event is375862cells (hard stubs re-applied AFTER dependencies, same corrected method), below400k; this count is emitted logic excluding hard children, not an actual physical fill/route result. Extra physical wrapper/FIRM allocation and new provider type costs must be separately included before P&R.

The unchanged shared-table VMB core-face defects were also tested with all four existing mirror choices:0improvements. Consistent bank/consumer placement remains required; no per-instance pin exception or new view was adopted.
