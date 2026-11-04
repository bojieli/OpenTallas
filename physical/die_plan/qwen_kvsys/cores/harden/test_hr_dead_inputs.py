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


def test_stopped_post_leg_stays_pending_and_declares_nothing(tmp_path):
    pre = dict(modules=dict(m=dict(ports=dict(dead=dict(direction='input',bits=[2])),cells={})))
    fp=tmp_path/'fp';fp.mkdir();kit=tmp_path/'kit';kit.mkdir()
    (fp/'pre.json').write_text(json.dumps(pre))
    (fp/'eq_rc.txt').write_text('post stopped see post_leg_note.txt mut rc=1 emitted_v rc=0')
    assert H.emit(fp,'m',kit,['dead[0]']) == []
    assert json.loads((kit/'hr_dead_inputs_proof.json').read_text())['verdict']=='PENDING'
    assert not (kit/'dead_inputs.json').exists()
    import pytest
    for bad in ('post stopped mut pending emitted_v pending','post stopped mut rc=0 emitted_v rc=0',
                'post stopped mut rc=1 emitted_v rc=1','post rc=1 mut rc=1 emitted_v rc=0'):
        (fp/'eq_rc.txt').write_text(bad)
        with pytest.raises(ValueError): H.emit(fp,'m',kit,['dead[0]'])


def test_exact_declared_indices_for_offset_and_ascending_ports():
    pre = dict(modules=dict(m=dict(ports=dict(
        off=dict(direction='input', bits=[2,3], offset=5),
        asc=dict(direction='input', bits=[4,5], offset=8, upto=1)),
        cells=dict(c=dict(connections=dict(A=[3,5]))))))
    assert H.exact_dead_bits(pre, 'm', ['off[0]','off[5]','off[6]',
        'asc[8]','asc[9]','asc[10]']) == ['asc[9]', 'off[5]']


def named_fp(tmp_path, rc='post stopped see post_leg_note.txt mut rc=1 emitted_v rc=0'):
    import hr_named_leg as N
    pre = dict(modules=dict(m=dict(ports=dict(dead=dict(direction='input',bits=[2])),cells={})))
    fp=tmp_path/'fp';fp.mkdir();kit=tmp_path/'kit';kit.mkdir()
    (fp/'pre.json').write_text(json.dumps(pre));(fp/'post.json').write_text('{"p":1}');(fp/'mut.json').write_text('{"m":1}')
    (fp/'eq_rc.txt').write_text(rc)
    def ys(name, gate):
        y=tmp_path/name
        y.write_text(f'read_json {fp}/pre.json\nread_json {fp}/{gate}\n'+'\n'.join(N.FORM)+'\n')
        return y
    log=tmp_path/'post.log';log.write_text('i/o = 3/ 1 lat =24 and = 146\ni/o = 3/ 1 lat = 0 and = 0\nUNSATISFIABLE\n')
    mlog=tmp_path/'mut.log';mlog.write_text('i/o = 3/ 1 lat =24 and = 146\ni/o = 3/ 1 lat = 3 and = 2\nasserted in frame 4\nNetworks are not equivalent.\n')
    return N,fp,kit,ys('p.ys','post.json'),log,ys('m.ys','mut.json'),mlog


def write_named(N,fp,y,log,my,mlog,leg='post'):
    (fp/'named_legs.json').write_text(json.dumps(dict(schema=N.SCHEMA,module='m',legs={leg:N.build(fp,'m',y,log,my,mlog)})))


def test_named_post_leg_returns_under_its_own_name(tmp_path):
    N,fp,kit,y,log,my,mlog=named_fp(tmp_path)
    rc=(fp/'eq_rc.txt').read_text()
    assert H.proof_state(fp,'m')=='pending'
    write_named(N,fp,y,log,my,mlog)
    assert H.proof_state(fp,'m')=='named'
    assert H.emit(fp,'m',kit,['dead[0]'])==['dead[0]']
    r=json.loads((kit/'hr_dead_inputs_proof.json').read_text())
    leg=r['named_legs']['post']
    assert leg['initial_state']=='zero' and leg['srams']=='ports' and leg['mutant']['frame']==4
    assert 'state outside zero init is not proved' in r['method'] and 'scorr' in r['method']
    assert 'post rc=0' not in ' '.join(r['eq_rc']) and (fp/'eq_rc.txt').read_text()==rc


def test_named_leg_refuses_other_netlist_failed_leg_and_uncaught_mutant(tmp_path):
    import pytest
    N,fp,kit,y,log,my,mlog=named_fp(tmp_path)
    write_named(N,fp,y,log,my,mlog)
    # a failed yosys leg stays failed
    for bad in ('post rc=1 mut rc=1 emitted_v rc=0','post stopped mut rc=0 emitted_v rc=0','post stopped mut rc=1 emitted_v rc=1'):
        (fp/'eq_rc.txt').write_text(bad)
        assert H.proof_state(fp,'m')=='fail'
        with pytest.raises(ValueError): H.emit(fp,'m',kit,['dead[0]'])
    (fp/'eq_rc.txt').write_text('post stopped mut rc=1 emitted_v rc=0')
    # the netlist changed after the leg ran
    (fp/'post.json').write_text('{"p":2}')
    with pytest.raises(ValueError): H.proof_state(fp,'m')
    (fp/'post.json').write_text('{"p":1}')
    # mutant not caught, or a leg that did not finish
    with pytest.raises(ValueError): N.build(fp,'m',y,log,my,log)
    with pytest.raises(ValueError): N.build(fp,'m',y,mlog,my,mlog)
    # another form: no zero-init aiger
    y.write_text(y.read_text().replace('write_aiger -zinit','write_aiger'))
    with pytest.raises(ValueError): N.build(fp,'m',y,log,my,mlog)


def test_emitted_and_post_named_cover_a_stopped_proof(tmp_path):
    N,fp,kit,y,log,my,mlog=named_fp(tmp_path,'post stopped mut pending emitted_v pending')
    write_named(N,fp,y,log,my,mlog)
    assert H.proof_state(fp,'m')=='pending'     # emitted_v, the kit RTL itself, is still open
    doc=json.loads((fp/'named_legs.json').read_text())
    doc['legs']['emitted_v']=doc['legs']['post']
    (fp/'named_legs.json').write_text(json.dumps(doc))
    assert H.proof_state(fp,'m')=='named'
