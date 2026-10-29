# SPB V3_stagger3 independent native-ODB pin review

2026-10-29 14:00 PDT. Source: epyc2:/srv/opentallas-scratch2/claude/die-hbm-19/spb/V3_stagger3/probe_grt.odb. Read-only native ODB dump through ot-run unit1158816-1793307498, exit0; no new route. Personally viewed spb_v3_actual.png.

Verdict PASS-COND for adoption of the PHY rx pin-table form only. Actual512 rx M7 pins occupy three rows y634.944/565.824/496.704 with171/171/170 pins. Global x107.68..140.32 is4..36.64um inside the PHY west edge103.68. Pitch0.192um and the staged registers outside the west edge give a coherent escape rather than one crowded row. FF count4104 and source/cycle structure are unchanged. Existing run reports GRT M6/total overflow0 and macroNoAp0; no new DRC/clock/PG measurement here.

Conditions: keep the existing modeled escape/edge-depth/upper-layer access assumptions and fixed keepouts; carry this exact physical pin table into the current plan/source bind before production routing. This interface coupon does not qualify a full die or hard core: its full picture contains surrogate FFs inside the EP abstract rectangle. No legal full-placement, CTS, PG continuity, die timing, PHY silicon or SIGNED claim follows from this pin-access review. HBM owner notified directly.
