"""Stage the actual generated HEAD transport/reset coupon; run its script through ot-run."""
from pathlib import Path
import argparse,re,shutil,subprocess
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[2]);ap.add_argument('--generated-root',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
r=a.repo.resolve();o=a.generated_root.resolve();stage=a.out.resolve();stage.mkdir(parents=True,exist_ok=False)
source=[]
for line in (o/'leaf_sources.f').read_text().splitlines()+['rtl/dsrom_sys/s81_head/ot_s81hd_host276.sv','rtl/dsrom_sys/s81_head/ot_s81hd_beat_link.sv']:
 p=r/line;dst=stage/p.name;dst.write_bytes(subprocess.check_output(['git','-C',str(r),'show','HEAD:'+line]));source.append(dst.name)
shutil.copy2(o/'nominal/ot_dp_cells.sv',stage/'ot_dp_cells.sv');source.append('ot_dp_cells.sv')
L=['`timescale 1ns/1ps','module tb_head_transport;','reg ck=0;always #0.4165 ck=~ck;reg raw=0,start=0;integer c=0,post_checks=0,nnew=0,nold=0;',
 'reg[514:0] st_in={1\'b1,2\'b10,512\'hA515B};reg[64:0] mission_in={1\'b1,64\'h1234};',
 'wire[275:0] hstream;reg hv=0;reg[552:0] hf=0;wire txf;wire[276:0] hu_in={1\'b1,hstream};',
 'ot_s81hd_host276_tx tx(.ck(ck),.rn(raw),.v(hv),.frame(hf),.lane(hstream),.fault(txf));']
outputs={}
for kind,tn in [('st','st_k5'),('sp','spn_end'),('phy','serdes')]:
 for mode in ['nominal','old']:
  tag='new' if mode=='nominal' else 'old'; p=o/mode/f'ot_s81hd_{tn}.sv';s=p.read_text();module=f'coupon_{kind}_{tag}';s=re.sub(r'\bot_s81hd_'+tn+r'\b',module,s);f=stage/f'{module}.sv';f.write_text(s);source.append(f.name)
  head=s[:s.index(');')];ports=[]
  for m in re.finditer(r'\b(input|output)\s+wire\s*(?:\[(\d+):0\]\s*)?(\w+)',head):
   direction,w,name=m.group(1),int(m.group(2))+1 if m.group(2) else 1,m.group(3)
   if direction=='input':
    if name.startswith('clk') or name=='pma_rck':value='ck' if w==1 else '{'+str(w)+'{ck}}'
    elif name=='arst_n':value='raw'
    elif name=='start_i':value='start'
    elif kind=='st' and name=='u_i':value='st_in'
    elif kind=='st' and name=='tx_i':value='mission_in'
    elif kind=='sp' and name=='hu_i':value='hu_in'
    elif kind=='sp' and name=='au_i':value='mission_in'
    else:value=f"{w}'d0"
   else:
    value=f'{kind}_{tag}_{name}';L.append(f'wire[{w-1}:0] {value};');outputs[(kind,tag,name)]=(value,w)
   ports.append(f'.{name}({value})')
  L.append(module+' '+kind+'_'+tag+'('+','.join(ports)+');')
for tag in ['new','old']:
 L += [f'wire rv_{tag};wire[552:0] rf_{tag};wire rxf_{tag};',f'ot_s81hd_host276_rx rx_{tag}(.ck(ck),.rn(raw),.lane(sp_{tag}_hu_o[275:0]),.v(rv_{tag}),.frame(rf_{tag}),.fault(rxf_{tag}));']
L += [r'''
function automatic[552:0] config_frame(input integer n);begin
 config_frame=553'd0;config_frame[552]=1;config_frame[3:0]=6;config_frame[23:16]=9;config_frame[87:24]=64'hC0DE0000+n;
end endfunction
always@(negedge ck)begin
 c=c+1;raw=(c>=16);hv=0;
 if(c==100||c==120||c==140)begin hv=1;hf=config_frame((c-100)/20);end
 if(c==190)begin
  if(st_new_u_o[513:0]!==st_in[513:0]||st_old_u_o[513:0]!==st_in[513:0])$fatal(1,"station payload did not move before START");
  if(st_new_u_o[514]!==1||st_old_u_o[514]!==0)$fatal(1,"station bootstrap epoch role mismatch");
  if(sp_new_hu_o[276]!==1||sp_old_hu_o[276]!==0)$fatal(1,"spine bootstrap epoch role mismatch");
  if(phy_new.u_phy.rst_n!==1||phy_old.u_phy.rst_n!==0)$fatal(1,"actual PHY provider reset role mismatch");
  if(sp_new.u_spo.rst_n!==0||sp_new.u_spr.rst_n!==0||sp_old.u_spo.rst_n!==0||sp_old.u_spr.rst_n!==0)$fatal(1,"mission spine core released before START");
  if(st_new_tx_o[64]!==0||sp_new_au_o[64]!==0)$fatal(1,"undeclared mission epoch released before START");
  if(nnew!=3||nold!=3)$fatal(1,"embedded-valid HOST276 frame delivery mismatch new%0d old%0d",nnew,nold);
  $display("PRESTART_PAYLOAD real_HOST276_new=%0d old=%0d station_payload_both=PASS epoch_new_old=1/0 PHY_reset_new_old=1/0 mission_spo_spr_reset=0",nnew,nold);
  $display("OLD_ROLE_MUTANT_CAUGHT missing_raw_epoch_and_PHY_reset; payload_was_not_blocked");
 end
 if(c==200)start=1;
 if(c>=250)begin
  st_in[31:0]=c;
  if(st_new_u_o!==st_old_u_o||sp_new_hu_o!==sp_old_hu_o||st_new_tx_o!==st_old_tx_o||sp_new_au_o!==sp_old_au_o)$fatal(1,"post-START transport lockstep mismatch");
  if(sp_new.u_spo.rst_n!==1||sp_new.u_spr.rst_n!==1)$fatal(1,"mission cores did not release after START");
  post_checks=post_checks+1;
 end
 if(c==450)begin
  if(txf||rxf_new||rxf_old)$fatal(1,"real HOST276 codec fault");
  $display("HEAD_TRANSPORT_BOOT PASS post_START_lockstep_checks=%0d source_cycles_added=0; PHY traffic/token/production dates NOT CLAIMED",post_checks);$finish;
 end
end
always@(posedge ck)begin
 #0.1;
 if(rv_new)begin if(rf_new!==config_frame(nnew))$fatal(1,"new decoded CSR payload mismatch");nnew=nnew+1;end
 if(rv_old)begin if(rf_old!==config_frame(nold))$fatal(1,"old decoded CSR payload mismatch");nold=nold+1;end
end
endmodule
''']
(stage/'tb_head_transport.sv').write_text('\n'.join(L)+'\n');source.append('tb_head_transport.sv');(stage/'sources.f').write_text('\n'.join(dict.fromkeys(source))+'\n')
(stage/'run.sh').write_text('''#!/bin/bash
set -eu
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
verilator --binary --timing -O1 -Wno-fatal -Wno-TIMESCALEMOD -Wno-PINMISSING --top-module tb_head_transport -j 8 -Mdir obj -f sources.f > build.log 2>&1
./obj/Vtb_head_transport > run.log 2>&1
grep '^HEAD_TRANSPORT_BOOT PASS' run.log
''')
print('staged',len(source),'files',sum(p.stat().st_size for p in stage.iterdir() if p.is_file()))

for n in ['ot_s81_gf1024.svh','ot_s81_kp4_syn_mat.svh','ot_s81_kp4_enc_mat.svh']:
 (stage/n).write_bytes(subprocess.check_output(['git','-C',str(r),'show','HEAD:rtl/dsrom_sys/s81_link/'+n]))
