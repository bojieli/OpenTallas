import copy
from types import SimpleNamespace as S

import pytest

from qwen_split.homes_metadata import prepare


def fixture():
    xs=[0,20,70,90]
    ins=[]
    for c,x in enumerate(xs):
        for n,y,w,h in [(f't_{c}_0',0,10,10),(f's_{c}_0',12,2,2),(f'h_{c}',20,2,2)]:
            ins.append(S(name=n,x=x,y=y,w=w,h=h,orient='R0'))
    ins.append(S(name='sp_port_tiles_0',x=50,y=5,w=5,h=10,orient='R0'))
    regions=[dict(name='tile_field_w',kind='tile_field',rect=[0,0,35,30]),
        dict(name='tile_field_e',kind='tile_field',rect=[70,0,105,30]),
        dict(name='hchan_s_w',kind='channel',rect=[0,10,35,12]),
        dict(name='spine',kind='hub',rect=[35,0,70,30]),
        dict(name='spine_vchan',kind='channel',rect=[52,0,54,30]),
        dict(name='slab_port_tiles_0',kind='slab',rect=[50,5,55,15])]
    regions += [dict(name=f'corr_{c}',kind='corridor',rect=[x+10,0,x+12,30]) for c,x in enumerate(xs)]
    m=dict(insts=ins,col_x=lambda c:xs[c],corridor_lanes=[(x+10,2) for x in xs],
        regions=regions,geo=dict(x_arr_w=0,x_spine=35,x_arr_e=70,x_eband=105))
    p={i.name:dict(x=i.x+(5 if c<2 else -5),y=i.y,w=i.w,h=i.h,o=i.orient)
        for c in range(4) for i in ins if i.name in (f't_{c}_0',f's_{c}_0',f'h_{c}')}
    p['sp_port_tiles_0']=dict(x=55,y=6,w=5,h=10,o='R0')
    return m,p


def test_actual_lanes_fields_slabs_and_reserved_channels_are_coherent():
    m,p=fixture()
    before=copy.deepcopy(m['regions'])
    updates,r=prepare(m,p,dict(clear=dict(x=41,y=0,w=2,h=30)))
    assert [updates['col_x'](c) for c in range(4)]==[5,25,65,85]
    assert updates['corridor_lanes']==[(15,2),(35,2),(75,2),(95,2)]
    by={r['name']:r for r in updates['regions']}
    assert by['tile_field_w']['rect']==[5,0,40,30]
    assert by['tile_field_e']['rect']==[65,0,100,30]
    assert by['corr_3']['rect']==[95,0,97,30]
    assert by['hchan_s_w']['rect']==[5,10,40,12]
    assert by['slab_port_tiles_0']['rect']==[55,6,60,16]
    assert by['spine']['rect']==[40,0,65,30]
    assert 'spine_vchan' not in by
    assert by['gfp_reserve_clear']['rect']==[41,0,43,30]
    assert r['removed_stale_regions']==['spine_vchan']
    assert updates['geo']['x_spine']==40 and updates['geo']['x_arr_e']==65
    assert m['regions']==before and m['col_x'](0)==0


@pytest.mark.parametrize('bad',['tile_y','station_x','head_y','orientation','nonrigid','lanes','missing_field','missing_slab'])
def test_unsupported_metadata_fails_before_mutation(bad):
    m,p=fixture()
    if bad=='tile_y':p['t_0_0']['y']+=1
    if bad=='station_x':p['s_0_0']['x']+=1
    if bad=='head_y':p['h_0']['y']+=1
    if bad=='orientation':p['t_0_0']['o']='MY'
    if bad=='nonrigid':
        for n in ('t_0_0','s_0_0','h_0'):p[n]['x']+=1
    if bad=='lanes':m['corridor_lanes'].pop()
    if bad=='missing_field':m['regions']=m['regions'][1:]
    if bad=='missing_slab':del p['sp_port_tiles_0']
    before=copy.deepcopy(m['regions'])
    with pytest.raises(ValueError):prepare(m,p,{})
    assert m['regions']==before and m['col_x'](0)==0
