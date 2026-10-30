# Pre-route review 2026-10-30 03:43-03:49 PDT

Personally viewed BD `bd_before.png`, ring `ring_before.png`, query `query_plan.png` and `query_context.png` at localhost `/srv/opentallas-scratch/claude/codex-hbm-cores-1030/`.

BD source: epyc2 hbm-cores-kits-26/bd/*k26s/rev/auto_geom.png. Uniform free logic, dense S face, GRT0 and r2r298.89; no macro walls, centre clock. PASS-COND unchanged geometry for correcting stale GRT clock lock only.

Ring source: epyc2 hbm-cores-kits-26/k31/kits/*ring_ag*k26c/rev/auto_geom.png. Quadrant logic, clear centre clock, no macros, full-face pins. Independent GEOM74PASS03:20. PASS-COND data drive repair; identical outline/pins/source, no clock ECO. Failed routed verdict preserved.

Query source: intel1 codex-hbm-cores-1030/query/review/ot_hbm_idx_query_static_8685b722456c/{plan,context}.png. N pin spread repaired, no partial face. E density7.3/um is budgetWARN per existing10-27 rule; measured GRT/pin access decides. Five macro positions unchanged,12.96um channels and centreclockclear per previous static review. PASS-COND PLACE+GRT only; actual macro/clock/reach image must pass before CTS or route. No old GRT result counted for new kit.
