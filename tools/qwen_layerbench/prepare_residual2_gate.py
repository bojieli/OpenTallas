#!/usr/bin/env python3
"""Prepare the actual native SU/VM residual2 witness from a completed XA cache.

No job is launched. Unchanged native bodies are copied into an owned finite
packet. The fixture only replaces the bench, uses actual native instructions1
and2, and initializes exact finite values with PS1 != PS2.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
import residual2_calendar_candidate as R


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base',type=Path,required=True);ap.add_argument('--manifest',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    manifest=json.loads(a.manifest.read_text());checked=R.verify_native_pair(manifest)
    a.out.mkdir(parents=True,exist_ok=False);d=a.out/'input';d.mkdir()
    sources=[];bodies={};total=0
    for i,line in enumerate((a.base/'source.f').read_text().splitlines()):
        src=Path(line)
        if src.name=='tb_mu_native.sv':continue
        target=d/f'{i:03d}_{src.name}';shutil.copy2(src,target);sources.append(target)
        bodies[str(src)]=hashlib.sha256(target.read_bytes()).hexdigest();total+=target.stat().st_size
    sl=manifest['stages'][0]['slices'][0]
    pairs='\n'.join(f" pair{idx}[{u}]=1024'h{sl['prog_users'][u][idx]['payload_hex']};" for u in range(4) for idx in (0,1))
    sv='''`timescale 1ns/1fs
module tb_mu_native;
reg ck=0;always #0.416500 ck=~ck;reg rst_n=0;reg[115:0]cmd=0;
reg wv=0,tv=0;reg[1:0]tk=0;reg[23:0]wa=0,ta=0;reg[511:0]wd=0;reg[1023:0]td=0;
reg[1023:0]pair0[0:3],pair1[0:3];reg[31:0]xs[0:3],exp[0:3];
integer u,j,l,k,active=-1,count=0,checks=0,cyc=0,origin=0,firstw,lastw;reg[383:0]seen=0;reg[23:0]out_a;reg[31:0]out_d,expected;
qfd_dv_s8_flat dut (.ck(ck),.rst_n(rst_n),.cmd_i(cmd),.hr_i('0),.rs_s('0),.rs_n('0),.l9_i('0),.st_up_i('0),.st_dn_i('0),.sc_up_i('0),.sc_dn_i('0),.ch_up_i('0),.ch_dn_i('0),.ag_up_i('0),.treq_i('0));
initial begin
 force dut.w16_we=wv;force dut.w16_addr=wa;force dut.w16_data=wd;
 force dut.tw_we=tv;force dut.tw_kind=tk;force dut.tw_addr=ta;force dut.tw_data=td;
PAIRS
 xs[0]=32'h3f800000;xs[1]=32'h40000000;xs[2]=32'h40400000;xs[3]=32'h40800000;
 exp[0]=32'h40400000;exp[1]=32'h40800000;exp[2]=32'h40a00000;exp[3]=32'h40c00000;
 repeat(64)@(negedge ck);rst_n=1;repeat(64)@(negedge ck);
 cmd=116'd15;@(negedge ck);cmd=0;repeat(16)@(negedge ck);
 for(u=0;u<4;u=u+1)begin
  for(j=0;j<384;j=j+16)begin
   wv=1;wa=24'(4096*u+j);for(l=0;l<16;l=l+1)wd[32*l+:32]=xs[u];@(negedge ck);
   wa=24'(4096*u+416+j);for(l=0;l<16;l=l+1)wd[32*l+:32]=32'h3f800000;@(negedge ck);
  end
  wv=0;tk=1;tv=1;
  for(j=0;j<24;j=j+1)begin
   ta=24'(128*u+j);for(l=0;l<16;l=l+1)td[64*l+:64]=64'h000000003f800000;@(negedge ck);
   ta=24'(128*u+24+j);for(l=0;l<16;l=l+1)td[64*l+:64]=64'h0000000040000000;
   if($test$plusargs("MUT_SCALE")&&u==1)td[31:0]=32'h40400000;@(negedge ck);
  end
  tk=3;ta=24'(64*u);td=pair0[u];@(negedge ck);ta=24'(64*u+1);td=pair1[u];@(negedge ck);tv=0;
  repeat(32)@(negedge ck);
 end
 repeat(64)@(negedge ck);
 for(u=0;u<4;u=u+1)begin
  active=u;seen=0;count=0;firstw=-1;lastw=-1;origin=cyc+1;
  cmd=(116'(2+128*u)<<4)|116'd3;
  if($test$plusargs("MUT_OLD_CALLER"))cmd=(116'(1+128*u)<<4)|116'd3;
  if($test$plusargs("MUT_USER")&&u==1)cmd=(116'd2<<4)|116'd3;
  @(negedge ck);cmd=0;repeat(1024)@(negedge ck);
  if(count!=384||seen!=={384{1'b1}})$fatal(1,"RES2_COVERAGE user%0d count%0d idle%b sufault%b vmfault%b",u,count,dut.su_idle,dut.su_fault,dut.vm_fault);
  if(dut.su_fault||dut.vm_fault)$fatal(1,"RES2_NATIVE_FAULT");
  $display("NATIVE_RES2_USER_PASS user%0d pidx%0d words%0d first%0d last%0d PS1=1 PS2=2 X%h expect%h",u,2+128*u,count,firstw,lastw,xs[u],exp[u]);active=-1;
 end
 $display("NATIVE_RES2_PASS words1536 users4 checks%0d actualnativeMA_AB_AD_C PS1notPS2 period833ps",checks);$finish;
end
always @(negedge ck)begin
 cyc=cyc+1;
 if(rst_n&&active>=0)begin
  for(k=0;k<8;k=k+1)if(dut.L_vm_we[k])begin
   out_a=dut.L_vm_waddr[24*k+:24];out_d=dut.L_vm_wdata[32*k+:32];
   if(out_a<24'(4096*active)||out_a>=24'(4096*active+384))$fatal(1,"RES2_WRONG_USER_OR_ADDRESS user%0d addr%h",active,out_a);
   j=integer'(out_a)-4096*active;expected=exp[active];
   if(out_d!==expected||seen[j])$fatal(1,"RES2_PAYLOAD_MISMATCH user%0d index%0d got%h expected%h duplicate%b",active,j,out_d,expected,seen[j]);
   if(firstw<0)firstw=cyc-origin;lastw=cyc-origin;seen[j]=1;count=count+1;checks=checks+1;
  end
 end
end
endmodule
'''.replace('PAIRS',pairs)
    tb=d/'tb_mu_native.sv';tb.write_text(sv);sources.append(tb)
    (a.out/'source.f').write_text(''.join(str(p.resolve())+'\n' for p in sources))
    receipt=dict(status='PREP_ONLY_NOT_LAUNCHED',prior_native_vehicle=str(a.base),native_pairs_checked=checked,
        manifest_sha256=hashlib.sha256(a.manifest.read_bytes()).hexdigest(),unchanged_bodies_sha256=bodies,
        source_files=len(sources),source_bytes=total+tb.stat().st_size,
        actual_native_instruction_pidx=[2,130,258,386],controls=['MUT_OLD_CALLER','MUT_SCALE','MUT_USER'],
        claim_boundary='native SU/VM arithmetic and actual word-index dispatch; excludes production calendar playhead, reduction aggregation and ROOT RSTD')
    (a.out/'preparation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:receipt[k] for k in ('status','source_files','source_bytes','native_pairs_checked')}))

if __name__=='__main__':main()
