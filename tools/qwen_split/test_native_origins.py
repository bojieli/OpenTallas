import copy
from types import SimpleNamespace
import pytest
from native_origins import apply


def fixture():
    i=SimpleNamespace(name='phy',master='real_phy',orient='MX',x=0.0,y=14.108,w=777.6,h=777.6)
    p=dict(schema='opentallas.native_origin_plan.v1',source='native place',entries=[dict(
        instance='phy',master='real_phy',orient='MX',before=[0,14.108,777.6,777.6],after_xy=[.216,14.12],
        master_lef_sha256='a'*64,track_snap_source_sha256='b'*64)])
    return i,p


def test_native_phy_reservation_precedes_relay_placement():
    i,p=fixture();r=apply([i],p)
    assert i.x==.216 and i.x+i.w==777.816
    assert r['moved'][0]['before']==[0,14.108,777.6,777.6]
    assert i.y==14.12


@pytest.mark.parametrize('field,value',[('master','wrong'),('orient','R0'),('before',[0,14.108,777.5,777.6]),('after_xy',[-1,0]),('master_lef_sha256','')])
def test_stale_or_unproved_native_plan_refused_without_mutation(field,value):
    i,p=fixture();p['entries'][0][field]=value
    with pytest.raises(ValueError):apply([i],p)
    assert (i.x,i.y)==(0,14.108)


def test_whole_plan_validated_before_mutating():
    i,p=fixture();other=copy.deepcopy(p['entries'][0]);other['instance']='missing';p['entries'].append(other)
    with pytest.raises(ValueError):apply([i],p)
    assert i.x==0


def test_native_origins_survive_later_source_model_reinstantiation():
    i,p=fixture();source={'phy':dict(x=i.x,y=i.y)}
    apply([i],p,source_positions=source)
    # apply_dv later rebuilds retained instances from DI; both representations agree.
    retained=SimpleNamespace(name='phy',x=source['phy']['x'],y=source['phy']['y'])
    assert (retained.x,retained.y)==(.216,14.12)
