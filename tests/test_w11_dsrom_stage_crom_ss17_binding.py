import w11_dsrom_stage_crom_ss17_binding as B

def test_corrected_route_pin_preserves_compiler_proof_and_scope():
    r=B.build()
    assert len(r['historical_diagnostic_programs'])==4
    assert all(not p['runnable'] and p['published_program_sha256'] is None for p in r['historical_diagnostic_programs'])
    for m in r['current_models']:
        assert m['SS_route_basis']['stages_each_direction']==17
        assert m['value_validity_catalog_and_geometry_byte_fields_identical']
        assert m['actual_absolute_PC_release'] is None and not m['actual_service_bound']
    assert not r['historical_11_cycle_timing_credit']
    assert not r['hardware_admission'] and not r['image_admission']
    assert r['L1_invalid_local_slots']==[12528,33008]
