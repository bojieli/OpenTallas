import copy
from collections import OrderedDict
from pathlib import Path
import pytest
import kvspc_model_projection as P
import kvspc_face_ports as F

DATA=Path(__file__).resolve().parents[5]/'results/hhp_model_projection_1102/guard_inputs'

def fixture():
    text=(DATA/'raw_extracted_qkd_kvs_pc.sv').read_text();pd=P.declarations(text)
    pc={k:('out' if pd[k[0]]['dir']=='output' else 'in') for k in P.bitkeys(pd)}
    con={k:('RAW_'+k[0],k[1] or 0) for k in pc}
    for i in (259,260):pc[('pc__land_er_259',i)]='stale_in';con[('pc__land_er_259',i)]=None
    pc[('ck',0)]='clk'
    m=dict(hc={'module':'qkd_kvs_pc','inst':'kvpc1'},ms=['kvpc1'],pre=None,mine={'u_kvpc1':'kvpc1'},pdecl=pd,pin_class=pc,part_conn=con,pins=OrderedDict(),rep={},lb={('u_kvpc1','pc__land_er',i):dict(nb=con[('pc__land_er',i)],base='pc__land_er',boundary=True) for i in (0,259,260)})
    g=P.verified_guard(DATA/'event.json',DATA/'rtl_overlay',DATA/P.BASE_FILE,('kvpc1','kvpc2','kvpc3'))
    return m,text,g


def test_projection_live_raw_bits_and_untouched_other_ports(monkeypatch):
    m,text,g=fixture();old=copy.deepcopy(m);calls=[];wrapper=F.wrapper
    def once(*a,**kw):calls.append(a[1:]);return wrapper(*a,**kw)
    monkeypatch.setattr(F,'wrapper',once)
    monkeypatch.setattr(F,'apply_kit',lambda *a,**k:(_ for _ in ()).throw(AssertionError('full transform forbidden')))
    p,sv=P.project_model(m,text,g)
    assert m==old and len(calls)==1 and p['wrapper_only_split_model']
    assert len(p['pdecl'])==25 and len(P.bitkeys(p['pdecl']))==4129
    with pytest.raises(ValueError):P.project_model(p,sv,g)
    assert set(p['part_conn'])==set(p['pin_class'])==P.bitkeys(p['pdecl'])
    assert p['pdecl']['pc__land_er_259']['lo']==259
    for i in (259,260):
        assert p['part_conn'][('pc__land_er_259',i)]==old['part_conn'][('pc__land_er',i)]
        assert p['pin_class'][('pc__land_er_259',i)]==old['pin_class'][('pc__land_er',i)]
    assert p['part_conn'][('pc__land_er',0)]==old['part_conn'][('pc__land_er',0)]
    for k,v in old['part_conn'].items():
        if k[0] not in P.BANKS+('pc__land_er','pc__land_er_259'):assert p['part_conn'][k]==v
    for b,d in old['pdecl'].items():
        if b not in P.BANKS+('pc__land_er','pc__land_er_259'):assert p['pdecl'][b]==d
    assert P.declarations(P.functional_declaration(p))==P.declarations(sv)
    assert 'leaf_src' not in p and not any(b.startswith('ft_ck_') for b in p['pdecl'])


@pytest.mark.parametrize('kind',['module','owner','owner_members','width','direction','missing_bit','stale_alias','substituted_live','common_clock','ft','head_owner','bank_width','bank_direction','class_direction'])
def test_bad_context_rejected(kind):
    m,text,g=fixture()
    if kind=='class_direction':m['pin_class'][('pc__cfg_stack',0)]='out'
    elif kind=='head_owner':m['hc']['inst']='kvpc0'
    elif kind=='bank_width':m['pdecl']['pc__front_hbm_data']['hi']=4
    elif kind=='bank_direction':m['pdecl']['pc__return_hbm_data']['dir']='output'
    elif kind=='module':m['hc']['module']='qkd_kvs_pc_h_head_p'
    elif kind=='owner':m['hc']['inst']='head0'
    elif kind=='owner_members':m['mine']={'u_head0':'head0'}
    elif kind=='width':m['pdecl']['pc__land_er']['hi']=259
    elif kind=='direction':m['pdecl']['pc__land_er']['dir']='output'
    elif kind=='missing_bit':del m['part_conn'][('pc__land_er',260)]
    elif kind=='stale_alias':m['part_conn'][('pc__land_er_259',259)]=('STALE_ALIAS',259)
    elif kind=='substituted_live':m['part_conn'][('pc__land_er',259)]=('STALE_ALIAS',259)
    elif kind=='common_clock':text=text.replace('.hck(ck[0])','.hck(hck[0])')
    elif kind=='ft':m['pdecl']['ft_ck_i_0']=dict(dir='input',hi=None,lo=None,gaps=[])
    with pytest.raises(ValueError):P.project_model(m,text,g)


def test_guard_required_and_default_off():
    m,text,g=fixture()
    assert P.prepare_split(None,[m])['status']=='DISABLED'
    with pytest.raises(ValueError):P.project_model(m,text,None)
    forged=P.SourceGuard(g.owners,g.event_sha256,g.source_sha256,g.original_header_sha256,object())
    with pytest.raises(ValueError):P.project_model(m,text,forged)


def test_wrong_event_and_source_and_owner_fail_closed(tmp_path):
    m,text,g=fixture();bad=tmp_path/'event.json';bad.write_text((DATA/'event.json').read_text().replace('"qualified": false','"qualified": true'))
    with pytest.raises(ValueError):P.verified_guard(bad,DATA/'rtl_overlay',DATA/P.BASE_FILE,('kvpc1',))
    with pytest.raises(ValueError):P.verified_guard(DATA/'event.json',tmp_path,DATA/P.BASE_FILE,('kvpc1',))
    with pytest.raises(ValueError):P.verified_guard(DATA/'event.json',DATA/'rtl_overlay',DATA/P.BASE_FILE,('head0',))


def test_other_nonzero_indices_are_preserved():
    m,text,g=fixture();b='pc__cfg_stack';m['pdecl'][b].update(hi=10,lo=9)
    for field in ('part_conn','pin_class'):
        for a,z in [(0,9),(1,10)]:m[field][(b,z)]=m[field].pop((b,a))
    text=text.replace('[1:0] pc__cfg_stack','[10:9] pc__cfg_stack').replace('pc__cfg_stack[1:0]','pc__cfg_stack[10:9]')
    p,_=P.project_model(m,text,g)
    assert p['pdecl'][b]==m['pdecl'][b]
    assert p['part_conn'][(b,9)]==m['part_conn'][(b,9)] and p['part_conn'][(b,10)]==m['part_conn'][(b,10)]
