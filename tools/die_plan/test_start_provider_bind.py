import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import start_provider_bind as P

TOP='module die(input rst_n,input data,input pst_r0,output y); assign y=data & pst_r0; endmodule\n'
PROVIDER='module ot_die_start_stages(input rst_raw_n,input t_st_root__clk,output pst_r0); assign pst_r0=rst_raw_n; endmodule\n'
DOC=dict(schema='ot_start_stages/1',stages=[dict(clock_port='t_st_root__clk')],die_inputs=[],
         die_outputs=[dict(net='pst_r0')],counts=dict(flops=8))


def test_integrated_public_top_has_real_provider_and_no_pst_inputs():
    text,rec=P.integrate(TOP,'die',PROVIDER,DOC,'rst_n')
    public=P._module(text,'die')
    assert set(public.ports)=={'rst_n','data','y','t_st_root__clk'}
    assert 'ot_die_start_stages u_start_provider' in text
    assert '.pst_r0(pst_r0)' in text and 'wire pst_r0;' in text
    assert rec['logical_cycles_added']==0 and rec['driven_start_inputs']==['pst_r0']


@pytest.mark.parametrize('mutant', ['missing_output','wrong_direction','clock_collision','reset_missing'])
def test_provider_join_rejects_incomplete_or_ambiguous_source(mutant):
    top,provider,doc=TOP,PROVIDER,copy.deepcopy(DOC)
    if mutant=='missing_output':doc['die_outputs']=[]
    if mutant=='wrong_direction':provider=provider.replace('output pst_r0','input pst_r0')
    if mutant=='clock_collision':top=top.replace('input data','input t_st_root__clk,input data')
    if mutant=='reset_missing':top=top.replace('input rst_n,','')
    with pytest.raises(P.ProviderError):P.integrate(top,'die',provider,doc,'rst_n')
