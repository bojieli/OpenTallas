# HBM VM calendar a4 — current actual placement review

Verdict: PASS-COND under the EXISTING exact G7(B) FILL+ASPECT exception, via normal rejudge classifier only. Retain the raw AUTO FAIL; no new waiver or physical timing credit.

Personally viewed intel2 `kit-wave/hbm/d44o/items/hfd_hgi_vm_calendar_f20/attempt_4/geom/auto_geom.png` (copied to `/srv/opentallas-scratch/claude/codex-geom-1101/vmcal_a4`) and parsed its actual JSON. The241.92×116.64um outline has one SRAM at43.65% area, a coherent N-side standard-cell band and W/E legs, with open side channels.14901 cells/3233FF; GRT0(converged27), r2r267.79/0>405, pin-reg p90/max7.57/23.13, no unregistered pins/macro overlaps/relay collapse/blocked channels, clock-entry reach200.19um. Raw failures are aspect2.074, fill12.99%, empty58.17%.

Exact standing authority: COORD-REVIEW-QUEUE line8436,2026-11-01 04:42 GEOM103 G7(B), same hfd_hgi_vm_calendar_f20 core/outline/N-strip+W/E-leg form and~43.7% macro; it explicitly concurs with FILL+ASPECT release via `--write`. Current reach/pin metrics are comparable or better. FLOW was asked to apply the existing classifier normally, without changing source/pin contracts. CTS must still measure its real leaf reach/clock tree and propagated timing; routed DRV/DRC/own equivalence and current source/parent joins remain required.
