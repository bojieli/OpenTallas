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


def test_sequential_lockstep_and_swapped_provider_mutant(tmp_path):
    import shutil, subprocess
    if not shutil.which('iverilog') or not shutil.which('vvp'):
        pytest.skip('iverilog is required for the sequential wrapper control')
    top='''module die(input rst_n,input [7:0] data,input pst_a,input pst_b,output [7:0] y);
      assign y = (data & {8{pst_a}}) ^ ((data << 1) & {8{pst_b}}); endmodule'''
    provider='''module ot_die_start_stages(input rst_raw_n,input t_st_root__clk,output pst_a,output pst_b);
      reg [3:0] q=0;
      always @(posedge t_st_root__clk) if(!rst_raw_n) q<=0; else q<={q[2:0],1'b1};
      assign pst_a=q[1]; assign pst_b=q[3]; endmodule'''
    doc=copy.deepcopy(DOC);doc['die_outputs']=[dict(net='pst_a'),dict(net='pst_b')]
    joined,rec=P.integrate(top,'die',provider,doc,'rst_n')
    tb='''module tb;
      reg clk=0,rst_n=0; reg [7:0] data=1;
      wire a,b; wire [7:0] got,want;
      always #5 clk=~clk;
      die u(.rst_n(rst_n),.data(data),.y(got),.t_st_root__clk(clk));
      ot_die_start_stages refp(.rst_raw_n(rst_n),.t_st_root__clk(clk),.pst_a(a),.pst_b(b));
      die__without_start_provider refd(.rst_n(rst_n),.data(data),.pst_a(a),.pst_b(b),.y(want));
      integer n;
      initial begin
        repeat(2) @(negedge clk); rst_n=1;
        for(n=0;n<24;n=n+1) begin @(negedge clk); if(got!==want) $fatal(1,"START_WIRING_DIFF"); data=data+3; end
        $display("START_WIRING_EQ 24"); $finish;
      end
    endmodule'''
    def run(text,label):
        src=tmp_path/(label+'.sv');exe=tmp_path/(label+'.vvp')
        src.write_text(text+'\n'+provider+'\n'+tb)
        subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),str(src)],check=True,capture_output=True,text=True)
        return subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
    positive=run(joined,'positive')
    assert positive.returncode==0 and 'START_WIRING_EQ 24' in positive.stdout
    lines=joined.splitlines()
    lines=[l.replace('.pst_a(pst_a)', '.pst_a(pst_b)').replace('.pst_b(pst_b)', '.pst_b(pst_a)')
           if 'ot_die_start_stages u_start_provider' in l else l for l in lines]
    mutant=run('\n'.join(lines),'mutant')
    assert mutant.returncode!=0 and 'START_WIRING_DIFF' in mutant.stdout
