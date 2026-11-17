from pathlib import Path
import json, shutil, re, hashlib, subprocess
L=Path('/srv/opentallas-scratch2/claude/fable-fix-s81-serdes')
R=L/'wt'; P=L/'xface_retime1117'; S=P/'bench/src'; S.mkdir(parents=True,exist_ok=True)
A=R/'rtl/dsrom_sys/s81_link'
def copy(p,q):
    if p.is_file(): shutil.copy2(p,q)
    else: q.write_bytes(subprocess.run(['git','-C',str(R),'show','HEAD:'+str(p.relative_to(R))],capture_output=True,check=True).stdout)
for n in ['ot_s81_kp4_common.sv','ot_s81_kp4_enc.sv','ot_s81_kp4_bm.sv','ot_s81_kp4_dchn.sv','ot_s81_kp4_dout.sv']:
    copy(A/n,S/n)
for n in ['ot_s81_gf1024.svh','ot_s81_kp4_syn_mat.svh','ot_s81_kp4_syn_mat_q4.svh']:
    if (A/n).exists(): copy(A/n,S/n)
for n in ['ot_pl_land.sv']:
    copy(R/'rtl/common/landed_parent'/n,S/n)
for d,n in [('ot_sram_1r1w2c_64x546_m1','ot_sram_1r1w2c_64x546_m1.v'),('ot_sram_1r1w_32x546_m1','ot_sram_1r1w_32x546_m1.v')]:
    copy(R/'physical/asap7_memory_macros'/d/n,S/n)
for n in ['ot_s81_kp4_dsyn.sv','ot_s81_kp4_ddly.sv']:
    old=(P/'h5_src'/n).read_text()
    module=n[:-3]
    (S/(module+'_gold.sv')).write_text(old.replace('module '+module+' ','module '+module+'_gold ',1))
    if module.endswith('dsyn'):
        canonical=(A/n).read_text()
        a=old.index('    // RCK extraction:'); b=old.index('\nendmodule',a)
        ca=canonical.index('    // RCK extraction:'); cb=canonical.index('\nendmodule',ca)
        candidate=old[:a]+canonical[ca:cb]+old[b:]
    else:
        canonical=(A/n).read_text()
        a=old.index('module ot_s81_kp4_ddly #('); b=old.index('    input  wire',a)
        ca=canonical.index('// XPIPE1 moves'); cb=canonical.index('    input  wire',ca)
        candidate=old[:a]+canonical[ca:cb]+old[b:]
    (S/n).write_text(candidate)
parent=(P/'h5_src/ot_s81_kp4_dec_native_flat_lp.sv').read_text()
(S/'ot_s81_kp4_dec_native_flat_lp.sv').write_text(parent)
gold=parent.replace('module ot_s81_kp4_dec_native_flat_lp ','module gold_dec ',1).replace('ot_s81_kp4_dsyn u_syn','ot_s81_kp4_dsyn_gold u_syn').replace('ot_s81_kp4_ddly u_dly','ot_s81_kp4_ddly_gold u_dly')
(S/'gold_dec.sv').write_text(gold)
mut=parent.replace('module ot_s81_kp4_dec_native_flat_lp ','module mutant_dec ',1).replace('ot_s81_kp4_ddly u_dly','ot_s81_kp4_ddly #(.DD(55)) u_dly')
(S/'mutant_dec.sv').write_text(mut)
ports='''.rst_n(rst_n), .p_v(p_v), .p_d(ch_d), .q_v(V), .q_d(D), .q_first(F), .q_unc(U), .q_nerr(N), .q_seq(S), .lock(L), .n_corr(C), .n_unc(E), .n_relock(R), .ck_syn(clk), .ck_dly(clk), .ck_chn(clk), .ck_out(clk)'''
inst=''
for pre,mod in [('g','gold_dec'),('c','ot_s81_kp4_dec_native_flat_lp'),('m','mutant_dec')]:
    inst+=f'wire {pre}v,{pre}f,{pre}u,{pre}l; wire [511:0] {pre}d; wire [4:0] {pre}n; wire [7:0] {pre}s; wire [31:0] {pre}c,{pre}e,{pre}r;\n'
    arg=ports
    for k in ['V','D','F','U','N','S','L','C','E','R']: arg=re.sub(r'\b'+k+r'\b',pre+k.lower(),arg)
    inst+=f'{mod} u_{pre} ({arg});\n'
tb='''`timescale 1ns/1ps
module tb_xface;
 reg clk=0; always #0.4165 clk=~clk;
 reg rst_n=0; reg tx_v=0; reg [511:0] tx_d=0;
 wire p_v; wire [543:0] p_d; wire enc_fault;
 reg [543:0] ch_d;
 ot_s81_kp4_enc u_enc(.clk(clk),.rst_n(rst_n),.tx_v(tx_v),.tx_d(tx_d),.p_v(p_v),.p_d(p_d),.fault(enc_fault));
'''+inst+'''
 integer cyc=0,epoch=0,age=0,bad=0,checks=0,valid_words=0,mut_bad=0,mut_epoch[0:3];
 reg [31:0] rng=32'hb1730a19;
 integer i;
 always @(negedge clk) begin
   cyc=cyc+1;
   if(cyc==9 || cyc==921 || cyc==1841) begin rst_n=1;age=0;end
   if(cyc==901 || cyc==1821) begin rst_n=0;age=0;epoch=epoch+1;end
   tx_v=rst_n;
   for(i=0;i<16;i=i+1) begin
     rng=rng^(rng<<13);rng=rng^(rng>>17);rng=rng^(rng<<5);
     tx_d[i*32+:32]=rng;
   end
   ch_d=p_d;
   // Finite symbol errors, including uncorrectable frames, exercise unchanged syndrome path.
   if(p_v && cyc%97==0) ch_d[123+:10]=p_d[123+:10]^10'h093;
   if(p_v && cyc%211==0) ch_d[300+:160]=p_d[300+:160]^{16{10'h001}};
   if(rst_n) age=age+1;
   if(age>12) begin
     checks=checks+1;
     if({cv,cl,cc,ce,cr} !== {gv,gl,gc,ge,gr}) begin
       bad=bad+1; if(bad<4)$display("XFACE_CONTROL_BAD cycle=%0d age=%0d",cyc,age);
     end
     if(gv || cv) begin
       valid_words=valid_words+1;
       if({cf,cu,cn,cs,cd} !== {gf,gu,gn,gs,gd}) begin
         bad=bad+1; if(bad<4)$display("XFACE_DATA_BAD cycle=%0d epoch=%0d",cyc,epoch);
       end
       if({mf,mu,mn,ms,md} !== {gf,gu,gn,gs,gd}) begin mut_bad=mut_bad+1;mut_epoch[epoch]=mut_epoch[epoch]+1;end
     end
   end
   if(cyc==2800) begin
     if(bad==0 && valid_words>1800 && mut_bad>0 && mut_epoch[0]>0 && mut_epoch[1]>0 && mut_epoch[2]>0)
       $display("XFACE_FULL_DECODER_PASS checks=%0d valid_words=%0d resets=3 mutant_mismatches=%0d",checks,valid_words,mut_bad);
     else $display("XFACE_FULL_DECODER_FAIL checks=%0d valid_words=%0d bad=%0d mutant=%0d epochs=%0d,%0d,%0d",checks,valid_words,bad,mut_bad,mut_epoch[0],mut_epoch[1],mut_epoch[2]);
     $finish;
   end
 end
 initial begin for(i=0;i<4;i=i+1)mut_epoch[i]=0;end
endmodule
'''
(S/'tb_xface.sv').write_text(tb)
sources=sorted(S.glob('*.sv'))+sorted(S.glob('*.v'))
(P/'bench/sources.f').write_text('\n'.join(str(p) for p in sources)+'\n')
receipt={str(p.relative_to(P)):hashlib.sha256(p.read_bytes()).hexdigest() for p in S.iterdir() if p.is_file()}
(P/'bench/source_sha256.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('PREPARED',len(sources),len(receipt))
