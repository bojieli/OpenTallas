# KV GEN9 takeover3 source hand-back

Source `390ad0bbf3`: actual SAFE2 388.8-square reservations before wire planning; per-port core clock for control/EST, measured HBM halves preserved; digest recomputed after export domain correction. Explicit source-fixed group cost is control depth+1 (1..8), upstream gather depth (0..7), EST +1, reset release +2 core/+2 HBM. Missing external lanes remain unknown. This is source/planning evidence, not a die or physical PASS.

Final fleet validation on ep4 unit4168042 exited 0: generated SAFE2 source matches; 15 clock/domain/relay/cost tests passed. Earlier ep8 attempts failed for missing pytest and unavailable ensurepip; those raw failures are preserved separately and do not count as source failures.

Minimal merger delta is cherry-pick390ad0bbf3 after GRP2a5b15ce36 hooks. Full private ancestry: current-main799eebe53 -> c1e64273f (GEN9e4eb15/current-main composition; current conflict hunks retained) -> 2cb6c1c22 (GRP2a5b15; main macro metadata retained) ->390ad0bbf3. No runtime/main writes here.

Original strict e4eb15 on ep5 failed17:04 because qkd_astk_rly_296_fl lacks selected native profile. Diagnostic prep completed17:32, bind failed17:34 because reviewed static-head role rejects newly explicit ADD_LAT=7/LTW=12 defaults; exact role repair owned by KV lead, native qualification remains separate. Diagnostic chain remains running and NOT_A_DIE_RESULT. Waiter targeting original7f run was not retargeted.

Remaining implementation: extract per-group external ages from actual forwarded/landed netlist, compose fixed captures with each group's real phase/boot/first-use/status calendar, and compare against selected hardened views/clock references. Current global programme_to_groups field cannot be replaced with a blanket+8. Source receipt is explicitly unqualified; no new STATIC_SCHEDULE/token/physical PASS is established. No GEN10 prep, new gate or physical submission launched.

Corrected EMB4bf0929ec is separate (raw d963 known unsafe); AHUBg2l input-reg -83.1ps remains failing. Actual health/fault/retire/closed-successor composition remains owned by KV lead.
