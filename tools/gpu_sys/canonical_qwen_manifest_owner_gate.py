"""Source-derived actual allinput/multioutput owner gate, canonical SM0 PCs0..11.

External engine/cold initializer events are synthetic, full identities; no
payload/producer arithmetic oracle or whole-program qualification.
"""
from pathlib import Path
import json,hashlib
from tools.gpu_sys.canonical_qwen_source_mapping import SourcePlacement
from tools.gpu_sys.canonical_qwen_range_owner_gate import parse_ports
from tools.gpu_sys.canonical_qwen_manifest_range_owner import generate,model,profiles
ROOT=Path(__file__).resolve().parents[2]

def prepare(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=False)
 p=SourcePlacement.released();m=model(p)
 (out/'model.json').write_text(json.dumps(m,sort_keys=True,indent=2)+'\n')
 rtl=generate(out,p);ports=parse_ports(rtl.read_text().split(')(\n',1)[1].split(');',1)[0])
 decl=[];defaults=[]
 for n,(d,w) in ports.items():
  decl.append(('reg' if d=='input' else 'wire')+(' ['+w+']' if w else '')+' '+n+';')
  if d=='input':defaults.append(n+'=0;')
 # Reuse the actual qualified tasks verbatim, adapt only module name and
 # append tasks for a complete output manifest, with every actual page ACK.
 old=(ROOT/'rtl/test/canonical_qwen_range_owner_20261003/tb_r2.sv').read_text()
 tasks=old[old.index('task step;'):old.index('initial begin')]
 tasks=tasks.replace('reg [238:0] A,B,L;reg [54:0] OA,OB,OL;reg [71:0] held_bad_word;','')
 tasks=tasks.replace('claim_tuple=id;claim_owner=own;claim_valid=1;', 'claim_tuple=id;claim_owner=own;claim_valid=1;')
 hs=[h for h in p.rf.values() if h.rank==0 and h.sm==0]
 sequence=[h for h in sorted(hs,key=lambda h:p.version_ids[h.version]) if h.birth<0]+[h for pc in range(12) for h in sorted(hs,key=lambda h:p.version_ids[h.version]) if h.birth==pc]
 def tup(h,tag):return (1<<175)|((2047 if h.birth<0 else h.birth)<<164)|(((1<<63)|tag)<<100)|(((1<<63)|1)<<36)|(p.version_ids[h.version]<<19)|(h.first<<10)|h.end
 symbols={h.version:'T'+str(i) for i,h in enumerate(sequence)}
 definitions=[]
 for i,h in enumerate(sequence):
  tag=90+p.version_ids[h.version] if h.birth<0 else 100+h.birth
  definitions.append(f"reg [238:0] T{i};reg [54:0] O{i};")
 events=[];row_for={};free=list(range(7));tagmap={}
 for pc in range(12):
  if not any(h.birth==pc for h in sequence):definitions.append(f'reg [238:0] Z{pc};reg [54:0] OZ{pc};')
 def alloc(h):
  r=free.pop(0);row_for[h.version]=r;idx=sequence.index(h)
  return f"claim_initial={int(h.birth<0)};reserve(T{idx},O{idx});claim_initial=0;"
 def page_events(group,root):
  r=sequence.index(root);lines=[f'producer_visible_tuple=T{r};producer_visible_valid=1;#1;must(producer_visible_ready,"whole root visible");step;producer_visible_valid=0;']
  all_pages=[(sequence.index(h),slot) for h in group for slot in range(h.first,h.end)]
  for n,(idx,slot) in enumerate(all_pages):
   lines.append(f"page_ack_owner={{O{idx}[54:9],9'd{slot}}};page_ack_valid=1;#1;must(page_ack_ready,\"source manifest ACK\");step;page_ack_valid=0;#1;")
   if n<len(all_pages)-1:lines.append('must(!rf_range_ack_valid,"all siblings needed not anchor alone");')
  lines += [f'must(rf_range_ack_valid&&rf_range_ack_tuple==T{r}&&rf_range_ack_owner==O{r},"root anchor aggregate after ALL outputs");',
            'repeat(2)begin step;must(rf_range_ack_valid,"held manifest ACK");end',
            'rf_range_ack_ready=1;step;rf_range_ack_ready=0;',
            f'publish_tuple=T{r};publish_owner=O{r};publish_page_mask=expected_output_page_mask;publish_valid=1;#1;must(publish_ready,"whole output manifest publication");step;publish_valid=0;#1;']
  return '\n'.join(lines)
 for seed in (h for h in sequence if h.birth<0):
  si=sequence.index(seed);events += [alloc(seed),f'issuer_held_owner55=O{si};launch(T{si},0);',page_events([seed],seed),f'finish_frame(T{si},O{si},0);']
 for pc in range(12):
  group=[h for h in sequence if h.birth==pc];root=group[0] if group else None;idx=sequence.index(root) if root else None
  rootname='T'+str(idx) if root else 'Z'+str(pc);ownname='O'+str(idx) if root else 'OZ'+str(pc)
  inputs=[h for h in hs if pc in h.consumers]
  mask=sum(1<<row_for[h.version] for h in inputs)
  for n,h in enumerate(group):
   if n==len(group)-1 and len(group)>1:
    events +=[f'bind_tuple={rootname};bind_mask=7\'d{mask};#1;must(!bind_ready,"incomplete output manifest refused");']
   events.append(alloc(h))
  if inputs:events.append(f'bind_tuple={rootname};bind_mask=0;#1;must(!bind_ready,"omitted canonical input refused");')
  events.append(f'issuer_held_owner55={ownname};launch({rootname},7\'d{mask});')
  for h in inputs:
   hi=sequence.index(h);events.append(f'read_source({rootname},T{hi}[29:19],T{hi}[18:10],O{hi}[54:9]);')
  if group:events.append(page_events(group,root))
  else:events.append(f'producer_visible_tuple={rootname};producer_visible_valid=1;#1;must(producer_visible_ready,"whole nonRF provider visible separate");step;producer_visible_valid=0;must(rf_range_ack_valid&&rf_range_ack_page_mask==0&&rf_range_ack_tuple=={rootname}&&rf_range_ack_owner=={ownname},"typed emptyRF debt witness");rf_range_ack_ready=1;step;rf_range_ack_ready=0;publish_tuple={rootname};publish_owner={ownname};publish_page_mask=0;publish_valid=1;#1;must(publish_ready,"nonRF wholepublication");step;publish_valid=0;')
  events.append(f'finish_frame({rootname},{ownname},7\'d{mask});')
  for h in inputs:
   if h.consumers[-1]==pc:
    hi=sequence.index(h);events.append(f'source_native_retire_session=1;source_native_retire_version=T{hi}[29:19];source_native_retire_owner=O{hi};source_native_retire_valid=1;#1;must(source_native_retire_ready,"actual last consumer retirement");step;source_native_retire_valid=0;')
    free.append(row_for.pop(h.version));free.sort()
  events.append('must(!fault,"no hidden source faults");')
  if pc==5:events.append('must($countones(live_rows)==4,"ALL3 PC5 outputs plus initial input remain");')
 initializers=['T%d=239\'h%060x;O%d={46\'d%d,T%d[18:10]};'%(i,tup(h,90+p.version_ids[h.version] if h.birth<0 else 100+h.birth),i,200+i,i) for i,h in enumerate(sequence)]
 for pc in range(12):
  if not any(h.birth==pc for h in sequence):
   t=(1<<175)|(pc<<164)|(((1<<63)|100+pc)<<100)|(((1<<63)|1)<<36)|(2047<<19)
   initializers.append(f"Z{pc}=239'h{t:060x};OZ{pc}={{46'd{300+pc},9'd0}};")
 tasks=tasks.replace('next_source_PC=id[174:164];','next_source_PC=(id[174:164]==2047)?0:id[174:164];')
 tasks=tasks.replace('go_tuple=id;go_accepted=1;inputs_bound_ready=1;','go_tuple=id;go_accepted=1;inputs_bound_ready=1;issuer_held_valid=1;issuer_held_tuple=id;')
 tasks=tasks.replace('frame_retire_valid=1;#1;must(frame_retire_ready,"frame retirement");','frame_retire_valid=1;workspace_children_drained=0;#1;must(!frame_retire_ready,"scratch accepted childdebt prevents frame release");workspace_children_drained=1;#1;must(frame_retire_ready,"frame retirement");')
 bench='''`timescale 1ps/1ps
module tb;
@DECL@
ot_gpu_qwen_manifest_range_owner #(.ENABLE(1),.SM_INDEX(0)) dut(.*);
always #500 clk=~clk;
integer cycles=0;always @(posedge clk)cycles<=cycles+1;
@DEFS@
@TASKS@
initial begin
@DEFAULT@
@INITS@
workspace_children_drained=1;por_n=1;#2;por_n=0;#5;por_n=1;step;
session_begin_id=1;session_begin_valid=1;allcopies_fenced=1;reverse_fenced=1;ingress_quiet=1;#1;must(session_begin_ready,"source cold fence");step;session_begin_valid=0;
@EVENTS@
must(published_rows==live_rows&&$countones(live_rows)==2,"only canonical future-consumer versions survive PC11");
warm_reset=1;step;warm_reset=0;#1;must(fault&&$countones(live_rows)==2&&!session_begin_ready,"warm reset never clears output leases");
$display("PASS_MANIFEST_OWNER sourcecompletePC0to11 allinputrows all3outputs typedEmptyRF scratchDrain noRepeatedGO whole239 frameVsLease cycles=%0d",cycles);$finish;
end
endmodule
'''
 for k,v in {'DECL':'\n'.join(decl),'DEFS':'\n'.join(definitions),'TASKS':tasks,'DEFAULT':'\n'.join(defaults),'INITS':'\n'.join(initializers),'EVENTS':'\n'.join(events)}.items():bench=bench.replace('@'+k+'@',v)
 (out/'tb.sv').write_text(bench)
 codec=ROOT/'rtl/experimental/w2_nc6_protection_20261003/ot_w2_sealed_secded72.sv';(out/codec.name).write_bytes(codec.read_bytes())
 manifest={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(out.iterdir()) if f.is_file()}
 (out/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n');return manifest
if __name__=='__main__':
 import argparse
 a=argparse.ArgumentParser();a.add_argument('--out',required=True);print(prepare(a.parse_args().out))
