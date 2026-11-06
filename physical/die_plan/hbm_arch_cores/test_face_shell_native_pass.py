#!/usr/bin/env python3
"""Native-register cut: whole shell equals two selectively shelled elastic/skid pieces, including reverse ready."""
import importlib.util
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('fs', HERE / 'face_shell.py')
fs = importlib.util.module_from_spec(spec); spec.loader.exec_module(fs)
PROD = '''module prod(input wire clk,rst_n,input wire i_v,input wire[7:0]i_d,output wire i_ready,
 input wire send_r,output reg send_v,output reg[7:0]send_d);
 assign i_ready=!send_v||send_r;
 always @(posedge clk or negedge rst_n)if(!rst_n)send_v<=0;else if(i_ready)send_v<=i_v;
 always @(posedge clk)if(i_ready&&i_v)send_d<=i_d;
endmodule
'''
DP = '''module dp(input wire clk,rst_n,input wire send_v,input wire[7:0]send_d,output wire send_r,
 input wire o_r,output wire o_v,output wire[7:0]o_d);
 ot_hbm_svc_pin_skid2 #(.WIDTH(8)) u_native(.clk(clk),.rst_n(rst_n),.in_v(send_v),.in_r(send_r),
 .in_data(send_d),.out_v(o_v),.out_r(o_r),.out_data(o_d));
endmodule
'''
WIDTHS = dict(clk=1,rst_n=1,i_v=1,i_d=8,i_ready=1,o_r=1,o_v=1,o_d=8)
DIRS = {n: ('output' if n in ('i_ready','o_v','o_d') else 'input') for n in WIDTHS}
WHOLE = '''module whole_native(input wire clk,rst_n,input wire i_v,input wire[7:0]i_d,output wire i_ready,
 input wire o_r,output wire o_v,output wire[7:0]o_d);
 wire send_v,send_r;wire[7:0]send_d;
 prod__fcore u_p(.clk(clk),.rst_n(rst_n),.i_v(i_v),.i_d(i_d),.i_ready(i_ready),.send_r(send_r),.send_v(send_v),.send_d(send_d));
 dp__fcore u_o(.clk(clk),.rst_n(rst_n),.send_r(send_r),.send_v(send_v),.send_d(send_d),.o_r(o_r),.o_v(o_v),.o_d(o_d));
endmodule
module cut_wrap(input wire clk,rst_n,input wire i_v,input wire[7:0]i_d,output wire i_ready,
 input wire o_r,output wire o_v,output wire[7:0]o_d);
 wire send_v,send_r;wire[7:0]send_d;
 prod u_p(.clk(clk),.rst_n(rst_n),.i_v(i_v),.i_d(i_d),.i_ready(i_ready),.send_r(send_r),.send_v(send_v),.send_d(send_d));
 dp u_o(.clk(clk),.rst_n(rst_n),.send_r(send_r),.send_v(send_v),.send_d(send_d),.o_r(o_r),.o_v(o_v),.o_d(o_d));
endmodule
'''
TB = '''module tb;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,i_v=0,o_r=0;reg[7:0]i_d=0;wire gr,cr,gv,cv;wire[7:0]gd,cd;
 integer i,bad=0,writes=0,stalls=0;reg[15:0] rng=16'h7123;
 gold_wrap g(.clk(clk),.rst_n(rst_n),.i_v(i_v),.i_d(i_d),.i_ready(gr),.o_r(o_r),.o_v(gv),.o_d(gd));
 cut_wrap c(.clk(clk),.rst_n(rst_n),.i_v(i_v),.i_d(i_d),.i_ready(cr),.o_r(o_r),.o_v(cv),.o_d(cd));
 initial begin
  repeat(5)@(negedge clk);rst_n=1;
  for(i=0;i<600;i=i+1)begin
   @(negedge clk);
   if(i>8)begin
    if(gr!==cr||gv!==cv||(gv&&gd!==cd))bad=bad+1;
    if(gv&&o_r)writes=writes+1;
    if(gv&&!o_r)stalls=stalls+1;
   end
   rng={rng[14:0],rng[15]^rng[13]^rng[12]^rng[10]};
   i_v=(i<500)&&(rng[0]||rng[2]);i_d=rng[11:4];o_r=(i>=500)||(rng[3]&&rng[5]);
  end
  if(writes<40||stalls<40)$fatal(1,"no flow-control coverage %0d %0d",writes,stalls);
  $display("NATIVE_CUT bad=%0d writes=%0d stalls=%0d",bad,writes,stalls);
  if(bad)$fatal(1,"native cut differs");$finish;
 end
endmodule
'''

def fixture(root, module, source, pass_buses=None, extra=()):
    kd = root/module; (kd/'rtl').mkdir(parents=True)
    path=kd/'rtl'/f'{module}.sv'; path.write_text(source)
    local=[str(path)]; srcs=[f'/work/rtl/{module}.sv']
    for f in extra:
        target=kd/'rtl'/f.name;target.write_text(f.read_text());local.append(str(target));srcs.append('/work/rtl/'+f.name)
    report=fs.apply(kd,module,local,srcs,{},[],[],r'^clk$',r'^rst_n$',drop=False,pass_buses=pass_buses)
    return kd,report


def run(root, prod_shell):
    p=root/'sim';p.mkdir(exist_ok=True)
    (p/'prod_shell.sv').write_text(prod_shell)
    (p/'whole.sv').write_text(WHOLE);(p/'tb.sv').write_text(TB)
    (p/'gold.sv').write_text(fs.emit_shell('gold_wrap','whole_native',{},WIDTHS,DIRS,WIDTHS,{'clk','rst_n'},'clk'))
    files=[p/'tb.sv',p/'whole.sv',p/'gold.sv',p/'prod_shell.sv',root/'dp/rtl/dp__fshell.sv',
           root/'prod/rtl/prod.sv',root/'dp/rtl/dp.sv',root/'dp/rtl/ot_hbm_svc_pc_ctrl_leaf.sv',root/'prod/rtl/ot_hbm_face_reg.sv']
    subprocess.run(['iverilog','-g2012','-s','tb','-o',str(p/'sim'),*(str(f) for f in files)],check=True)
    q=subprocess.run(['vvp',str(p/'sim')],capture_output=True,text=True)
    return q.returncode,q.stdout

with tempfile.TemporaryDirectory() as temp:
    root=Path(temp)
    repo=HERE.parents[2]
    leaf=repo/'rtl/hbm_accel/loader/service_native/ot_hbm_svc_pc_ctrl_leaf.sv'
    prod,pr=fixture(root,'prod',PROD,[r'^send_(v|d|r)$'])
    dp,dr=fixture(root,'dp',DP,[r'^send_(v|d|r)$'],[leaf])
    for report in (pr,dr):
        assert report['native_registered_passthrough']==['send_d','send_r','send_v']
        assert report['face_cycle_overrides']==dict(send_d=0,send_r=0,send_v=0)
        assert report['face_flops']==10
    sh=(prod/'rtl/prod__fshell.sv').read_text()
    assert 'u_bin_send_r' not in sh and 'u_bout_send_' not in sh
    rc,out=run(root,sh);assert rc==0,out;print(out.strip())
    # Wrong ready latency is a real flow-control mutation, not merely a string test.
    w=dict(clk=1,rst_n=1,i_v=1,i_d=8,i_ready=1,send_r=1,send_v=1,send_d=8)
    d={n:('output' if n in ('i_ready','send_v','send_d') else 'input') for n in w}
    for name,passthrough in [('ready_registered',{'clk','rst_n','send_v','send_d'}),
                             ('data_registered',{'clk','rst_n','send_v','send_r'})]:
        mutant=fs.emit_shell('prod','prod__fcore',{},w,d,w,passthrough,'clk')
        rc,out=run(root,mutant);assert rc!=0,(name,'mutant survived',out);print(name,'CAUGHT',out.strip().splitlines()[0])
    # Empty option keeps old generation byte-identical and does not add metadata.
    a,ar=fixture(root/'default_none','prod',PROD,None)
    b,br=fixture(root/'default_empty','prod',PROD,[])
    assert (a/'rtl/prod__fshell.sv').read_text()==(b/'rtl/prod__fshell.sv').read_text()
    assert 'native_registered_passthrough' not in ar and 'face_cycle_overrides' not in ar
    try:
        fixture(root/'bad','prod',PROD,[r'^missing$'])
    except RuntimeError as e:
        assert 'matches no signal bus' in str(e)
    else:
        raise AssertionError('unmatched native passthrough accepted')
print('test_face_shell_native_pass PASS')
