# S81 actual die pickup (2026-10-19 17:38 PT)

All eight exact native case-strap receipt cells now report `die_bindable.ok=true`, `native=PASS` in the live element API; job identities are included in landing_api_receipt.json. This completes the pending table synchronization for S81.STA.LAND and S81.STA.OWN.8. Existing static strap assumptions and die SDC obligations remain. This is a receipt pickup, with no new engine run.

The mu4 chain remains live before repeaters (BIND_RC=CASE_RC=MAINCHK_RC=0, run.log ends OT_DIE_REP pre instances=13067); mu3c is GRT extra9/30 and mu2 extra18/30. No final overflow, TT/FF lane result or die-clock result exists yet. THIN x_f_4L10_l1 is seven stages /276bits in actual mu3c case, with frame_lane_pins_mcp landing model; historical model margins are not a current real-view timing PASS. Preserve all live jobs.

Strict mu4c source 19bf4121e remains unread0/open10, all other counters0: SM w_* outputs have no genuine target consumer. A separate fresh target owner now owns real local SRAM-backed storage; no bind waiver, fabricated sink or new duplicate die chain was added.
