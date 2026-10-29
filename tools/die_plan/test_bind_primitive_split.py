import copy,subprocess,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bind_elab as E
from bind_primitive_split import split_cells,PrimitiveSplitError
from bind import _glue

def fixture():
 c=E.Cell('ff','$adff',{},dict(CLK=[1],ARST=[2],D=list(range(10,18)),Q=list(range(20,28))),dict(CLK='input',ARST='input',D='input',Q='output'),'glue',ytype='$adff',yparams=dict(WIDTH='1000',CLK_POLARITY='0',ARST_POLARITY='1',ARST_VALUE='10100110'))
 return c,[dict(member='ff',fragments=[dict(path='ff.a',bits=[7,0,4]),dict(path='ff',bits=[1,2,3,5,6])])]

def test_exact_cover_and_rejection():
 c,s=fixture();new,receipt=split_cells([c],s,E.Cell)
 assert len(new)==2 and receipt[0]['terminal_partition_equality']
 assert c.ports['Q']==list(range(20,28)) and c.yparams['ARST_VALUE']=='10100110'
 for bad in ([0,1], [7,0,4,4], [True,0,4]):
  ss=copy.deepcopy(s);ss[0]['fragments'][0]['bits']=bad
  with pytest.raises(PrimitiveSplitError):split_cells([c],ss,E.Cell)
 c.ytype='$aldff'
 with pytest.raises(PrimitiveSplitError,match='unsupported'):split_cells([c],s,E.Cell)

def test_split_native_ff_lockstep_and_mutant(tmp_path):
 c,s=fixture();cs,receipt=split_cells([c],s,E.Cell)
 def emit(c,i):
  def bit(b):return 'cp'if b==1 else 'rst'if b==2 else f'd[{b-10}]'if b<20 else f'q[{b-20}]'
  conns={p:'{'+','.join(bit(b)for b in reversed(bs))+'}'for p,bs in c.ports.items()}
  # A scalar event control must remain a scalar expression.
  conns['CLK']='cp';conns['ARST']='rst'
  return _glue(c,conns,str(i))
 exact='\n'.join(emit(c,i)for i,c in enumerate(cs))
 bench='''module tb;reg cp=0,rst=0;reg[7:0]d=0;wire[7:0]q;reg[7:0]gold;integer i;
 always #5 cp=~cp;
 always @(negedge cp or posedge rst)if(rst)gold<=8'b10100110;else gold<=d;
 FRAGMENTS
 always @(cp or rst)begin #1;if(q!==gold)$fatal(1,"fragment mismatch");end
 initial begin #2;rst=1;#4;rst=0;for(i=0;i<512;i=i+1)begin #7;d=$random;if(i==111)rst=1;if(i==114)rst=0;end
 $display("SPLIT LOCKSTEP PASS512 cold/warm reset+negative clock+nonzero reset");$finish;end endmodule
'''
 for name,rtl,ok in [('exact',exact,True),('wrong_reset',exact.replace("3'b001","3'b000",1),False),('wrong_clock',exact.replace('negedge cp','posedge cp',1),False)]:
  if name=='wrong_reset':assert rtl!=exact
  p=tmp_path/(name+'.sv');p.write_text(bench.replace('FRAGMENTS',rtl));exe=tmp_path/(name+'.out')
  b=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),str(p)],capture_output=True,text=True)
  assert b.returncode==0,b.stderr
  run=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
  assert (run.returncode==0)==ok,(name,run.stdout,run.stderr)
