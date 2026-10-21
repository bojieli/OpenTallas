"""Reserved-zero role inventory, not a native qualification or waiver."""
from pathlib import Path
import json,gzip,re,sys,hashlib
r=Path.cwd();t=r/'rtl/test/host_peer_main_fixture_1020';report=Path(sys.argv[1]);out=Path(sys.argv[2]);d=json.loads(gzip.decompress(report.read_bytes()));rows=d['constant_output_bits'];actual={}
for x in rows:
 m=re.fullmatch(r'(.+)\[(\d+)\]',x['port_bit']);assert m,x
 p,b=m.groups();actual.setdefault(p,set()).add(int(b));assert x['source']['function']=='0',x
ctd=set(range(2,5))|set(range(6,8))|set(range(10,16))|set(range(19,24))|set(range(263,512))
cohort=set(range(0,6))|set(range(37,43));expected={'u_rank__u_control__u_packet__ctd':ctd,'cohort_tag':cohort};assert actual==expected,{p:sorted(v^expected.get(p,set()))for p,v in actual.items()}
p=t/'historical/rtl/qwen_sys/host_cluster_20261017/peer_pd/qkd_host_ctrl_token_service_packet_collected_pd2.sv';s=p.read_text();expr=re.findall(r'tx_d\s*<=\s*(.*?);',s,re.S);assert len(expr)==5,len(expr)
allocator=r/'rtl/qwen_sys/redesign_qwen/ot_qwen_tp8_token_epoch_allocator.sv';a=allocator.read_text();assert "assign grant_tag = {grant_epoch,6'd0,grant_token,grant_position[12:0],6'd0};"in a
z={'status':'PASS_RESERVED_ZERO_ROLE_INVENTORY','scope':'No dynamic pin is waived or tied by this audit; native fullleaf remains FAIL384/max731. Exact source packet layout accounts for all277 preexisting constant output bits.','packet_ctd':{'count':len(ctd),'zero_ranges':[[2,4],[6,7],[10,15],[19,23],[263,511]],'reason':'Opcode21/22/23 uses only bits0,1,5; version1/2 only8,9; rank3bits16..18; target24..31; sequence32..47; active182bits48..229; epoch230..245, marker246, service_epoch247..262; no source field writes high263..511.','source_tx_assignments':expr,'assignment_sha256':hashlib.sha256('\n'.join(expr).encode()).hexdigest()},'cohort_tag':{'count':len(cohort),'zero_ranges':[[0,5],[37,42]],'reason':'Allocator grant_tag exact59bit tuple epoch16,zero6,token18,position13,zero6.','source':str(allocator.relative_to(r)),'source_sha256':hashlib.sha256(allocator.read_bytes()).hexdigest()}}
out.write_text(json.dumps(z,indent=2)+'\n');print(z['status'],len(rows),'packet',len(ctd),'cohort',len(cohort))
