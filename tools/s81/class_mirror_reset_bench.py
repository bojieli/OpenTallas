#!/usr/bin/env python3
"""Exercise the actual BF-root mirror processes across held-source resets.

This is the smallest control vehicle: the qx_gt function and both mirror always
blocks are copied verbatim from the RTL. Other datapath inputs are boundary
stimulus. Full arithmetic/frame and ROM lockstep receipts are separate.
"""
import argparse, pathlib, re, subprocess
ROOT = pathlib.Path(__file__).resolve().parents[2]

def fragment(text, bit):
    anchor=f'    always @(posedge gclk) if (cen[{bit}]) if (rst_n) begin'
    start=text.index(anchor)
    return text[start:text.index('`ifdef QP_CHECK', start)]

def module(text, name, mode):
    fun=re.search(r'    function automatic \[NSEG-1:0\] qx_gt\(.*?    endfunction',text,re.S).group()
    blocks='\n'.join(fragment(text, b) for b in (24,25))
    reset=re.compile(r'end else begin ([nw])_coh <= NSEG\'\(1\) << \1_c; \1_cgt <= qx_gt\(NSEG\'\(1\) << \1_c\); end[^\n]*')
    assert len(reset.findall(blocks))==2, 'expected exact held-source reset arms'
    if mode=='old': blocks=reset.sub('end', blocks)
    if mode=='zero': blocks=reset.sub(lambda m: f"end else begin {m[1]}_coh <= '0; {m[1]}_cgt <= '0; end", blocks)
    return f'''module {name} #(parameter NSEG=8, SW=5)(
input gclk,rst_n,input [25:0] cen,input go_e,hit,qx_n_end,n_more,
input issue,w_seg_last,w_cl,w_restart,input [4:0] n_c,w_c,c_first,c_live,
input [NSEG-1:0] qn_ohf,qn_ohl,qn_nxoh,qx_ohf,qx_ohl,qx_nxoh,qx_nxgt,
output reg [NSEG-1:0] n_coh,n_cgt,w_coh,w_cgt);
localparam N32=0,GX=0; wire [3:0] gok=0;
wire [6*NSEG-1:0] qn_a_go=0,qn_a_rs=0; wire qn_ca_nx=0;
reg n_ca_r,n_ca_r2;
function automatic ca_f(input [6*NSEG-1:0] fa,input [SW-1:0] fc,input [2:0] fj); ca_f=0; endfunction
{fun}
{blocks}
endmodule
'''

def testbench():
    return r'''module case_one #(parameter NSEG=8)(output reg done=0);
reg clk=0,rst=1,go=1,hit=0,ne=0,nm=0,issue=0,sl=0,cl=0,restart=0;
reg [25:0] cen='1; reg [4:0] nc=0,wc=0,first=0,live=0,nextn=0,nextw=0;
wire [NSEG-1:0] nohf=NSEG'(1)<<first,nohl=NSEG'(1)<<live,nnx=NSEG'(1)<<nextn;
wire [NSEG-1:0] wohf=nohf,wohl=nohl,wnx=NSEG'(1)<<nextw;
function automatic [NSEG-1:0] gt(input [NSEG-1:0] oh);
reg seen; gt=0;seen=0;for(int i=0;i<NSEG;i++)begin gt[i]=seen;seen|=oh[i];end endfunction
wire [NSEG-1:0] oldn,oldng,oldw,oldwg,newn,newng,neww,newwg,mutn,mutng,mutw,mutwg;
`define ARGS .gclk(clk),.rst_n(rst),.cen(cen),.go_e(go),.hit(hit),.qx_n_end(ne),.n_more(nm),.issue(issue),.w_seg_last(sl),.w_cl(cl),.w_restart(restart),.n_c(nc),.w_c(wc),.c_first(first),.c_live(live),.qn_ohf(nohf),.qn_ohl(nohl),.qn_nxoh(nnx),.qx_ohf(wohf),.qx_ohl(wohl),.qx_nxoh(wnx),.qx_nxgt(gt(wnx))
old_kernel #(NSEG) gold (`ARGS,.n_coh(oldn),.n_cgt(oldng),.w_coh(oldw),.w_cgt(oldwg));
new_kernel #(NSEG) dut (`ARGS,.n_coh(newn),.n_cgt(newng),.w_coh(neww),.w_cgt(newwg));
zero_kernel #(NSEG) mutant (`ARGS,.n_coh(mutn),.n_cgt(mutng),.w_coh(mutw),.w_cgt(mutwg));
integer cycles=0,resets=0,mutcaught=0,seed=982737+NSEG; reg seen=0;
initial begin
for(int c=0;c<12000;c++)begin
 if(c>0)begin
 cen[24]=$random(seed);cen[25]=$random(seed);rst=(c%17!=8)&&(c%17!=9);go=(c%29==0);
 hit=$random(seed);ne=$random(seed);nm=$random(seed);issue=$random(seed);sl=$random(seed);cl=$random(seed);restart=$random(seed);
 first=($unsigned($random(seed))%NSEG);live=($unsigned($random(seed))%NSEG);nextn=($unsigned($random(seed))%NSEG);nextw=($unsigned($random(seed))%NSEG);
 end
 #5;clk=1;#1;
 if(rst && cen[24])begin if(go)nc=first;else if(hit)nc=(ne&&nm)?live:nextn;end
 if(rst && cen[25])begin if(go)wc=first;else if(issue&&sl&&cl)wc=restart?live:nextw;end
 if(c==0)seen=1;
 #1;
 if(seen && {oldn,oldng,oldw,oldwg} !== {newn,newng,neww,newwg})$fatal(1,"MIDRESET_MISMATCH N=%0d c=%0d",NSEG,c);
 if(seen && {oldn,oldng,oldw,oldwg} !== {mutn,mutng,mutw,mutwg})mutcaught++;
 if(!rst)resets++;cycles++;
 #3;clk=0;
end
if(mutcaught==0)$fatal(1,"MUTANT_NOT_CAUGHT N=%0d",NSEG);
$display("MIRROR_RESET PASS N=%0d cycles=%0d reset_edges=%0d zero_mutant_caught=%0d",NSEG,cycles,resets,mutcaught);done=1;
end
endmodule
module tb;
wire [3:0] done;
case_one #(1) a(done[0]);case_one #(2) b(done[1]);case_one #(8) c(done[2]);case_one #(32) d(done[3]);
initial begin wait(&done);$display("MIRROR_RESET ALL_PASS actual_BF_processes=2 shapes=4 added_cycles=0");$finish;end
endmodule
'''

def main():
    ap=argparse.ArgumentParser(__doc__);ap.add_argument('--work',type=pathlib.Path,required=True);a=ap.parse_args();a.work.mkdir(parents=True,exist_ok=True)
    src=(ROOT/'rtl/v41rom/ot_v41_bf_front_core_roots.sv').read_text()
    code='\n'.join(module(src,n,m) for n,m in [('old_kernel','old'),('new_kernel','new'),('zero_kernel','zero')])+testbench()
    path=a.work/'mirror_reset.sv';path.write_text(code)
    subprocess.run(['iverilog','-g2012','-s','tb','-o',str(a.work/'sim'),str(path)],check=True)
    subprocess.run(['vvp',str(a.work/'sim')],check=True)
if __name__=='__main__':main()
