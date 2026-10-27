import copy
import pytest
import qxpq_go_boundary as G


def words():
    x=[0x124]*128
    x[10]|=2; x[96]|=1
    return x


def test_legacy_byte_identical_and_gb_only_moves_go():
    x=words();same,r=G.lower_lc_words(x,[],enabled=False);assert same==x
    y,r=G.lower_lc_words(x,[60],enabled=True)
    assert [i for i,v in enumerate(y) if v&1]==[95]
    assert all((a&~1)==(b&~1) for a,b in zip(x,y))
    # Golden composition = the actual one-edge GB capture. Unadvanced mutant must differ.
    assert [0]+[v&1 for v in y[:-1]]==[v&1 for v in x]
    assert [0]+[v&1 for v in x[:-1]]!=[v&1 for v in x]


@pytest.mark.parametrize('case', ['missing','late','adjacent','edge0'])
def test_unsafe_calendar_refused(case):
    x=words();legal=[60]
    if case=='missing':legal=[]
    if case=='late':legal=[96]
    if case=='adjacent':x[97]|=1;legal=[60,60]
    if case=='edge0':x[0]|=1;legal=[0,60]
    with pytest.raises(ValueError):G.lower_lc_words(x,legal,enabled=True)


FRAME='''module frame(input clk);\nwire a,b,c,d;\not_v41_rom_elem_q_qxpq_w10 #(.NB(2), .PP(1), .PQ(1), .QX(10), .RSTP(1), .INSTANCE({INSTANCE,"_e0"})) u_e0 (.clk(clk), .go(a), .go_tag({b,c}), .xs_sv({d,c}));\nendmodule\n'''

def test_unused_input_elision_preserves_upstream_and_other_consumers():
    out,rec=G.lower_frame_text(FRAME)
    assert '.xs_sv' not in out and 'wire a,b,c,d;' in out
    assert '.go_tag({b,c})' in out and rec['upstream_wires_preserved']


def test_frame_preserves_other_connections_and_parameters():
    src=FRAME.replace('.go_tag({b,c})','.go_tag({b,b})')
    out,r=G.lower_frame_text(src)
    assert G.GB+' #' in out and '.GO_BOUNDARY(1)'in out and '.CGR(8)'in out
    assert '.RSTP(1)'in out and '.go(a)'in out and '.go_tag({b,b})'in out
    assert 'xs_sv'not in out and 'wire a,b,c,d;'in out
    assert r['instances']==['u_e0'] and r['qualified']is False


def test_nb_and_conflicting_profile_refused():
    with pytest.raises(ValueError,match='NB2'):G.lower_frame_text(FRAME.replace('.NB(2)','.NB(1)'))
    with pytest.raises(ValueError,match='CGR'):G.lower_frame_text(FRAME.replace('.NB(2)','.NB(2),.CGR(0)'))


def test_plan_selection_is_explicit_and_signed_view_cannot_be_reused():
    hc=dict(module=G.LEGACY,lef='old.lef',pins_file='old.json')
    raw=dict(partition_types={'a':dict(hard_cores=[hc]),'b':dict(hard_cores=[copy.deepcopy(hc)])})
    new,r=G.lower_plan(raw,['a']);assert new['partition_types']['a']['hard_cores'][0]['module']==G.GB
    assert new['partition_types']['b']==raw['partition_types']['b'] and raw['partition_types']['a']['hard_cores'][0]['module']==G.LEGACY
    with pytest.raises(ValueError):G.lower_plan(raw,[])
    raw['partition_types']['a']['hard_cores'][0]['lib']='old_signed.lib'
    with pytest.raises(ValueError,match='signed'):G.lower_plan(raw,['a'])


def test_bare_actual_band_requires_explicit_selected_profile():
    src=FRAME.replace('#(.NB(2), .PP(1), .PQ(1), .QX(10), .RSTP(1), .INSTANCE({INSTANCE,"_e0"})) ', '')
    with pytest.raises(ValueError,match='hard_params'):G.lower_frame_text(src)
    out,r=G.lower_frame_text(src,hard_params=dict(NB='2',PP='1',PQ='1',QX='10',RSTP='1',QM='5'))
    assert '.QM(5)' in out and '.RSTP(1)' in out and '.NB(2)' in out
    assert '.GO_BOUNDARY(1)' in out and '.CGR(8)' in out
    assert '.xs_sv' not in out and r['instances']==['u_e0']
    with pytest.raises(ValueError,match='NB2'):G.lower_frame_text(src,hard_params=dict(NB='1'))


@pytest.mark.parametrize('field', ['libTT','libFF','lib_tt','lib_ff'])
def test_no_corner_library_carryover(field):
    raw=dict(partition_types={'a':dict(hard_cores=[dict(module=G.LEGACY, **{field:'old.lib'})])})
    with pytest.raises(ValueError,match='signed'):G.lower_plan(raw,['a'])
