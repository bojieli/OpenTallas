import hashlib,json,re
from pathlib import Path
P=Path(__file__).resolve().parent;read=lambda p:json.loads(p.read_text())
assert 'PHASE0_RC=0\nPHASE166_RC=0\nPHASE_M166_RC=0\nBAD_LINK_RC=1\nGATE_PASS'in(P/'status.txt').read_text()
stage=read(P/'stage.json');mapping=read(P/'boundaries.json');profiles=[]
for name,shift,want in[('phase0',0,11),('phase166',166,10),('phase_m166',-166,11)]:
 text=(P/(name+'.log')).read_text();assert 'RESCALE_PASS vectors8 BF16elements64 errors0 rstd40ca3c85 rstd_to_y017 clock833'in text
 m=re.search(r'ACTUAL_RETURN source(\d+) XR(\d+) VN(\d+) XRlocal(\d+) native_link(\d+) firstY(\d+) shift(-?\d+) ready(\d) fault(\d) epoch(\d)',text);assert m
 source,xr,vn,local,link,y,sh,ready,fault,epoch=map(int,m.groups());assert(local,link,y,sh,ready,fault,epoch)==(2,want,17,shift,1,0,1)
 profiles.append(dict(fclk_shift_ps=shift,component_source_event=source,XR_RSTD_output_event=xr,VN_RSTD_input_event=vn,
  XR_local_edges=local,native_selected_link_edges=link,VN_RSTD_to_first_Y_edges=y,source_event_to_first_Y_edges=local+link+y,
  actual_BF16_outputs=64,errors=0,landing_ready=True,landing_fault=False,destination_epoch=True))
negative=(P/'bad_link.log').read_text();assert 'RSTD_TRANSPORT_DATA got408a3c85 want40ca3c85 epoch1'in negative and 'BF16elements64 errors9'in negative
chosen=next(r for r in mapping['leaves']if r['sid']==0 and r['leaf']==2)
assert chosen['active_packet_bits']==595 and chosen['rstd_bus_bits']==dict(valid=68,data=list(range(36,68)))and chosen['bound_lane_edges']==11
result=dict(schema='opentallas.s81.actual_native_RSTD_return_cut.v1',status='PASS_CONDITIONAL_SOURCE_CLOCK_RETURN_PROFILES',clock_ps=833,
 actual_native_path=dict(lane='dn_s_0S_L2',source_clock=chosen['source_clock'],receiver_clock=chosen['receiver_clock'],
  primitive_path='currentXR1 local2;actualCresetcarrierD6/XRresetD7;W595sourceboundary;W596ot_dp_clk_landing;6nativeot_dp_stFTstations;W595destboundary;actualVNpublicRSTDpins',
  other_source_fields='quiescent valid0, actualresetcarrierbit0 and epoch preserved; no spare-bit or alternateKV-layout inference'),
 declared_clock_fixture=stage['clock_profiles'],profiles=profiles,
 actual_RSTD_source='current16XFcaptured40ca3c85',genuine_input_context='SID0leaf2 ofcurrent3920image;samequalifiedVP/VNconsumer,8actualpacked128vectors',
 source_sha256=stage['source_sha256'],wrong_RSTD_packet_bit_control=dict(got='408a3c85',wanted='40ca3c85',payload_mismatches=1,Y_vector_mismatches=8,terminal_failure=True,native_landing_fault_claimed=False),
 all80_boundary_wiring_sha256=hashlib.sha256((P/'boundaries.json').read_bytes()).hexdigest(),
 advertised_count_is_universal_actual_latency=False,physical_clock_phase_authority=False,
 note='observednative link11/10/11 provesconditionalphase dependence; advertised11 cannotbeusedasactualglobaldatewithoutcurrentclock/readercontract. ExistingnominalPDSKtie/repairisprivatePREP underadvertisedcountbook only',
 global_GO_qualified=False,global_RSTD_dates_qualified=False,physical_START_qualified=False,native_programme_admitted=False,production_RTL_or_plan_changed=False,full_token=False)
(P/'receipt.json').write_text(json.dumps(result,indent=1)+'\n');print(result['status'],'link11/10/11,Y30/29/30,3profiles+payloadcontrol')
