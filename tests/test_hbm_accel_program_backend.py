"""Concrete native backend input and pin-contract checks; no model inference."""
from pathlib import Path
import pytest
from tools.hbm_accel_program_backend import validate_native,emit_top,VerilatorPins


def test_native_words_and_entries_refuse_request_graph_or_narrowing():
    images={(d,s):[0,1] for d in range(2) for s in range(2)}
    validate_native(images,{'layer':1})
    for bad in (b'program.bin',{},dict(images,wrong=[0])):
        with pytest.raises(ValueError):validate_native(bad)
    bad=dict(images);bad[0,0]=[1<<64]
    with pytest.raises(ValueError,match='OTG-1'):validate_native(bad)
    with pytest.raises(ValueError,match='entries'):validate_native(images,{'layer':2})


def test_simulation_loader_binds_each_original_die_and_probes_actual_units(tmp_path):
    top=tmp_path/'top.sv';emit_top(top,2097152);source=top.read_text()
    assert 'ot_ds_hbm_source_entry20 #(.ENABLE(1),.MEM_WORDS(2097152))' in source
    assert 'defparam' not in source
    for die in range(2):
        for part in range(2):
            assert f'%s_d{die}_p{part}.hex' in source
            assert f'g_die[{die}].u_mem.u_ms.g_on.g_s[{part}].u_part.g_on.u_model.mem' in source
        for sm in range(2):
            assert f'g_die[{die}].g_sm[{sm}].u_sm.g_on.can_issue' in source
    assert '#1;' in source  # load only after original time-zero array initialisation


def test_cpl109_snapshot_decodes_real_flat_bus_without_fabricating_fields():
    pins=VerilatorPins.__new__(VerilatorPins)
    a=(0x12345678<<77)|(9<<73)|(17<<41)|(2<<37)|(1048575<<17)|128799
    b=a^(1<<73)
    raw=a|(b<<109)
    pins._rpc=lambda request:[format(v,'x') for v in (833,1,1,0,3,3,raw,0,0,0,0)]
    s=pins.snapshot()
    assert s['time_ps']==833 and s['cycle']==1
    assert s['dies'][0]['cpl_data']==a and s['dies'][1]['cpl_data']==b


def test_native_loader_refuses_bad_words_before_mutating_real_pins():
    pins=VerilatorPins.__new__(VerilatorPins)
    pins._rpc=lambda request:pytest.fail('mutated pins before validation')
    with pytest.raises(ValueError):pins.load_native({(0,0):b'program.bin'})
