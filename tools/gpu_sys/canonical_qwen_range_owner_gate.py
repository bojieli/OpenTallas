"""Prepare ONE source-owned range-owner directed gate; no engine or payload oracle."""
from pathlib import Path
import re,json,hashlib
from tools.gpu_sys.canonical_qwen_source_mapping import SourcePlacement
from tools.gpu_sys.canonical_qwen_range_owner_rtl import generate,BITS
from tools.gpu_sys.canonical_qwen_range_owner_controls import control_model
ROOT=Path(__file__).resolve().parents[2]

def parse_ports(header):
 header=re.sub(r'//[^\n]*', '', header)
 ports={};direction=None;width=''
 for token in header.split(','):
  token=token.strip()
  match=re.fullmatch(r'(input|output) wire(?: \[([^\]]+)\])? ([a-zA-Z_]\w*)',token)
  if match:
   direction,width,name=match.groups();width=width or ''
  else:
   if not direction or not re.fullmatch(r'[a-zA-Z_]\w*',token):raise ValueError('port declaration '+token)
   name=token
  if name in ('input','output') or name in ports:raise ValueError('invalid duplicate port '+name)
  ports[name]=(direction,width)
 return ports

def prepare(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=False)
 p=SourcePlacement.released();rtl=generate(out)
 header=rtl.read_text().split(')(\n',1)[1].split(');',1)[0]
 decl=[];defaults=[]
 for name,(direction,width) in parse_ports(header).items():
  decl.append(('reg' if direction=='input' else 'wire')+(' ['+width+']' if width else '')+' '+name+';')
  if direction=='input':defaults.append(name+"=0;")
 homes=[h for h in p.rf.values() if h.rank==0 and h.sm==0]
 a=next(h for h in homes if h.birth==13 and h.end-h.first==32);b=next(h for h in homes if h.birth==14)
 large=next(h for h in homes if h.birth==13 and h.end-h.first==32)
 def t(h,tag):return (1<<175)|(h.birth<<164)|(tag<<100)|(1<<36)|(p.version_ids[h.version]<<19)|(h.first<<10)|h.end
 bench='''`timescale 1ps/1ps
module tb;
@DECL@
ot_gpu_qwen_native_range_owner #(.ENABLE(1),.SM_INDEX(0)) dut(.*);
always #500 clk=~clk;
integer cycles=0;always @(posedge clk)cycles<=cycles+1;
task step;begin @(posedge clk);#1;@(negedge clk);#1;end endtask
task must(input bit value,input [511:0] label);begin if(!value)$fatal(1,"FAIL %0s cycle%0d",label,cycles);end endtask
reg [238:0] A,B,L;reg [54:0] OA,OB,OL;reg [71:0] held_bad_word;
task reserve(input [238:0] id,input [54:0] own);begin
 claim_tuple=id;claim_owner=own;claim_valid=1;#1;must(claim_ready,"legal claim");step;claim_valid=0;#1;end endtask
task launch(input [238:0] id,input [6:0] mask);begin
 next_source_PC=id[174:164];bind_tuple=id;bind_mask=mask;bind_valid=1;#1;must(bind_ready,"captured canonical inputs");step;bind_valid=0;#1;
 must(inputs_bound_valid&&inputs_bound_tuple==id&&inputs_bound_mask==mask,"held inputs before GO");
 go_tuple=id;go_accepted=1;inputs_bound_ready=1;step;go_accepted=0;inputs_bound_ready=0;#1;end endtask
task finish_frame(input [238:0] id,input [54:0] own,input [6:0] mask);begin
 input_terminal_tuple=id;input_terminal_mask=mask;input_terminal_valid=1;#1;must(input_terminal_ready,"actual terminal");step;input_terminal_valid=0;
 frame_retire_valid=1;frame_retire_tuple=id;frame_retire_owner=own;#1;must(!frame_retire_ready,"reverse needed");frame_retire_valid=0;
 input_reverse_tuple=id;input_reverse_mask=mask;input_reverse_valid=1;#1;must(input_reverse_ready,"actual reverse");step;input_reverse_valid=0;
 frame_retire_valid=1;#1;must(frame_retire_ready,"frame retirement");step;frame_retire_valid=0;#1;end endtask
task pages_and_publish(input [238:0] id,input [54:0] own);integer k,n;begin
 n=id[9:0]-id[18:10];
 producer_visible_tuple=id;producer_visible_valid=1;#1;must(producer_visible_ready,"fullengine visible");step;producer_visible_valid=0;
 publish_tuple=id;publish_owner=own;publish_page_mask=32'hffffffff>>(32-n);publish_valid=1;#1;must(!publish_ready,"visible alone no publication");publish_valid=0;
 for(k=0;k<n;k=k+1)begin
  page_ack_owner={own[54:9],9'(id[18:10]+k)};page_ack_valid=1;#1;must(page_ack_ready,"page common-mirror ACK");step;page_ack_valid=0;#1;
  if(k<n-1)must(!rf_range_ack_valid,"no first-page shortcut");
 end
 must(rf_range_ack_valid&&rf_range_ack_tuple==id&&rf_range_ack_owner==own&&rf_range_ack_page_mask==publish_page_mask,"complete range aggregate");
 repeat(3)begin step;must(rf_range_ack_valid&&rf_range_ack_tuple==id,"range ACK held");end
 rf_range_ack_ready=1;step;rf_range_ack_ready=0;#1;
 publish_valid=1;#1;must(publish_ready,"real pages plus visibility");step;publish_valid=0;#1;end endtask
task read_source(input [238:0] id,input [10:0] ver,input [8:0] slot,input [45:0] own);begin
 query_tuple=id;query_version=ver;query_slot=slot;query_write=0;query_valid=1;#1;must(query_ready,"saved source input association");step;query_valid=0;
 repeat(4)step;#1;must(query_result_valid&&query_result_tuple==id&&query_result_owner==own&&source_owner_retained,"physical held query");
 repeat(2)step;must(query_result_valid,"held read result");query_result_ready=1;step;query_result_ready=0;#1;end endtask
initial begin
 @DEFAULT@
 A=239'h@A@;B=239'h@B@;L=239'h@L@;
 OA={46'd19,A[18:10]};OB={46'd20,B[18:10]};OL={46'd21,L[18:10]};
 por_n=1;#2;por_n=0;#5;por_n=1;step;
 session_begin_id=1;session_begin_valid=1;#1;must(!session_begin_ready,"positive fences needed");
 allcopies_fenced=1;reverse_fenced=1;ingress_quiet=1;#1;must(session_begin_ready,"cold source fences");step;session_begin_valid=0;
 reserve(A,OA);launch(A,0);pages_and_publish(A,OA);finish_frame(A,OA,0);
 must(live_rows[0]&&published_rows[0],"producer frame never clears lease");
 source_native_retire_session=1;source_native_retire_version=A[29:19];source_native_retire_owner=OA;source_native_retire_valid=1;#1;must(!source_native_retire_ready,"declared consumer still owed");source_native_retire_valid=0;
 next_source_PC=A[174:164]+2;#1;must(!row_barrier_ready,"expired lease blocks PC advance");next_source_PC=A[174:164]+1;
 reserve(B,OB);launch(B,7'b1);
 read_source(B,A[29:19],A[18:10],OA[54:9]);
 pages_and_publish(B,OB);finish_frame(B,OB,7'b1);
 source_native_retire_valid=1;#1;must(source_native_retire_ready,"last consumer actual terminal plus reverse");step;source_native_retire_valid=0;
 must(!live_rows[0]&&live_rows[1],"only named source lease retired");
 must(published_rows[1]&&!live_rows[0],"32 page source retained through consumer");
 // Single codeword CE stalls release until actual scrub; no repaired-data bypass.
 @(negedge clk);dut.rows[1].record.coded[0]=~dut.rows[1].record.coded[0];#10;
 must(!dut.all_clean&&!query_ready&&!claim_ready,"CE blocks all source actions");step;#1;must(dut.all_clean&&!fault,"verified next-edge scrub");
 // Double error preserves debt and refuses irreversible publication/retirement.
 @(negedge clk);dut.rows[1].record.coded[0]=~dut.rows[1].record.coded[0];dut.rows[1].record.coded[1]=~dut.rows[1].record.coded[1];#10;
 must(fault&&!source_native_retire_ready&&!frame_retire_ready,"double error fail closed");held_bad_word=dut.rows[1].record.coded[0 +:72];step;
 warm_reset=1;step;warm_reset=0;#1;must(fault&&!session_begin_ready&&dut.rows[1].record.coded[0 +:72]==held_bad_word,"warm reset retains actual coded debt");
 $display("PASS_RANGE_OWNER full239 source_input_rows frame_vs_lease bitmap32 held_query CE DUE reset cycles=%0d",cycles);$finish;
end
endmodule
'''
 replacements={'DECL':'\n'.join(decl),'DEFAULT':'\n '.join(defaults),'A':f'{t(a,100):060x}','B':f'{t(b,101):060x}','L':f'{t(large,102):060x}'}
 for k,v in replacements.items():bench=bench.replace('@'+k+'@',v)
 (out/'tb.sv').write_text(bench)
 codec=ROOT/'rtl/experimental/w2_nc6_protection_20261003/ot_w2_sealed_secded72.sv'
 (out/codec.name).write_bytes(codec.read_bytes())
 model=control_model(p);(out/'model.json').write_text(json.dumps(model,sort_keys=True,indent=2)+'\n')
 manifest={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(out.iterdir()) if x.is_file()}
 (out/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
 return manifest
if __name__=='__main__':
 import argparse
 a=argparse.ArgumentParser();a.add_argument('--out',required=True);print(prepare(a.parse_args().out))
