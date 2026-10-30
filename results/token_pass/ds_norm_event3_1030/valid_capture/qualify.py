import hashlib,json,re
from pathlib import Path
P=Path(__file__).resolve().parent;parent=P.parent;read=lambda n:json.loads(n.read_text());sha=lambda b:hashlib.sha256(b).hexdigest()
base=(P/'base.log').read_text();negative=(P/'payload.log').read_text()
assert 'BASE_RC=0\nPAYLOAD_RC=1\nGATE_PASS'in(P/'status.txt').read_text()
assert 'NORM_PRODUCER_PASS checks80 errors0'in base
observed=re.findall(r'ACTUAL_VALID_PARTIAL leaf(\d+) cycle(\d+) data([0-9a-f]{8})',base);d={int(i):word for i,c,word in observed}
assert len(observed)==80 and sorted(d)==list(range(80))
actual=''.join(d[i]+'\n'for i in range(80));(P/'actual_partials80.hex').write_text(actual)
assert (parent/'xf/actual_partials80.hex').read_text()==actual
assert (parent/'producer/partial.memh').read_text()==actual
mut={int(i):word for i,c,word in re.findall(r'ACTUAL_VALID_PARTIAL leaf(\d+) cycle(\d+) data([0-9a-f]{8})',negative)}
assert mut[0]!=d[0]and 'NORM_PRODUCER_FAIL'in negative
source=read(parent/'producer/stage.json');native=read(parent/'norm_control.json')
result=dict(schema='opentallas.s81.actual_valid_norm_partial_capture.v1',status='PASS_ACTUAL_VALID_PARTIAL_CAPTURE',
 selected_source_top_sha256=native['die_sha256'],clock_ps=833,source_sha256=source['source_sha256'],
 actual_partial_count=80,actual_partial_input_sha256=sha(actual.encode()),
 actual_input_image_sha256=sha((parent/'producer/entry.memh').read_bytes()),VP_command_pin_to_partial_edges=116,
 actual_partials=[dict(global_beat=int(i),valid_cycle=int(c),data32=word)for i,c,word in observed],
 payload_control=dict(leaf=0,positive=d[0],mutant=mut[0],terminal_failed=True),
 old_late_diagnostic_words_are_handoff=False,
 existing_XF_and_collector_input_bytes_identical=True,
 correction='historical lateNORM_PRODUCER data was printed afterp_v and could drift; onlyACTUAL_VALID_PARTIAL onp_v is authoritative. Previous valid-time80-word score comparisons were correct; originalhandoff usedthat equality-validated scoreboardfile. Canonicalhandoff nowcomesdirectlyfromvalid-timecapture,identicalbytes,nodatapath/RTLrerunofconsumersrequired',
 global_GO_qualified=False,physical_START_qualified=False,full_token=False)
selection=read(parent/'producer/stage.json')
result['defines']=selection['defines']
result['source_selection']=dict(path=selection['selected_manifest'],sha256=selection['selected_manifest_sha256'])
(P/'receipt.json').write_text(json.dumps(result,indent=1)+'\n');print(result['status'],result['actual_partial_input_sha256'],'existinginputsamebytes')
