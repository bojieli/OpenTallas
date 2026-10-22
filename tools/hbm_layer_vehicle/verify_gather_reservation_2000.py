"""Compiler guard checks. Abstract unit edges are not hardware timing receipts."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hbm_layer_vehicle.su_indexed_gather_2000 import programme_replay,encode_programme_row


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
    print('GATHER_RESERVATION_GUARDS_PASS: prior-owner overlap rejected; exact fixture ABI retained; early start and premature completion rejected')
if __name__=='__main__':main()
