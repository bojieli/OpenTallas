#!/usr/bin/env python3
"""Stage actual native loader/dispatcher replay for an existing compiled boot bundle."""
import argparse,json,re,shutil,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
r=a.repo;o=a.out;o.mkdir(parents=True,exist_ok=True)
here=r/'physical/die_plan/qwen_kvsys/cores/harden';sys.path.insert(0,str(here));import kvsctl_boot_capture as BC
face=r/'rtl/qwen_sys/static_kv_die_20261017/qkd_kv_ctl_nc32_face.sv';text=face.read_text();start=text.index('module qkd_static_kv_boot_dispatch_mu_nc32 ');header=text[start:].split(')(\n',1)[1].split(');',1)[0]
ports={};direction=None;width=''
for token in header.replace('\n',' ').split(','):
 token=token.strip();m=re.fullmatch(r'(input|output)\s+(?:wire|reg)\s*(\[[^]]+\])?\s*(\w+)',token)
 if m:direction,width,name=m[1],m[2] or '',m[3]
 else:name=token
 assert direction and re.fullmatch(r'\w+',name),token
 ports[name]=(direction,width)
inputs={'ck':'ck','rst_n':'rst_n','boot_pr':'boot__boot_pr','boot_image_target':'boot__boot_image_target','boot_image_ready':'boot__boot_image_ready','boot_image_fault':'boot__boot_image_fault','boot_image_epoch':'boot__boot_image_epoch','boot_image_digest':'boot__boot_image_digest','execution_active':'d2d__svc[23:23]','sink_applied':"160'hffffffffffffffffffffffffffffffffffffffff",'local_configured':"3'b111",'sink_fault':"1'b0",'diecfg_sealed':"1'b1",'diecfg_fault':"1'b0"}
outputs=[n for n,(d,w) in ports.items() if d=='output'];nbit=lambda w:1 if not w else int(w[1:].split(':')[0])+1
nb=sum(nbit(ports[n][1]) for n in outputs)
common='input wire ck,rst_n,input wire[142:0]boot__boot_pr,input wire[3:0]boot__boot_image_target,input wire boot__boot_image_ready,boot__boot_image_fault,input wire[15:0]boot__boot_image_epoch,input wire[63:0]boot__boot_image_digest,input wire[173:0]d2d__svc,output wire['+str(nb-1)+':0]obs,output wire setup,output wire fault_o'
body='\n'.join('wire '+ports[n][1]+' q_'+n+';' for n in outputs)+'\nassign obs={'+','.join('q_'+n for n in outputs)+'};\nassign setup=q_setup_ready;assign fault_o=q_fault;\n'
conns=', '.join('.'+n+'('+ (inputs[n] if n in inputs else 'q_'+n)+')' for n in ports)
leaf=(r/'results/kv_host_regen_1/rtl/qkd_kvs_ctl/qkd_kvs_ctl_nc32__leaf.sv').read_text()
production=[x for x in leaf.splitlines() if 'qkd_static_kv_boot_dispatch_mu_nc32 #' in x and ' u_boot (' in x]
assert len(production)==1
inst=production[0].split(' u_boot (',1)[0]+' u_boot ('+conns+');\n'
gold='module boot_gold('+common+');\n'+body+inst+'endmodule\n'
gate,ledger=BC.apply(gold.replace('module boot_gold(','module boot_gate('))
mut=gate.replace('module boot_gate(','module boot_mut(').replace('cb_boot_pr_lo <= boot__boot_pr[74:0];','cb_boot_pr_lo <= boot__boot_pr[74:0]; cb_boot_pr_lo[74] <= wrong_valid;')
mut=mut.replace('    always @(posedge ck) begin ', '    reg wrong_valid;always @(posedge ck) wrong_valid<=boot__boot_pr[74];\n    always @(posedge ck) begin ',1)
assert mut!=gate
(o/'wrappers.sv').write_text(gold+gate+mut)
bundle=json.loads(a.bundle.read_text());(o/'frames.hex').write_text('\n'.join(bundle['frames528'])+'\n');nframes=len(bundle['frames528'])
(o/'ledger.json').write_text(json.dumps(dict(ledger,bundle_epoch=bundle['epoch'],target_order=bundle['target_order'],images=len(bundle['images']),frames=nframes,feedback='legal stable sink_applied/local_configured/diecfg_sealed; this is a capture protocol component test, not a whole-die token pass'),indent=2)+'\n')
for src in (face,r/'rtl/qwen_sys/static_kv_die_20261017/qkd_kv_ctl_c32_boot.sv',r/'rtl/qwen_sys/static_kv_die_20261017/qkd_kv_ctl_c32_misc.sv',r/'rtl/lib/ot_s32_cells.sv',r/'rtl/qwen_sys/host_20261013/qkd_host_program_loader_target.sv',r/'physical/asap7_memory_macros_v2/ot_sram_1rw_256x64_m4_r2c2/ot_sram_1rw_256x64_m4_r2c2.v'):shutil.copy2(src,o/src.name)
tb=r'''`timescale 1ps/1ps
module tb;
reg ck=0;always begin #416 ck=1;#417 ck=0;end
reg rst_n=0,begin_image=0,word_v=0,word_desc=0,seal=0,auth_v=0,execution_active=0;
reg[15:0]image_epoch=0,auth_epoch=0;reg[3:0]image_target=0,auth_target=0,dw_count=0;reg[10:0]pw_count=0;reg[9:0]word_addr=0;reg[63:0]word_data=0,auth_digest=0;
wire[142:0]pr;wire[3:0]replay_target;wire program_ready,loader_fault;wire[63:0]digest;wire[15:0]program_epoch;
qkd_host_program_loader_target #(.MU(1),.AGES(1),.NRST(43),.DIECAP(1)) loader(.ck(ck),.rst_n(rst_n),.begin_image(begin_image),.image_epoch(image_epoch),.image_target(image_target),.auth_target(auth_target),.replay_target(replay_target),.pw_count(pw_count),.dw_count(dw_count),.word_v(word_v),.word_desc(word_desc),.word_addr(word_addr),.word_data(word_data),.seal(seal),.auth_v(auth_v),.auth_epoch(auth_epoch),.auth_digest(auth_digest),.execution_active(execution_active),.pr(pr),.program_ready(program_ready),.fault(loader_fault),.digest(digest),.program_epoch(program_epoch),.authorized_footer_valid(),.authorized_footer());
wire[173:0]svc={150'd0,execution_active,23'd0};
wire ready=program_ready&&!begin_image&&!loader_fault;
wire[NB-1:0]g,c,m;wire gs,cs,ms,gf,cf,mf;
`define PORTS .ck(ck),.rst_n(rst_n),.boot__boot_pr(pr),.boot__boot_image_target(replay_target),.boot__boot_image_ready(ready),.boot__boot_image_fault(loader_fault),.boot__boot_image_epoch(program_epoch),.boot__boot_image_digest(digest),.d2d__svc(svc)
boot_gold G(`PORTS,.obs(g),.setup(gs),.fault_o(gf));
boot_gate C(`PORTS,.obs(c),.setup(cs),.fault_o(cf));
boot_mut M(`PORTS,.obs(m),.setup(ms),.fault_o(mf));
reg[NB-1:0]prev;reg checked=0;integer cycles=0,mismatches=0,mutant_seen=0,word_writes=0,first_gs=-1,first_cs=-1;
always @(posedge ck) begin
 #1;cycles=cycles+1;
 if(rst_n&&cycles>100)begin
  if(checked&&c!==prev)begin mismatches=mismatches+1;if(mismatches<4)$display("MISMATCH cycle%0d target%0d",cycles,replay_target);end
  if(checked&&m!==prev)mutant_seen=mutant_seen+1;
  if(gs&&first_gs<0)first_gs=cycles;if(cs&&first_cs<0)first_cs=cycles;
 end
 prev=g;checked=rst_n;
 if(pr[74])word_writes=word_writes+1;
end
reg[527:0]frames[0:NF-1];integer i,w,images=0;reg[527:0]f;
task idle;begin begin_image=0;word_v=0;seal=0;auth_v=0;end endtask
initial begin
 $readmemh("frames.hex",frames);
 repeat(8)@(negedge ck);rst_n=1;repeat(100)@(negedge ck);
 for(i=0;i<NF;i=i+1)begin
  f=frames[i];idle();
  case(f[7:0])
   1:begin begin_image=1;image_epoch=f[23:8];pw_count=f[34:24];dw_count=f[38:35];image_target=f[42:39];end
   2:begin word_v=1;word_desc=f[8];word_addr=f[18:9];word_data=f[82:19];end
   3:seal=1;
   4:begin auth_v=1;auth_epoch=f[23:8];auth_digest=f[87:24];auth_target=f[91:88];end
   default:$fatal(1,"invalid frame command");
  endcase
  @(negedge ck);idle();@(negedge ck);
  if(f[7:0]==4)begin
   w=0;while(!program_ready&&w<int'(pw_count)+int'(dw_count)+16)begin @(negedge ck);w=w+1;end
   if(!program_ready||loader_fault)$fatal(1,"native loader failed target%0d",image_target);
   repeat(64)@(negedge ck);images=images+1;
   $display("IMAGE target%0d fault gold%0d cap%0d epoch%0d",image_target,gf,cf,program_epoch);
  end
 end
 repeat(64)@(negedge ck);
 if(images!=14||mismatches||gf||cf||!gs||!cs||first_cs!=first_gs+1||!mutant_seen)$fatal(1,"capture FAIL images%0d mismatch%0d faults%0d/%0d setup%0d/%0d rise%0d/%0d mutant%0d",images,mismatches,gf,cf,gs,cs,first_gs,first_cs,mutant_seen);
 $display("PASS images%0d replay_writes%0d cycles%0d setup_rise%0d/%0d extra_boot1 mission0 mutant_mismatches%0d",images,word_writes,cycles,first_gs,first_cs,mutant_seen);$finish;
end
endmodule
'''.replace('NB',str(nb)).replace('NF',str(nframes))
(o/'tb.sv').write_text(tb)
(o/'run.sh').write_text((Path(__file__).parent/'run.sh').read_text())
(o/'.keep').touch()
print(json.dumps(dict(outputs=nb,frames=nframes,stage=str(o))))
