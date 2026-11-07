# HEAD raw-export cohort diagnosis (candidate only)

The current full counter has4520 clock_landings raw-export source mismatches
and one independent native reset release qualification error. On complete pinned
93c061c396c plan/assets, samples reproduce CTL5/5, westRX1/1, SerDes3/6 source
instance/net/XY mismatches. See diagnosis.json and diagnose_g0c.py; the script
uses git only in the caller's owned repo and exports exact referenced assets.

A same-q metadata refresh is NOT a complete fix. The experimental helper fails
closed on CTL rst_start_raw_3: rst_rl_6 has no eligible raw/boot producer in the
current emitter. It must not silently choose another indexed relay or waive the
gate. That attempted helper produced no candidate output.

A separate joint derivation used existing shared reset-export/provider tools,
current93 emitter/POR geometry and retained OLD provider1251stage positions:
177 uniform aliases(13 existing outputs +164 new), maxhop402.112um,0>405;
root raw release21,relative span85, minimumSETTLE89. All25 raw-wrapper patches
passed exact registered-source checks. Crucially89 is +1 versus OLD provider88,
but +25 versus POR64. Candidate plan/provider remain mismatched and unqualified.
Artifacts: intel2:/srv/opentallas-scratch2/claude/codex-head-start-joint-1107.

Required next steps are a single coherent source/sidecar/current-clock-stage
cohort, observer binding, actual reset-phase/crossing qualification, native bind
LEC and compiler boot pricing. The existing head_start_reset_exports,
head_start_local_reset and head_start_sources tools provide the joint pipeline.
No full-die simulation or per-bit4520test expansion was run. No POR changes.

The separate reset error covers12SerDes u_phy.u_link.u_dec.u_chn.rst_n targets
on pma_rck. Metadata updates cannot grant this native-clock qualification.
