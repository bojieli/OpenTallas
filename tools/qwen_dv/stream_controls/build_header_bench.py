from pathlib import Path
import re,json
w=Path('.');s=(w/'results/arch/qwen_stream_controls_1019/native_valid/tb_controls.sv').read_text()
s=s.replace('`timescale 1ns/1ps','`timescale 1ns/1fs').replace('always #5 ck=~ck;','always #0.416666666 ck=~ck;')
s=s.replace('reg[3:0] sid=0;','wire[3:0] sid;').replace('reg[1087:0] sw=0,se=0;','reg[1087:0] rawsw=0,rawse=0;reg[1087:0] sw=0,se=0;')
# Only stimulus writes change to raw inputs; consumer samples actual LP/core captures.
a=s.index(' always @(negedge ck) begin');b=s.index(' always @(posedge ck) begin',a)
x=s[a:b].replace('sw[','rawsw[').replace('se[','rawse[').replace("sid=4'(cycle%16);", "cmd_i={108'd0,4'(cycle%16),4'hf};")
s=s[:a]+x+s[b:];s=s.replace('.sid(MUT==4 ? prior_sid :', '.sid(MUT==4 ? sid_previous_edge :');s=s.replace('  #1;','  #0.001;')
s=re.sub(r'\.sw_i_copies\(\{.*?\}\),\.se_i_copies\(\{.*?\}\),', '.sw_i_copies(sw_feed),.se_i_copies(se_feed),',s)
assert '.sw_i_copies(sw_feed)' in s
insert='''
 integer PHASE=0;reg ck_w=0;
 initial begin if(!$value$plusargs("PHASE=%d",PHASE)) PHASE=0;#(0.416666666+PHASE/1000.0);ck_w=1;forever #0.416666666 ck_w=~ck_w;end
 wire[4351:0] sw_bank,se_bank;wire[11:0] sw_epo,se_epo;wire[183:0] sw_vld,se_vld;
 wire[1087:0] sw_read,se_read;
 ot_pl_land_chunk_w #(.W(1088),.D(4),.CHUNK_BITS(24)) u_ww(.ck(ck_w),.rsi(rst),.i(rawsw),.bank(sw_bank),.epo(sw_epo),.vld(sw_vld));
 ot_pl_land_chunk_w #(.W(1088),.D(4),.CHUNK_BITS(24)) u_we(.ck(ck_w),.rsi(rst),.i(rawse),.bank(se_bank),.epo(se_epo),.vld(se_vld));
 ot_pl_land_chunk_r #(.W(1088),.D(4),.K(2),.CHUNK_BITS(24)) u_rw(.ck(ck),.rsi(rst),.bank(sw_bank),.epo(sw_epo),.vld(sw_vld),.o(sw_read));
 ot_pl_land_chunk_r #(.W(1088),.D(4),.K(2),.CHUNK_BITS(24)) u_re(.ck(ck),.rsi(rst),.bank(se_bank),.epo(se_epo),.vld(se_vld),.o(se_read));
 reg[115:0] cmd_i=0,cmd_q=0;reg[3:0] sid_q=0,sid_previous_edge=0;always @(posedge ck) sid_previous_edge<=sid;
 wire setid=cmd_q[0]&&cmd_q[3:1]==3'd7;assign sid=sid_q;
 always @(posedge ck or negedge rst) if(!rst)begin sw<=0;se<=0;cmd_q<=0;sid_q<=0;end else begin sw<=sw_read;se<=se_read;cmd_q<=cmd_i;if(setid)sid_q<=cmd_q[7:4];end
 wire[95:0] sw_hdr;wire[49:0] se_hdr;reg[95:0] sw_hdr_old=0;reg[49:0] se_hdr_old=0;
 always @(posedge ck)begin sw_hdr_old<=sw_hdr;se_hdr_old<=se_hdr;end
 wire[6:0] capture_resets={7{rst}} | (MUT==7 ? 7'b1 : 7'b0);
 qfd_dv_stream_header_producer u_header(.ck(ck),.rst_read({5{rst}}),.rst_capture(capture_resets),.sw_bank(sw_bank),.se_bank(se_bank),.sw_epo(sw_epo),.se_epo(se_epo),.sw_vld(sw_vld),.se_vld(se_vld),.sw_i_copies(sw_hdr),.se_i_copies(se_hdr));
 wire[95:0] sw_feed;wire[49:0] se_feed=MUT==5 ? se_hdr_old : se_hdr;
 for(genvar k=0;k<96;k=k+1)begin:g_feed
  assign sw_feed[k]=(MUT==5 ? sw_hdr_old[k] : sw_hdr[k]) ^ ((MUT==1)&&(k>=6));
 end
 integer header_checks=0;
'''
pos=s.index(' wire[1087:0] le,lw');s=s[:pos]+insert+s[pos:]
checks=[]
rows=json.loads((w/'results/arch/qwen_stream_controls_1019/native_final/boundary.json').read_text())
for r in rows:
 if r['source_port'] not in ('sw_i','se_i'):continue
 ref='sw' if r['source_port']=='sw_i' else 'se';hdr='sw_hdr' if ref=='sw' else 'se_hdr'
 checks.append(f"  if({hdr}[{r['copy_bit']}] !== {ref}[{r['source_bit']}]) $fatal(1,\"HEADER_CAPTURE_MISMATCH cycle%0d port{ref} bit{r['copy_bit']} MUT%0d\",cycle,MUT);")
s=s.replace('  #0.001;','  #0.001;\n'+('\n'.join(checks))+'\n  header_checks=header_checks+146;')
s=s.replace('STREAM_NATIVE_QUALIFIED_EQ PASS edges10000 resets2 varyingSID/config concurrentrelay/taps/fullcompletion controls+allvalidpayload','STREAM_HEADER_NATIVE_COMPOSE PASS edges10000 resets2 actualLPread/corecapture/SETID checks%0d phase%0d allcontrols+validpayload')
s=s.replace('checks%0d phase%0d allcontrols+validpayload");','checks%0d phase%0d allcontrols+validpayload",header_checks,PHASE);')
p=w/'rtl/test/qwen_dv/stream_controls/tb_header_compose.sv';p.write_text(s)

p=w/'rtl/test/qwen_dv/stream_controls/tb_header_compose.sv';t=p.read_text().replace("rawsw[1086:1084]=3'(cycle%4);rawse[1086:1084]=3'((cycle+1)%4);", "rawsw[1086:1084]=3'(cycle%8);rawse[1086:1084]=3'((cycle+1)%8);");t=t.replace('integer header_checks=0;', 'integer header_checks=0;reg[145:0] seen_one=0,seen_zero=0;').replace('  header_checks=header_checks+146;', '  header_checks=header_checks+146;seen_one=seen_one|{se_hdr,sw_hdr};seen_zero=seen_zero|~{se_hdr,sw_hdr};');t=t.replace('  if(cycle==10000) begin $display(', '  if(cycle==10000) begin if(!(&seen_one)||!(&seen_zero))$fatal(1,"HEADER_DYNAMIC_COVERAGE_MISSING one%h zero%h",seen_one,seen_zero);$display(');p.write_text(t)

p=w/'rtl/test/qwen_dv/stream_controls/tb_header_compose.sv';t=p.read_text().replace("rawsw[1083:1080]=4'(cycle%16);rawse[1083:1080]=4'((cycle+5)%16);", "rawsw[1083:1080]=seed[15:12];rawse[1083:1080]=seed[23:20];");t=t.replace('integer header_checks=0;', 'integer targeted=0,broadcasts=0;reg[15:0] targeted_sids=0;integer header_checks=0;');t=t.replace('  header_checks=header_checks+146;', '  if((sw[1087]&&sw[1086:1084]!=0&&sw[1083:1080]==sid)||(se[1087]&&se[1086:1084]!=0&&se[1083:1080]==sid))begin targeted=targeted+1;targeted_sids[sid]=1;end\n  if((sw[1087]&&sw[1086:1084]!=0&&sw[1083:1080]==15)||(se[1087]&&se[1086:1084]!=0&&se[1083:1080]==15))broadcasts=broadcasts+1;\n  header_checks=header_checks+146;');t=t.replace('if(!(&seen_one)||!(&seen_zero))', 'if(targeted<10||broadcasts<10||!(&targeted_sids))$fatal(1,"HEADER_SID_ROUTE_COVERAGE_MISSING targeted%0d broadcasts%0d sids%h",targeted,broadcasts,targeted_sids);if(!(&seen_one)||!(&seen_zero))');t=t.replace('checks%0d phase%0d allcontrols+validpayload",header_checks,PHASE', 'checks%0d phase%0d target%0d broadcast%0d sids%h allcontrols+validpayload",header_checks,PHASE,targeted,broadcasts,targeted_sids');p.write_text(t)
