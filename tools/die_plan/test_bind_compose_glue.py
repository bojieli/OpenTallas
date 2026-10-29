"""Actual primitive reset/clock behavior survives opt-in core composition."""
import copy,shutil,subprocess,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bind_elab as E
from bind_compose import compose,CompositionError

class Rules:
    def part_of(self,path):return 'p'

def fixture():
    f=E.Flat();f.new(12)
    f.top_ports={'cp':('input',[1]),'cn':('input',[7]),'rst':('input',[2]),'d':('input',[3,4]),'q':('output',[8,9])}
    f.cells=[E.Cell('top.a','$adff',{},dict(CLK=[1],ARST=[2],D=[3,4],Q=[5,6]),dict(CLK='input',ARST='input',D='input',Q='output'),'glue',ytype='$adff',yparams=dict(WIDTH='10',CLK_POLARITY='1',ARST_POLARITY='0',ARST_VALUE='10')),
             E.Cell('top.b','$dff',{},dict(CLK=[7],D=[5,6],Q=[8,9]),dict(CLK='input',D='input',Q='output'),'glue',ytype='$dff',yparams=dict(WIDTH='10',CLK_POLARITY='0'))]
    def port(direction,path,pin,n):return dict(dir=direction,bits=[[dict(member='top.'+path,port=pin,bit=i)] for i in range(n)])
    s=dict(allow_glue=True,cores=[dict(inst='top.cut',module='actual_cut',members=['top.a','top.b'],ports=dict(cp=port('input','a','CLK',1),cn=port('input','b','CLK',1),rst=port('input','a','ARST',1),d=port('input','a','D',2),q=port('output','b','Q',2)))])
    return f,s

def test_glue_requires_explicit_boolean_optin():
    f,s=fixture();s.pop('allow_glue')
    with pytest.raises(CompositionError,match='allow_glue'):compose(f,Rules(),s,E.Cell)
    f,s=fixture();s['allow_glue']='true'
    with pytest.raises(CompositionError,match='boolean'):compose(f,Rules(),s,E.Cell)

def test_glue_unsupported_primitive_fails_closed():
    f,s=fixture();f.cells[0].ytype='$memrd'
    with pytest.raises(CompositionError,match='not supported'):compose(f,Rules(),s,E.Cell)
    assert len(f.cells)==2

def test_distinct_clocks_cannot_be_aliased():
    f,s=fixture();s['cores'][0]['ports']['cp']['bits'][0].append(dict(member='top.b',port='CLK',bit=0))
    with pytest.raises(CompositionError,match='net or direction mismatch'):compose(f,Rules(),s,E.Cell)

def test_real_ff_lockstep_and_reset_clock_mutants(tmp_path):
    if not shutil.which('iverilog') or not shutil.which('vvp'):pytest.skip('iverilog unavailable')
    f,s=fixture();sources,r=compose(f,Rules(),s,E.Cell)
    assert r['terminal_equality'] and len(f.cells)==1
    actual=sources[0][1]
    bench='''module tb;
reg cp=0,cn=0,rst=0;reg[1:0]d=0;always #5 cp=~cp;always #7 cn=~cn;
reg[1:0]a,b;wire[1:0]q;integer i;
actual_cut dut(.cp(cp),.cn(cn),.rst(rst),.d(d),.q(q));
always @(posedge cp or negedge rst)if(!rst)a<=2'b10;else a<=d;
always @(negedge cn)b<=a;
always @(cp or cn or rst)begin #1;if(q!==b)$fatal(1,"clock/reset lockstep mismatch");end
initial begin
 #3;rst=1;#2;rst=0;#3;rst=1;
 for(i=0;i<128;i=i+1)begin #9;d=$random;if(i==57)rst=0;if(i==60)rst=1;end
 $display("COMPOSE_GLUE PASS 128 stimuli, separate positive/negative clocks, warm reset");$finish;
end
endmodule
'''
    variants=[('exact',actual,True),('wrong_clock',actual.replace('always @(posedge','always @(negedge',1),False),('wrong_reset',actual.replace('if (!','if (',1),False)]
    for name,rtl,positive in variants:
        path=tmp_path/(name+'.sv');path.write_text(rtl+bench);exe=tmp_path/(name+'.out')
        build=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),str(path)],capture_output=True,text=True)
        assert build.returncode==0,build.stderr
        run=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
        assert (run.returncode==0)==positive,(name,run.stdout,run.stderr)
