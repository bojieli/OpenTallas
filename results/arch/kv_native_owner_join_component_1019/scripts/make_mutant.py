#!/usr/bin/env python3
"""Materialize ONE source mutant from a frozen manifest; never runs a build."""
import argparse,hashlib,json,pathlib,re
p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',required=True);p.add_argument('--mutant',required=True,choices=['epoch','generation','stage','input_next','client_substitution','latest_pending','rank_masks','early_post','raw_cleanup','pin_aw_before','pin_w_before','bridge_duplicate','false_retire_marker','false_cq_marker']);a=p.parse_args()
src=pathlib.Path(a.source).resolve();out=pathlib.Path(a.out).resolve()
if out.exists():raise SystemExit('refuse existing output')
m=json.loads((src/'source_manifest.json').read_text());out.mkdir(parents=True)
for row in m['sources']:
 f=src/row['path'];data=f.read_bytes()
 if hashlib.sha256(data).hexdigest()!=row['sha256']:raise SystemExit('frozen source changed '+row['path'])
 d=out/row['path'];d.parent.mkdir(parents=True,exist_ok=True);d.write_bytes(data)
core='private/qkd_host_native_owner_join_rc.sv';case=0;fail='HEALTHY_SOURCE_FAULT';condition=None
if a.mutant in ('epoch','generation','stage','input_next'):
 field={'epoch':(45,16,10),'generation':(0,2,11),'stage':(39,6,12),'input_next':(21,18,13)}[a.mutant]
 lo,width,case=field;mask=((1<<87)-1)^(((1<<width)-1)<<lo)
 path=core;old='certificate_key!=expected_key';new=f"(certificate_key&87'h{mask:x})!=(expected_key&87'h{mask:x})";fail='CORRUPT_CERTIFICATE_WAS_ACCEPTED'
elif a.mutant=='client_substitution':
 path=core;old='a_d.request_tag=allocation_tag;';new="a_d.request_tag={43'd0,p_q.client};";fail='BOUND_KEY_IS_NATIVE_TAG59'
elif a.mutant=='latest_pending':
 path=core;old='cq_key!=expected_key';new="cq_key!={p_q.client,p_q.slot,p_q.desc_gen,{a_q.request_tag[58:43],6'd37,p_q.input_token,p_q.position[12:0],6'd0},p_q.package_gen}";case=3
 condition='actual next UNBOUND pending issue must coexist with old CQ B; never fabricate another allocation'
elif a.mutant=='rank_masks':
 path='private/qkd_host_peer_coordinator_codec_rc.sv';old='result_busy&&(&result_return)';new='result_busy&&(|result_return)';case=8;fail='ENGINE_CREDIT_BEFORE_ALL_RESULT_RETURNS';condition='separate watchdog512 cancellation fixture, rank7 result return delayed by genuine drain'
elif a.mutant=='early_post':
 path='baseline/rtl/qwen_sys/host_integrated_20261014/qkd_host_post_collector.sv';old='(!cq_needed||cq_seen||MUT==1)';new="1'b1";case=3;fail='POST_BEFORE_REAL_CQB'
elif a.mutant=='raw_cleanup':
 path='private/qkd_host_native_token_endpoint_cancel_rc.sv';old='RC_MUT=0';new='RC_MUT=2';case=4;fail='RAW_CLEANUP_HEALTH_VETO';condition='real health failure after all actual requests; existing RC_MUT2 gates real native retirement'
elif a.mutant=='pin_aw_before':
 path='private/qkd_host_if_pins_observed_rc.sv';old='.out_d({m_awaddr,m_awlen,m_awsize})';new='.out_d({mut_aw_raw,m_awlen,m_awsize})';case=1;fail='OFFERED_AW_CHANGED_BEFORE_ACCEPTANCE'
elif a.mutant=='pin_w_before':
 path='private/qkd_host_if_pins_observed_rc.sv';old='.out_d({m_wdata,m_wstrb,m_wlast})';new='.out_d({mut_w_raw,m_wstrb,m_wlast})';case=2;fail='OFFERED_W_CHANGED_BEFORE_ACCEPTANCE'
elif a.mutant=='bridge_duplicate':
 path='private/qkd_host_axi_packet_rc.sv';old='wire capture_aw=!dw&&!ba&&!m_awready&&m_awvalid_q;';new='wire capture_aw=!dw&&!m_awready&&m_awvalid_q;';case=2;fail='EXTRA_BRIDGE_AW_CAPTURE_ACK'
elif a.mutant=='false_retire_marker':
 path='private/ot_host_if_pb2_observed_rc.sv';old='step_retire_native_valid<=ENABLE_NATIVE_OWNER_JOIN && pending_native_valid;';new="step_retire_native_valid<=1'b0;";case=0;fail='RETIRE_MARKER_ALIGNMENT'
else:
 path='private/ot_host_if_pb2_observed_rc.sv';old='cq_native_valid_observed<=ENABLE_NATIVE_OWNER_JOIN && cq_saved_native_valid;';new="cq_native_valid_observed<=1'b0;";case=0;fail='CQ_MARKER_ALIGNMENT'
f=out/path;s=f.read_text()
if s.count(old)!=1:raise SystemExit(f'exact mutation anchor count {s.count(old)} for {path}: {old}')
oldsha=hashlib.sha256(f.read_bytes()).hexdigest();s=s.replace(old,new,1)
if a.mutant=='pin_aw_before':s=s.replace('endmodule',"wire[63:0]mut_aw_raw;assign m_awaddr=mut_aw_raw ^ (m_wready?64'd1:64'd0);\nendmodule",1)
if a.mutant=='pin_w_before':s=s.replace('endmodule',"wire[63:0]mut_w_raw;assign m_wdata=mut_w_raw ^ (m_awready?64'd1:64'd0);\nendmodule",1)
f.write_text(s)
for row in m['sources']:
 if row['path']==path:row['sha256']=hashlib.sha256(f.read_bytes()).hexdigest();row['bytes']=f.stat().st_size;row['origin']+='; deliberate causal mutation '+a.mutant
m['causal_mutant']=a.mutant
(out/'source_manifest.json').write_text(json.dumps(m,indent=2)+'\n');(out/'sources.f').write_bytes((src/'sources.f').read_bytes())
(out/'mutant.json').write_text(json.dumps({'name':a.mutant,'changed_source':path,'original_sha256':oldsha,'mutated_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'old':old,'new':new,'case':case,'required_fail_regex':fail,'extra_condition':condition,'verdict':'NOT_RUN','caught_requires':'baseline same negative/healthy case passes; mutated application fails named invariant with committed trace; timeout alone is not causal evidence','fixture_watchdog':512 if a.mutant=='rank_masks' else 1<<22},indent=2)+'\n')
print('MATERIALIZED',a.mutant,'case',case,'not run')
