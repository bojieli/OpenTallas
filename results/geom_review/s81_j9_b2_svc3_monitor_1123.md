# S81 J9 B2 SVC3 monitor corridor, 2026-11-23

The viewed plan image on E10 is `/srv/opentallas-scratch2/claude/s81-j9-r6/compose/svc3_monitor_codex_1438/svc3_monitor_b2.png`. Exact B2 r1 source `a6e153d98ff6` produced `ebe2f8d53364` with tool `084de3f898c2`. The static worker `oth-ubuntu-3840968-1795473422` completed successfully.

The ready, fault and forwarded clock start on the east of `fW0_p1_b0` and enter the west of `svc_3`. The stock planner inserted 11 shared relay sites through the intervening soft station and service slots. The longest of the three chains' 12 physical endpoint estimates is 291.3493 µm versus 3,029.632 µm before relays. The landing-contract errors fall from three to zero. The stock primitive adds 11 monitor-status cycles and zero data cycles. No other edge changed.

The sites clear the planned hard boxes. Site 9 has the smallest center-to-box clearance at 2.62 µm. Some planned links pass over hard-core footprints, so they need the available upper-metal tracks after die clock and power reservations and legal drops into the relay sites. This picture shows the plan geometry.

**PASS-COND for J9 compose and strict RTL bind.** Physical route qualification is held. The emitted RTL builds the monitor cells, while the current physical `landing_route.network` bypasses the relay sites and connects the original endpoints. The physical route kit must instantiate and place the segments before using the new reach claim.
