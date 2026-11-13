# S81 frame event FRAME-SPINE-1113 (FRAME-FORMS-1; DIEVIEW-S81-1113 F1)

One template re-pack for the frame family col_h9 / col_h10 (216 tiles, 26 kit items) under R-STREET.
Positions and orientations only: no core shape, pin, window, port, RTL or outline changes.

Files
- `frame_spine_seed.py`  the template: writes a core_place seed per type (rules + per-type deltas; see its docstring).
- `park_taps.py`         moves non-core clock taps off the seeded cores (same names and count) before core_place.
- `cp_frame.py`          core_place.py wrapper for this family (seed-legality report; base-inherited 0.54 / 0.89 um
                         outline overlaps accepted; seeds snap to the 0.108 grid so ROM columns abut at 3.0 um).
- `finalize.py`          restores die-owned points (type clock tap, reset tap, edge clocks) that core_place carried with
                         a core, and sets every core tap to base + its core's displacement.
- `run_types.sh`         seed -> park taps -> core_place (seed only, no search) -> street_rule check, for a type list.

Base plan: ready12b-A 18c864518844 (events/s81_ready12bA_1112/plan_ready12bA_18c864518844.json.gz).
