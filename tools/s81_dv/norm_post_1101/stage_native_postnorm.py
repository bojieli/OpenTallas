from pathlib import Path
import shutil,json
r=Path('/srv/opentallas-scratch2/claude/codex-ds-norm-1101');a=r/'native_final_post_v1';b=r/'native_final_postnorm_v1';b.mkdir(exist_ok=False)
for n in ['source','source.f','defines.f','stage.json','closure_retry.json','img.mem','imgv.mem','exp.mem','manifest.json']:
 if(a/n).is_dir():shutil.copytree(a/n,b/n)
 else:shutil.copyfile(a/n,b/n)
g=json.loads((r/'postnorm_gold_v2/gold.json').read_text());shutil.copyfile(r/'postnorm_gold_v2/gold.json',b/'postnorm_gold.json');shutil.copyfile(r/'head_gain_source_v1/head_gain_leaf0.memh',b/'head_gain.memh');shutil.copyfile(r/'head_gain_source_v1/source.json',b/'HEAD_gain_source.json')
s=(a/'tb_current_native_leaf.sv').read_text();s=s.replace('reg[127:0]rows_[0:1023];','reg[127:0]gain_[0:15];reg[1103:0]assembled_=0;integer nq=0,nb=0,npartial=0,fridx=0,normpin=-1;reg[127:0]rows_[0:1023];')
s=s.replace('if(op_==2)postpin=cyc;', 'if(op_==2)postpin=cyc;if(op_==7)normpin=cyc;')
monitor='''always @(posedge ck)begin #3;
if(arst_n&&normpin>=0&&dut.u_u_lf0_u_vn_u_b.p_v)begin npartial++;$display("POSTNORM_PARTIAL mode%0d age%0d data%08h",which,cyc-normpin,dut.u_u_lf0_u_vn_u_b.p_d);if(dut.u_u_lf0_u_vn_u_b.p_d!==32'hPARTIAL)errors++;end
if(arst_n&&normpin>=0&&dut.u_u_lf0_u_vq.xf_v)begin
 if(dut.u_u_lf0_u_vq.xf_s)fridx=0;
 assembled_[276*fridx+:276]=dut.u_u_lf0_u_vq.xf;
 if(fridx==3)begin
  if(assembled_[20:13]!==8'd128)errors++;
  if(assembled_[3:1]==3'd1)begin nq++;if(assembled_[21+:532]!==532'hQPAY)begin errors++;$display("POSTNORM_Q_BAD");end end
  else if(assembled_[3:1]==3'd2)begin nb++;if(assembled_[21+:1024]!==1024'hBPAY)begin errors++;$display("POSTNORM_BF_BAD got%0256h",assembled_[21+:1024]);end end
  else errors++;
 end
 fridx=(fridx+1)%4;
end end
'''.replace('PARTIAL',g['partial']).replace('QPAY',g['Q_payload']).replace('BPAY',g['BF16_payload'])
# Preserve label as a stable readable marker after replacing the numeric token.
monitor=monitor.replace('POSTNORM_'+g['partial'],'POSTNORM_PARTIAL')
s=s.replace('initial begin $readmemh',monitor+'initial begin $readmemh')
s=s.replace('$readmemh("img.mem",rows_);','$readmemh("head_gain.memh",gain_);$readmemh("img.mem",rows_);')
s=s.replace(' tick(16);command(3,0,0,0);','for(integer j=0;j<16;j++)begin data_={128\'d0,gain_[j]};if($test$plusargs("mut_headgain")&&j==0)data_[23]=~data_[23];packet=pack(0,0,1,10\'(480+j),8\'h0f,data_);tick(1);packet=pack(0,0,0,0,0,0);tick(1);end\n tick(16);command(3,0,0,0);')
seq='''command(1,480,0,0);tick(80);
for(which=0;which<2;which++)begin nq=0;nb=0;npartial=0;fridx=0;normpin=-1;command(7,1008,128,which==0?2:3);tick(140);packet=pack(0,0,0,0,0,0);packet[67]=1;packet[66:35]=32'hRSTD;tick(1);packet=pack(0,0,0,0,0,0);tick(180);$display("POSTNORM_CASE mode%0d Q%0d BF%0d partial%0d",which,nq,nb,npartial);if(nq!=which||nb!=1||npartial!=1)errors++;end
'''.replace('RSTD',g['rstd'])
s=s.replace('$display("POST_FAULT',seq+'$display("POST_FAULT')
s=s.replace('NATIVE_POST_', 'NATIVE_POSTNORM_');(b/'tb_current_native_leaf.sv').write_text(s);(b/'.keep').write_text('critical nativePOST→HEADGAIN→NORM component; no upstreamauthority\n')
