import json
import hr_dead_inputs as H


def test_dead_input_contract_rejects_feedthrough_and_live_alias(tmp_path):
    pre = dict(modules=dict(m=dict(ports=dict(dead=dict(direction='input',bits=[2]),
        feed=dict(direction='input',bits=[3]), live=dict(direction='input',bits=[4]),
        out=dict(direction='output',bits=[3])), cells=dict(c=dict(connections=dict(A=[4]))))))
    fp=tmp_path/'fp';fp.mkdir();kit=tmp_path/'kit';kit.mkdir()
    (fp/'pre.json').write_text(json.dumps(pre));(fp/'eq_rc.txt').write_text('post rc=0 mut rc=1 emitted_v rc=0')
    assert H.emit(fp,'m',kit,['dead[0]','feed[0]','live[0]']) == ['dead[0]']
    doc=json.loads((kit/'dead_inputs.json').read_text())
    assert doc['bits']==['dead[0]'] and doc['proof']['verdict']=='PASS'


def test_no_dead_contract_without_complete_proof(tmp_path):
    (tmp_path/'pre.json').write_text('{}');(tmp_path/'eq_rc.txt').write_text('post rc=0 mut rc=1')
    import pytest
    with pytest.raises(ValueError): H.emit(tmp_path,'m',tmp_path,['dead[0]'])


def test_exact_declared_indices_for_offset_and_ascending_ports():
    pre = dict(modules=dict(m=dict(ports=dict(
        off=dict(direction='input', bits=[2,3], offset=5),
        asc=dict(direction='input', bits=[4,5], offset=8, upto=1)),
        cells=dict(c=dict(connections=dict(A=[3,5]))))))
    assert H.exact_dead_bits(pre, 'm', ['off[0]','off[5]','off[6]',
        'asc[8]','asc[9]','asc[10]']) == ['asc[9]', 'off[5]']
