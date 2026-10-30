# Parent-owned b102/b103 slot-swap candidate — reset park

This is the single structural candidate requested by the HBM die owner. It swaps equal-width NW_b102/NW_b103 origins and mirrors the move on NE, preserving types, core local coordinates and clock contracts. Only eight affected original lanes are rerouted. It remains **unadopted**.

The source is d29d, SHA256 `1aefc6184b2a390f1599599878b65245b208778fe6f97f6607ee9f246fbccce3`. The candidate is intel1 `/srv/opentallas-scratch2/claude/codex-hbm-bind-2249/swap102/die_plan.json`, final SHA256 `78132fc14f363618bea09da043897cb17d1dde4b5584f7989dabb8198b1dd700` after latency generation.

The estimated b102/B013 overlap grows from 60.48 to 492.48 um (not the full 708.48-um partition width). Gross face supply is about 2,954 pins at six per um, against 2,747 including epoch for the proposed 2,746-bit source feed. Existing occupancy and a complete feed path remain to be constructed and checked.

Generation rebuilt all eight original affected lanes with zero lost lanes and zero declaration conflicts. L48 and L48m increase 64→69 cycles; L53 and L53m decrease 56→54; L164/L179 and mirrors remain 2 cycles. No additional source feed lanes are built here. The constructor now refuses any candidate with a lost original lane and refuses to reuse an existing output directory.

Collected before reset: G0 PASS, zero errors. G0C FAIL, eight errors and 128 pending views (the error count matches the base; the exact error set was not re-compared at reset). G0/G0C jobs are terminal. No P&R, STA, bind, token or adoption claim is made. Global clock/PG sidecars and moved-type internal station/FT-band reconciliation are not updated; these are explicit next steps for the die owner.

## Metadata alias incident

The inherited event writer hardlinked every sidecar, then wrote `replan_report.json` through that link. This changed the d29d inherited replan report to the swap report. The source plan JSON remains byte-identical at the SHA above, and no source core file was written. The own `g0_report.json` link was caught and removed before the G0 checker wrote, preserving the canonical G0 receipt. The own replan-report alias was subsequently broken and its bytes preserved.

No guessed restoration of the inherited report was made: its authoritative original SHA is unknown. The parent was notified and owns recovery. `metadata_incident.json` retains the exact paths and scope. The staged writer excludes `replan_report.json` and `g0_report.json` from sidecar linking and uses a fresh latency output directory. That I/O-only safety fix was not followed by another geometry run after reset.

The last admitted planning unit was `oth-ubuntu-3848396-1793343343` on intel1. Check `swap102_event.rc`, `swap102_g0.rc`, `swap102_g0c.rc` and the corresponding logs in the run root. All own jobs are terminal; no new engineering or jobs after the explicit reset.
