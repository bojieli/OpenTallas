import hashlib,json,re
from pathlib import Path
P=Path(__file__).resolve().parent;parent=P.parent;read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=(P/'base.log').read_text();negative=(P/'bad_rstd.log').read_text();stage=read(P/'stage.json');native=read(parent/'norm_control.json')
assert 'BASE_RC=0\nBAD_RSTD_RC=1\nGATE_PASS'in(P/'status.txt').read_text()
assert 'RESCALE_PASS vectors640 BF16elements5120 errors0 rstd40ca3c85 rstd_to_y017 clock833'in base
traces=re.findall(r'CURRENT_Y leaf(\d+) vectors(\d+) rstd_to_y0(\d+)',base)
assert len(traces)==80 and {int(i)for i,n,a in traces}==set(range(80))and {(int(n),int(a))for i,n,a in traces}=={(8,17)}
assert 'RESCALE_FAIL vectors640 BF16elements5120 errors640 rstd408a3c85'in negative
assert stage['actual_rstd_sha256']==sha(parent/'xf/actual_rstd.hex')==sha(P/'actual_rstd.hex')
assert sha(P/'entry.memh')==sha(parent/'producer/entry.memh')
result=dict(schema='opentallas.s81.current_norm_rescale_component.v1',status='PASS_CURRENT_NATIVE_NORM_RESCALE_COMPONENT_ONLY',
 selected_source_top_sha256=native['die_sha256'],clock_ps=833,source_sha256=stage['source_sha256'],
 actual_input_image_sha256=sha(P/'entry.memh'),actual_rstd_input_sha256=stage['actual_rstd_sha256'],actual_rstd32='40ca3c85',
 actual_vectors128=640,actual_BF16_elements=5120,errors=0,VN_RSTD_pin_to_first_Y_edges=17,
 output_format='eightBF16 lanes in actualpacked128bit vector;80leaves×8vectors;notlegacy256bitFP32container',
 first_Y_boundary='publicVN rb_v/rb_d drivenafterposedge;17includesVNinputcapture;nativeXF/RSTD/leaftransport separate',
 all_Y_observed_after_RSTD_within_component_wait_edges=101,
 matched_RSTD_corruption=dict(actual='408a3c85',terminal_failure=True,vector_mismatches=640),
 golden_rstd_used_as_input=False,expected_Y_scoreboard_only=True,
 global_RSTD_dates_qualified=False,global_GO_qualified=False,physical_START_qualified=False,full_token=False)
selection=read(parent/'producer/stage.json')
result['defines']=selection['defines']
result['source_selection']=dict(path=selection['selected_manifest'],sha256=selection['selected_manifest_sha256'])
(P/'receipt.json').write_text(json.dumps(result,indent=1)+'\n');print(result['status'],'5120BF16exact,RSTDpin→Y0=17,causalrstdcontrol640errors')
