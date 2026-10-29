import copy
from head_start_raw_private import prepare_plan,patch_rtl

TEXT='module x(input wire clk,d,output wire a); wire r; ot_dp_rrelay u_rrl_0 (.clk(clk),.d(d),.q(r)); assign a=r; endmodule'
ROW=dict(port='a',instance='u_rrl_0',net='r',xy_um=[4.,5.])
def test_private_copy_replaces_alias_preserves_native_d_and_q():
    t=dict(cells=10,reset_start_raw_exports=[ROW],clock=dict(landing_contract=dict(pins=[dict(name='a')])))
    p,r=prepare_plan(dict(partition_types={'X':t}),{'X'});t=p['partition_types']['X'];text,rr=patch_rtl(TEXT,t)
    assert t['cells']==11 and r['X']['added_cycles']==0 and rr['added_flops']==1
    assert '.d(d),.q(r)' in text and '.export_q(a)' in text and 'assign a=r' not in text
    assert 'ot_dp_head_raw_export_pair u_rrl_0' in text
    assert t['clock']['landing_contract']['pins'][0]['source_net']=='a'

def test_existing_ports_stay_untouched_and_wrong_sources_fail():
    import pytest
    t=dict(cells=10,reset_start_raw_exports=[dict(ROW,existing_port='a')])
    p,r=prepare_plan(dict(partition_types={'X':t}),{'X'});out,rr=patch_rtl(TEXT,p['partition_types']['X'])
    assert out==TEXT and rr['added_flops']==0 and r['X']['existing_outputs_reused']==1
    assert patch_rtl(TEXT,dict(reset_start_raw_exports=[ROW]))[0]==TEXT
    with pytest.raises(ValueError,match='source'):patch_rtl(TEXT.replace('ot_dp_rrelay','ot_dp_rgate'),dict(private_reset_start_exports=True,reset_start_raw_exports=[ROW]))
    with pytest.raises(ValueError,match='Q does not match'):patch_rtl(TEXT,dict(private_reset_start_exports=True,reset_start_raw_exports=[dict(ROW,net='wrong')]))
