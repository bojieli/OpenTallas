# GUNIT internal controls and reciprocal predecode

Source b039b5b1c, opt-in CONTROL_SAFE=1 with PIN_COPY=1. Model committed before implementation in 43305e7c6. No compiler constants, constraints, physical kit, canonical default or frozen old gate changed. Model updated to account for up to408 T FF restored by preventing merged copies. No timing or physical qualification claimed.

5.050 fleet numerical8-case PASS: router56/HC964 at stop pins. Existing numerical mutants8 and10 fail104/73. Actual lastHP_N-origin HOP fixture PASS three jobs/1655beats/15CTL rows per side/50roots/two rsqrt; old759/757 and +1-age fixtures fail35. The accepted fixture retains975N/973S, not unit976. Complete source manifests and build logs remain on fleet.

Predecode2048-case registered truth-table comparison passes every512 seed/square address and both denominator-low-half polarities. Mutants invert a coefficient bit and add a predecode register edge in private files; both produce committed PREDECODE FAIL witnesses. Every production coefficient is generated from the original immutable coefficient table by gen_predecode.py; arithmetic and rounding logic is unchanged.

Current canonical mapped-only run: unit oth-ubuntu-317184-1792431238 ep6, session41663; /srv/opentallas-scratch/claude/codex-s81-gunit-controls-1019/map. This is sizing through floorplan, not a gate or CTS. Map command in map.sh copied beside this packet. All new fixed module names are SYNTH_KEEP_MODULES. Canonical keep hook is materialized from branch HEAD. Production sources in src/ and HOP sources in hop_src/ match for the four changed RTL files. No mutation while mapping.

NEXT: collect actual1_2_yosys.v/1_synth.json, rerun complete recursive fanout census (not top4), inspect consumers and proof that all enable/T/predecode copies survived; continue same-edge structural repair of remaining controls and fault depth. Verify reset/validity at assertion/release and phase changes, runtime storage/delay census, actual measured area/fill/reach and native budgets. Reset and653.5ps fault-depth closure are not established by numerical tests. No CTS/route until root source/model/checklist review.
