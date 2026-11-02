# L730 actual source producer frontier

FAIL declared source placement; exact selected native port/view join HELD. No P&R/STA or repair adopted.

Reviewed L730_source_frontier.png. Moving the output pin window down to E136.128..413.2947 shortens its downstream seam, but leaves direct producers in the upper/central cuts. SOURCE13's single u_bout_L730_o captures1022 ctl bits and320 bits from each operand store directly; its input does not use the other xo boundary FF copies. No L730 internal-station conn exists in either declared type or core_conns sidecar.

Even allowing each source pin ANYWHERE in its declared matching-name core bounding box gives new lower bounds1416.272..1586.384um (ctl),598.256..651.640um (opstore_a),439.640um (opstore_b). All1662 data bits exceed405um. Original remote plan_s11/d44r's E647.648..924.8147 already had lower bounds904.784..1074.848/86.768..140.024/439.640..457.088um. Existing source-to-face closure was already missing; the window move increases the ctl minimum from2 to3 added banks and opstore_a from0 to1.

Under this declared placement, a repair needs at least3/1/1 extra banks for the three producer groups. Equal payload latency needs at least3 added cycles (+2499ps at833ps),4986 data FF plus3 epoch FF per type before clock/reset overhead. These are mathematical LOWER BOUNDS; exact native port locations, macro streets and body-aware bank allocation can increase them. No source/profile/R8/calendar change was made.

The current SOURCE13 ctl producer port and both cmd0_Q producer vectors have zero exact-name matches in their three declared native pin files. Do not infer aliases to older native port names. Their physical source-view join remains HELD, so this report rejects the declared plan; it does not claim qualified actual placed source ports. Reconstruct current selected native port-compatible views or supply an explicit proven native mapping before source-to-face siting/miter/model adoption.

Actual source: Intel1 tok-qk-2-hbmsrc-1101/source13/stage13/bound/hbm_arch_q_b113__physical_v1.sv. Original physical sidecars: Intel1 die-hbm-57/plan_s11/d44r (core_conns symlink resolves to codex-hbm-stationclock-1101/s11). Candidate: coord/tmp/codex-hbm-d44r-2039/entryO_union_clock.json. Retained input copies and generator: /srv/opentallas-scratch/claude/codex-hbm-l730-producer-2240. No heavy job launched for this finite frontier.

Current entryO L730/L730m natural latency is45 cycles (43 FT +2 boundary). The missing upstream relay minimum is an additional3 cycles, hence at least48 if this repair is selected. Preserved SOURCE13 still describes42; source/profile join is outstanding.
