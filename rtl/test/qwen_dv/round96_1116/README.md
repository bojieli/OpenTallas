# Native round96 and selected matrix timing

The off-by-default OT_QC_AR_ROUND96 selected-source patch pauses O80 and Down48 edges between their three rounds. It retains one GO, one X epoch and every accepted address/read phase. QKV, GU and HEAD37 do not match its complete instruction predicate. The before-build model budgets12624 FF (48 head controllers,1536 tile issue controllers), unchanged memory/interface ports and no floorplan fit claim.

Measured head and selected production-tile control streams match baseline except the required round dates. One actual G4/NPL2 arithmetic leaf independently checks all48 O and144 Down partials against FP32 integer gold. The epoch/cache mechanism and actual source installation remain separate requirements.

A55-edge station skew makes legacy pre-near configuration invalid for Down. Native O/Down configuration instead uses the real gap AFTER the complete rawnear burst and six edges BEFORE rawfar; exact payload and three-round controls pass. Flat cmd_i→station cfg is3 edges, so compiler lead is9. QKV/GU configure before rawnear with pinlead61/compiler64. The compiler checks all88 config windows and refuses to move a Down command across the live-near boundary. The original61-lead/96-round failures and the wrongly expected O20 negative are retained.

`prepare_native_round96.py --head-source SELECTED_HEAD --tile-source SELECTED_MATVEC --out NEW_SOURCE_DIR` checks exact input hashes and emits patched copies. Set the define only with those selected sources. The CB55 station is installed separately by stn55_source_profile.py. No physical view is qualified here.

The native matrix profile is results/rtl/qc_mat_native_1116/mat_ages.json. Use these exact compiler inputs:

```bash
export DV2_S8DIE=1
export DV_LOWER_VFLAGS='-DOT_QC_SRAM_MIF -DOT_S8_CROM_ALIGN -DOT_QC_AR_ROUND96'
export DV_SU_AGES=results/rtl/qc_mif_native_1116/composed_base_3_1/slice_ages.json
export DV_VEC_AGES=results/rtl/qc_mif_native_1116/composed_base_3_1/vec_ages.json
export DV_MAT_AGES=results/rtl/qc_mat_native_1116/mat_ages.json
PYTHONPATH=tools:tools/qwen_layerbench python3 tools/qwen_layerbench/dv_layer.py --out /tmp/native_matrix_layer.json
```

The candidate analytically emits406 entries, no command/occupancy clashes, layer6783/chained6750/cold7264 before the separate current X/cache and physical joins. This is a native base calendar, not a final rate or bound programme qualification. LM/amax is deliberately absent. Legacy untagged profiles retain their previous behavior.

Original terminal units and fixtures remain E7 recovery1116/{round96_1116,round96_head1116,round96_lane1116,stn55_repeat1116,stn55_sender1116,stn55_late_payload1116}. Reproduce only a changed mechanism through normal admission; the source capsule contains the exact selected tile closure and observation-only issue trace. Station fixtures use results/rtl/qc_stn55_1116/source_capsule.tar.gz; the latepayload fixture includes exact integer-gold oracle. No whole-array simulation is needed.
