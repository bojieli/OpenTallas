# Selected HP13 publisher local ages on the SEGCAL-regenerated source

The old receipt pins e95e85e7 and cannot qualify the selected5d45a822 publisher. This packet extracts all39 actual GI source FF statements and the publisher instance from selected cpub39_1 SHA5d45a822 and cpub39_2 SHAfc00de4f. The source tuple, clock root and output ordering are checked literally against those files; SOURCE_PUBLISH_RECORD.json is a distinct typed record, not an LP compiler record.

The minimum extracted component measures MAIN calendar capture1 + publisher1 =2 core rising edges; ALT capture1 + publisher2 =3. Each passes596 changing39-bit tuples with an independent HR clock. The existing wrong-clock and wrong-tuple mutants both fail for each variant. This prices source-local availability only. Actual GEN TT-to-native, native-to-face lanes and regional landing/clock evidence remain required separately.

LOCAL_AVAILABILITY_p1/p2.json use the typed tt_source_local.v1 schema with exact RTL, source-record, component source and measured-log hashes. tools/qwen_split/tt_source_local.py checks that schema directly; head_prepare_age.py dispatches it separately from the unchanged legacy tt_emb_source.v1 LP contract. No schema coercion, no old hash substitution and no inherited local4.

Actual component fleet unit: gold1 oth-ubuntu-51015-1792732044, Verilator5.050. Focused receipt checker confirms local2/local3 and catches wrong RTL hash, wrong master and an invented local4. Run heavy builds with ot-run; run_component.sh rebuilds only this39-bit mechanism.

The exact selected RTL and helper bytes are archived in selected_sources/ with SELECTED_SOURCE_ARCHIVE.json provenance. A canonical checkout with older RTL must fail the default checker. Use `check_receipts.py --selected-readset` only for the explicitly isolated source fixture, or `--source-root <selected-GEN-source-envelope>` for an actual matching source-complete envelope. The isolated fixture never qualifies canonical main and does not overwrite canonical source.
