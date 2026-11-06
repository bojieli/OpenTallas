import copy
import pytest
import reset_tree as RT


def fixture():
    rows=[dict(name='u_rrl_1_b',q='rst_boot_t1',d='rst_rl_0',role='bootstrap_transport',
               kind='tap',depth=2,xy=[5,5]),
          dict(name='u_rrl_2_b',q='rst_boot_t2',d='rst_rl_0',role='bootstrap_transport',
               kind='tap',depth=2,xy=[8,8])]
    text='''module actual(input clk, input rst_rl_0, output visible);
wire rst_boot_t1;
wire rst_boot_t2;
ot_dp_rrelay u_rrl_1_b (.clk(clk),.d(rst_rl_0),.q(rst_boot_t1));
ot_dp_rrelay u_rrl_2_b (.clk(clk),.d(rst_rl_0),.q(rst_boot_t2));
assign visible=rst_boot_t2;
endmodule
'''
    return rows,text


def test_only_source_dead_boot_leaf_is_omitted():
    rel,text=fixture();a=RT.unused_bootstrap_placements(rel,text,'actual')
    assert a['omitted']==['u_rrl_1_b']
    assert [r['occurrences'] for r in a['leaves']]==[2,3]
    assert len(a['wrapper_sha256'])==64


@pytest.mark.parametrize('fault',('consumer','alias','export','ambiguous_cell','different_input','not_boot'))
def test_any_live_use_or_ambiguity_keeps_placement(fault):
    rel,text=fixture()
    if fault=='consumer':text=text.replace('endmodule','assign extra=rst_boot_t1; endmodule')
    if fault=='alias':text=text.replace('endmodule','wire other; assign other=rst_boot_t1; endmodule')
    if fault=='export':text=text.replace('output visible','output visible,output rst_boot_t1')
    if fault=='ambiguous_cell':text=text.replace('endmodule','ot_dp_rrelay u_rrl_1_b (.clk(clk),.d(rst_rl_0),.q(other)); endmodule')
    if fault=='different_input':text=text.replace('.d(rst_rl_0),.q(rst_boot_t1)','.d(other),.q(rst_boot_t1)')
    if fault=='not_boot':rel[0]['role']='raw'
    assert not RT.unused_bootstrap_placements(rel,text,'actual')['omitted']


def test_ambiguous_or_missing_final_wrapper_refused():
    rows,text=fixture()
    for source in ('module other; endmodule',text+text):
        with pytest.raises(RT.ResetError):RT.unused_bootstrap_placements(rows,source,'actual')


def test_omission_does_not_relax_live_missing_or_hop_checks(monkeypatch):
    rows,_=fixture()
    monkeypatch.setattr(RT,'start_relays',lambda t:copy.deepcopy(rows))
    monkeypatch.setattr(RT,'out_relays',lambda t:{})
    t=dict(entry='relayed',root=[0,0],start=True,start_in=[0,0],reach_um=405,
           n_tree=0,n_pad=2,depth=2,max_hop_um=10,relays=[])
    out=RT.tcl_text(t,unused_bootstrap=['u_rrl_1_b'])
    assert 'rtr_place rst_boot_t1 ' not in out
    assert 'rtr_place rst_boot_t2 ' in out
    assert 'lappend rtr_miss $pat' in out
    assert '$rtr_hbad || [llength $rtr_miss]' in out
    with pytest.raises(RT.ResetError):RT.tcl_text(t,unused_bootstrap=['u_not_boot'])
