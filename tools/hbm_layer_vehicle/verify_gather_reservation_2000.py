"""Compiler guard checks. Abstract unit edges are not hardware timing receipts."""
from pathlib import Path
import sys
import json
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hbm_layer_vehicle.su_indexed_gather_2000 import programme_replay,encode_programme_row,load_binding


def main():
    # A late first engine start cannot repair an already asserted programme
    # selector. No command/producer dates are constructed in this negative case.
    binding=dict(control_transport='ot_static_program_target',calendar_epoch=100,
                 ownership_release_tail=2,port_free=101)
    plans=[dict(status='native_gather_emitted') for _ in range(6)]
    try:programme_replay(plans,binding)
    except ValueError as error:
        assert 'epoch precedes actual native bank port release' in str(error)
    else:raise AssertionError('programme accepted overlapping prior bank owner')
    binding.update(port_free=100,parameters=dict(READ_SAMPLE=10,WRITE_COMMIT=5))
    plans[0]['native_gather']=dict(start=108,done=137)  # selected source publishes done at start+30
    try:programme_replay(plans,binding)
    except ValueError as error:assert 'selected source phase profile' in str(error)
    else:raise AssertionError('programme accepted premature source completion')
    # Use exact encoded fixture bytes for the accepted ABI and change only the
    # first start to the prohibited control-capture interval.
    row=int(Path(sys.argv[1]).read_text().split()[0],16)
    names=('index_word','score_base','score_limit','dest_word','dyn_mul')
    descriptor={name:(row>>(24*i))&0xffffff for i,name in enumerate(names)}
    descriptor['segment_bases']=[descriptor['score_base']]+[(row>>shift)&0xffffff for shift in (152,176,200)]
    start=(row>>120)&65535;release=(row>>136)&65535;identity=(row>>224)&65535
    assert encode_programme_row(descriptor,start=start,release=release,row_identity=identity)==row
    try:encode_programme_row(descriptor,start=1,release=release,row_identity=identity)
    except ValueError as error:assert 'programme start' in str(error)
    else:raise AssertionError('programme starts before native selector captures')
    # Exercise actual calendar/host frame encoders in an abstract unit epoch.
    # These ages deliberately carry no source/physical qualification.
    from hbm_layer_vehicle.layer_images import cp_frames
    from hbm_layer_vehicle.sm_images import cal_word,prog_row
    raw_rows=[int(v,16) for v in Path(sys.argv[1]).read_text().split()]
    calrow=prog_row(0,cal_word(rslot_v=255,wslot_v=255),187)
    free=0
    for target in range(96,100):_,_,free=cp_frames(target,[calrow],free,loops=1,launch=False)
    _,host_launch,_=cp_frames(180,raw_rows,free)
    epoch=host_launch+4
    unit=dict(control_transport='ot_static_program_target',calendar_epoch=epoch,
        ownership_release_tail=2,port_free=0,parameters=dict(READ_SAMPLE=10,WRITE_COMMIT=5),
        launch_to_calendar_zero=4,configuration_start=0,target_id=180,
        bank_calendars={q:dict(target_id=96+i,source_sha256='abstract_unit_source',
                              launch_to_bank_owner_edges=[2+i]*8)
                        for i,q in enumerate(('SW','SE','NW','NE'))})
    encoded=[]
    for value in raw_rows:
        d={name:(value>>(24*i))&0xffffff for i,name in enumerate(names)}
        d['segment_bases']=[d['score_base']]+[(value>>shift)&0xffffff for shift in (152,176,200)]
        start=epoch+((value>>120)&65535)
        encoded.append(dict(status='native_gather_emitted',native_gather=dict(descriptor=d,start=start,done=start+30)))
    unit['parameters']['SEGMENTED96']=1
    result=programme_replay(encoded,unit)
    assert [c['target'] for c in result['native_owner_calendars']]==list(range(96,100))
    assert all(c['programme_rows']==[f'{calrow:064x}'] for c in result['native_owner_calendars'])
    launches=[e for e in result['events'] if e['port'].endswith('__launch_v') and int(e['val'],16)]
    assert len(launches)==1
    assert result['programme_rows']==[f'{value:064x}' for value in raw_rows]
    if len(sys.argv)>2:
        calendar=json.loads(Path(sys.argv[2]).read_text())
        assert calendar['status']=='PARTIAL'
        calendar['source_binding']['status']='PASS'  # hardware-only proof is insufficient
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'partial.json';path.write_text(json.dumps(calendar))
            assert load_binding(path)['status']=='PARTIAL'
    print('GATHER_RESERVATION_GUARDS_PASS: prior-owner overlap rejected; exact fixture ABI and four real calendar target encodings retained; early start, premature completion and hardware-only promotion rejected')
if __name__=='__main__':main()
