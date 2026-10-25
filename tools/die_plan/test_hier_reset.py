import re
import shutil
import subprocess
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from hier_reset import lift_module,LiftError

CORE='''module core #(parameter W=8,ID=0)(input wire clk,rst_n,input wire[W-1:0]d,output reg[W-1:0]q);
reg[1:0] private_reset;
always @(posedge clk) begin private_reset<={private_reset[0],rst_n}; if(!private_reset[1])q<=0;else q<=d+ID;end
endmodule
'''
BANK='''module bank #(parameter N=4,BASE=3)(input wire clk,rst_n,input wire[7:0]d,output wire[N*8-1:0]q);
genvar j;
generate for(j=0;j<N;j=j+1)begin:g_lane
 core #(.ID(BASE+j)) u_core(.clk(clk),.rst_n(rst_n),.d(d),.q(q[j*8+:8]));
end endgenerate
endmodule
'''
WRAP='''module wrap #(parameter N=4,BASE=3)(input wire clk,rst_n,input wire[7:0]d,output wire[N*8-1:0]q);
bank #(.N(N),.BASE(BASE)) u_bank(.clk(clk),.rst_n(rst_n),.d(d),.q(q));
endmodule
'''

def lifted():
    b,br=lift_module(BANK,'bank','N',[dict(module='core',instance='u_core',kind='leaf',pin='rst_n',old='rst_n',role='external_distribution',expr='ot_core_rst_n[j]')])
    w,wr=lift_module(WRAP,'wrap','N',[dict(module='bank',instance='u_bank',kind='pass',expr='ot_core_rst_n')])
    return b,w,br,wr


def test_parameterized_generate_lift_preserves_private_core_and_default_behavior(tmp_path):
    if not shutil.which('iverilog'):
        pytest.skip('iverilog unavailable')
    b,w,br,wr=lifted()
    # The protected core source is not passed to the rewriter. Its two private
    # reset edges remain in every reference, original and lifted instance.
    assert br['added_sequential_edges']==wr['added_sequential_edges']==0
    assert 'for(j=0;j<N;j=j+1)' in b and '.ID(BASE+j)' in b
    bl=re.sub(r'\bbank\b','bank_lift',b)
    wl=re.sub(r'\bbank\b','bank_lift',re.sub(r'\bwrap\b','wrap_lift',w))
    mutant_b=bl.replace('bank_lift','bank_wrong').replace('ot_core_rst_n[j]','ot_core_rst_n[(j+1)%N]')
    mutant_w=wl.replace('bank_lift','bank_wrong').replace('wrap_lift','wrap_wrong')
    tb='''module tb;
reg clk=0,rst_n=0;reg[7:0]d=0;reg[3:0] resets=0;always #5 clk=~clk;
wire[31:0]oldq,offq,onq,refq,wrongq;
wrap #(.N(4),.BASE(7)) orig(clk,rst_n,d,oldq);
wrap_lift #(.N(4),.BASE(7)) disabled(.clk(clk),.rst_n(rst_n),.d(d),.q(offq),.ot_core_rst_n(resets));
wrap_lift #(.N(4),.BASE(7),.OT_HIER_RST(1)) enabled(.clk(clk),.rst_n(rst_n),.d(d),.q(onq),.ot_core_rst_n(resets));
wrap_wrong #(.N(4),.BASE(7),.OT_HIER_RST(1)) mutant(.clk(clk),.rst_n(rst_n),.d(d),.q(wrongq),.ot_core_rst_n(resets));
genvar k;generate for(k=0;k<4;k=k+1)begin:g_ref
core #(.ID(7+k)) c(.clk(clk),.rst_n(resets[k]),.d(d),.q(refq[k*8+:8]));
end endgenerate
integer i,muts=0,checks=0;
initial begin
 for(i=0;i<160;i=i+1)begin
  @(negedge clk);rst_n=(i>12 && i%37>3);d=i*13;
  resets[0]=(i>18 && i%29>4);resets[1]=(i>20 && i%31>5);
  resets[2]=(i>23 && i%43>7);resets[3]=(i>25 && i%47>9);
  @(posedge clk);#1;
  if(i>8)begin
   checks=checks+1;
   if(oldq!==offq)$fatal(1,"default behavior changed");
   if(onq!==refq)$fatal(1,"lift/direct-core reference mismatch");
   if(wrongq!==refq)muts=muts+1;
  end
 end
 if(muts==0)$fatal(1,"wrong reset index mutant escaped");
 $display("PASS checks=%0d index_mutant=%0d private_core_edges=2",checks,muts);$finish;
end
endmodule
'''
    p=tmp_path/'all.sv';p.write_text(CORE+BANK+WRAP+bl+wl+mutant_b+mutant_w+tb)
    exe=tmp_path/'sim'
    c=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),str(p)],capture_output=True,text=True)
    assert c.returncode==0,c.stderr
    r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
    assert r.returncode==0,r.stdout+r.stderr
    assert 'PASS checks=151' in r.stdout


@pytest.mark.parametrize('role',['private_state','unknown',None])
def test_private_or_unclassified_reset_edge_rejected(role):
    with pytest.raises(LiftError,match='external_distribution'):
        lift_module(BANK,'bank','N',[dict(module='core',instance='u_core',kind='leaf',pin='rst_n',old='rst_n',role=role,expr='ot_core_rst_n[j]')])


def test_changed_original_carrier_fails_closed():
    with pytest.raises(LiftError,match='original reset expression changed'):
        lift_module(BANK,'bank','N',[dict(module='core',instance='u_core',kind='leaf',pin='rst_n',old='private_q',role='external_distribution',expr='ot_core_rst_n[j]')])


def test_conditional_alternative_opens_share_connection_close(tmp_path):
    # Actual ot_s81sl_vp syntax: parameterized versus hardened child opening,
    # followed by one common tail after `endif. Both source sites must be lifted.
    alt=BANK.replace(' core #(.ID(BASE+j)) u_core(.clk(clk),.rst_n(rst_n),.d(d),.q(q[j*8+:8]));',
                    '''`ifndef HARD
 core #(.ID(BASE+j)) u_core(.clk(clk),.rst_n(rst_n),
`else
 core u_core(.clk(clk),.rst_n(rst_n),
`endif
 .d(d),.q(q[j*8+:8]));''')
    new,rec=lift_module(CORE+alt,'bank','N',[dict(module='core',instance='u_core',kind='leaf',pin='rst_n',old='rst_n',source_role='external_distribution',expr='ot_core_rst_n[j]',expected=2)])
    assert CORE in new  # co-hosted core-private body remains byte-identical
    assert rec['edges'][0]['source_sites']==2
    assert new.count('OT_HIER_RST ? (ot_core_rst_n[j])')==2
    if shutil.which('iverilog'):
        src=tmp_path/'conditional.sv';src.write_text(new)
        for defines in ([],['-DHARD']):
            p=subprocess.run(['iverilog','-g2012','-s','bank',*defines,'-o',str(tmp_path/'sim'),str(src)],capture_output=True,text=True)
            assert p.returncode==0,p.stderr


def test_conditional_shared_reset_connection_is_edited_once(tmp_path):
    alt=BANK.replace(' core #(.ID(BASE+j)) u_core(.clk(clk),.rst_n(rst_n),.d(d),.q(q[j*8+:8]));',
                    '''`ifndef HARD
 core #(.ID(BASE+j)) u_core(
`else
 core u_core(
`endif
 .clk(clk),.rst_n(rst_n),.d(d),.q(q[j*8+:8]));''')
    new,rec=lift_module(CORE+alt,'bank','N',[dict(module='core',instance='u_core',kind='leaf',pin='rst_n',old='rst_n',source_role='external_distribution',expr='ot_core_rst_n[j]',expected=2)])
    assert rec['edges'][0]['source_sites']==2
    assert new.count('OT_HIER_RST ? (ot_core_rst_n[j])')==1
    if shutil.which('iverilog'):
        src=tmp_path/'shared.sv';src.write_text(new)
        for defines in ([],['-DHARD']):
            p=subprocess.run(['iverilog','-g2012','-s','bank',*defines,'-o',str(tmp_path/'sim'),str(src)],capture_output=True,text=True)
            assert p.returncode==0,p.stderr
