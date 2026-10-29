"""Smallest real RF_LOCAL source cut: port lockstep, mutant, and driver check.
Run after the canonical counter rename; HEAD is the unchanged source reference.
"""
from pathlib import Path
import json,subprocess,sys
root=Path(__file__).resolve().parents[2];out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
source='rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_static_pgslice.sv'
old=subprocess.check_output(['git','show','HEAD:'+source],cwd=root,text=True);new=(root/source).read_text()
def cut(text,name,mut=False):
    start=text.index(' if(RF_LOCAL)begin:g_rf_local');end=text.index(' end else begin:g_rf_direct',start)
    body=text[start:end].replace(' if(RF_LOCAL)begin:g_rf_local',' generate if(1)begin:g_rf_local')
    if mut:body=body.replace('rf_bcmd[vb_valid*9+8]','rf_bcmd[vb_valid*9+7]')
    return f'''module {name}(input wire clk_ctl,rst_n,input wire[127:0]rf_bword,input wire[255:0]rf_dsec,input wire[35:0]rf_bcmd,
output wire[127:0]rf_bword_u,output wire[255:0]rf_dsec_u,output wire[35:0]rf_bcmd_u);
'''+body+'\n end endgenerate\nendmodule\n'
bench='''module tb;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg[127:0] word=0;reg[255:0] sec=0;reg[35:0] cmd=0;
 wire[419:0] a,b;integer i,j,checks=0;
 gold g(clk,rst_n,word,sec,cmd,a[419:292],a[291:36],a[35:0]);
 dut d(clk,rst_n,word,sec,cmd,b[419:292],b[291:36],b[35:0]);
 initial begin
  for(i=0;i<256;i=i+1)begin
   @(negedge clk);rst_n=(i>2 && !(i>=99&&i<=101));
   for(j=0;j<4;j=j+1)word[j*32+:32]=$random;
   for(j=0;j<8;j=j+1)sec[j*32+:32]=$random;
   cmd={$random,$random};
   @(posedge clk);#1;
   if(a!==b)$fatal(1,"RF_LOCAL mismatch edge=%0d",i);
   checks=checks+1;
  end
  $display("RF_LOCAL PASS checks=%0d warmreset=1",checks);$finish;
 end
endmodule
'''
rows=[]
for mut in (False,True):
    p=out/('mutant' if mut else 'exact');p.mkdir(exist_ok=True)
    (p/'cut.sv').write_text(cut(old,'gold')+cut(new,'dut',mut)+bench)
    build=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(p/'a.out'),str(p/'cut.sv')],capture_output=True,text=True)
    assert build.returncode==0,build.stderr
    run=subprocess.run(['vvp',str(p/'a.out')],capture_output=True,text=True);(p/'result.log').write_text(run.stdout+run.stderr)
    rows.append(dict(mode='valid-bit mutant' if mut else 'exact',returncode=run.returncode,accepted=(run.returncode!=0 if mut else run.returncode==0)))
for name,text in [('old',old),('new',new)]:
    p=out/(name+'.sv');p.write_text(cut(text,name))
    run=subprocess.run(['yosys','-Q','-p',f'read_verilog -sv {p}; hierarchy -top {name}; proc; check -assert'],capture_output=True,text=True)
    (out/(name+'_drivers.log')).write_text(run.stdout+run.stderr)
    rows.append(dict(mode=name+' driver check',returncode=run.returncode,accepted=(run.returncode!=0 if name=='old' else run.returncode==0)))
record=dict(checks=rows,pass_all=all(x['accepted'] for x in rows),added_cycles=0,note='Counter separation changes only private procedural iteration variables; RF data/valid sampled edges are unchanged.')
(out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=1));sys.exit(0 if record['pass_all'] else 1)
