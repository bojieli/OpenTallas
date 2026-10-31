# QC (qwen_compute die) release notes

## Assumed PHY IP geometry

- **QC.PHYPG: PHY power contacts (OWNER ruling, 2026-10-30 18:35 PDT, final).** Each PHY supply/return source is modeled as a 30-um finite M9 contact pad, using the same ot_pad model as the core pads. Neither the PHY IP vendor nor a measured abstract has confirmed this geometry.
  - Result with this model: combined VDDPHY+VSS worst-case IR drop 11.22 mV (supply 1.68 + return 9.54) at u_b459 on the n9 coupon serdes_low_west, against a 35 mV limit: PASS. The earlier point-source model gave 39.74 mV. Source: DIE-QC-49/pg, COORD-REVIEW-QUEUE 13:43 PDT 10-30.
  - Decision: no extra PHY bumps or straps.
  - If the real PHY IP contact geometry differs, QC PHY PG must be re-run.
