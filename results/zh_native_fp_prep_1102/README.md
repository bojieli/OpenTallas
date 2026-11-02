# Corrected standalone Q6 ZH native floorplan capsule: PREP ONLY

No CAD dispatch and no ot-run controller. This is not a release of ZH floorplan or reuse of an old AHUB selected model.

Owned finite capsule: intel2:/srv/opentallas-scratch2/claude/codex-zh-native-fp-prep-0705. kit/ is an own copy of the a7f357a7f corrected candidate, plus genuine retained stage1 results and authentic logs, and the complete normal admission-tools bundle. EXPECTED.json pins89 input files. guard.py checks every hash and rejects any existing stage2/3/4/5/6 output. Compared with the retained source kit, only io.tcl, pins.json and generated .kw_inputs.json differ. All RTL, both SDCs, defines, native config and other helper inputs are byte-identical. Three authentic SYNTH hashes match the prior independent source join.

KW-RESUME FULL/SYNTH remains unchanged. Proposed classification is MANUAL_PHYSICAL_CONTINUATION, consistent with parent/FLOW's narrow finding that physical IO references/read-only unknown bookkeeping roots caused conservative FULL. No cache PASS, fingerprint override or forced synthesis reuse is asserted.

Proposed native targets are exactly do-2_1_floorplan, do-2_2_floorplan_macro, do-2_3_floorplan_tapcell, do-2_4_floorplan_pdn, do-2_floorplan and do-2_floorplan.sdc. inside_fp.sh records the same ordinary native stage API used by the reviewed RECIP floorplan. Its dry mode uses make -n; it has NOT BEEN INVOKED here. A future release must admit one normal measured job, run dry first, reject any synthesis or stage3+ command, and recheck exact inputs. No job is authorized by this packet.

Measured same-source actual ZH original2_1_floorplan peak699272KB,97.91s; actual retained synthesis peak564648KB. Thus proposed4GB/1thread/disk2GB has measured margin. Output scope must remain stage2 only, followed by actual OpenDB rows/PG/IO geometry query and LOOK before separately proposing PLACE.

Actual corrected generated geometry was already rendered and LOOKED in a7f357a7f: results/q6_resume_capsules_1102/owned_capsule_geometry.png (and results/q6_geometry_prep_1102/q6_corrected_generated_geometry.png). This ZH151.2square full-face268-south-pin case preserves source ABI/clock/reset and every existing other-face shape. It is separate from the published old ZH geometry with42.1% south-face span; no alias, borrowed proof or old-Lib/new-clock-graph substitution.
