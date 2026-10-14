#!/usr/bin/env python3
"""Collect bound ACK CTS actual pins/netlist, without treating CTS as routed closure."""
from pathlib import Path
import json,subprocess,re,gzip,hashlib,sys,collections
R=Path(__file__).resolve().parents[2];OUT=R/'results/arch/s81_hrow_reset_ack_1014/physical_candidate';sys.path.insert(0,str(Path(__file__).resolve().parent));from s81_ph_hrow_reset_classify import blocks,prop,uses
seq={}
for p in (R/'results/arch/s81_hrow_native_placement_1013/reset_classification').glob('*_RVT_SS.lib.gz'):
 for name,body,_ in blocks(gzip.open(p,'rt').read(),'cell'):
  if list(blocks(body,'ff')) or list(blocks(body,'latch')):seq[name]=body
summary={}
for kit in ['dsfd_die_rstsync_m5_ack1','hrow5_ing_ack1','hrow5_hub_ack1','dsfd_hrow_r1025_m5_ack1','dsfd_hrow_r2079_m5_ack1']:
 gp=R/'physical/ref_tile'/kit/'gate_result.json'
 if not gp.exists():summary[kit]={'status':'RUNNING gate'};continue
 g=json.loads(gp.read_text());b=g['source_binding'];assert b['schema']=='opentallas.ref_tile.source_snapshot.v1';assert len(b['route_overlay_plan']['files'])==46;assert b['route_overlay_plan']['content_sha256']==json.loads((OUT/'frozen_helpers46.json').read_text())['content_sha256']
 spec=json.loads((gp.parent/'spec.json').read_text());top=spec['top'];host=b['remote_host'];run=b['remote_run'];flow=run+'/routes/gate/work/orfs';base='/results/asap7/opentallas_'+top+'_asap7_ref_gate/base';out=OUT/'actual_cts'/top;out.mkdir(parents=True,exist_ok=True)
 image=re.search(r'GATE_TOOL_IMAGE_ID=(\S+)',b['runtime_tool_provenance'][0])[1]
 remoteout=run+'/pin_receipt'
 cmd=f'mkdir -p {remoteout}\ndocker run --rm -e HROW_ODB=/work{base}/4_1_cts.odb -e HROW_SOURCE={flow}{base}/4_1_cts.odb -v {run}/src:/src:ro -v {flow}:/work -v {remoteout}:/out {image} /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -python /src/tools/s81_ph/extract_actual_bterm_pins.py'
 r=subprocess.run(['ssh',host,'bash -s'],input=cmd,capture_output=True,text=True);(out/'pin_extract.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr
 subprocess.run(['scp',host+':'+remoteout+'/pins.json',str(out/'pins.json')],check=True,capture_output=True)
 net=flow+base+'/1_2_yosys.v';r=subprocess.run(['ssh',host,'cat '+net],capture_output=True);assert r.returncode==0;raw=r.stdout;gzip.open(out/'1_2_yosys.v.gz','wb').write(raw)
 types=collections.Counter();witness=[]
 for typ,name,body in re.findall(r'^\s*(\w+)\s+(\\\S+|[\w$]+)\s+\((.*?)\);',raw.decode(),re.M|re.S):
  if typ not in seq or not re.search(r'\.\w+\s*\(',body):continue
  types[typ]+=1
  conn={p:n.strip() for p,n in re.findall(r'\.(\w+)\s*\(([^()]*)\)',body)}
  if 'u_ack' in name and ('ack_q' in name or 'reset_seen' in name):witness.append({'instance':name,'cell_type':typ,'connections':conn})
 lib_arcs={};endpoint=[]
 for corner in ['SS','FF']:
  for lib in (R/'results/arch/s81_hrow_native_placement_1013/reset_classification').glob('*_RVT_'+corner+'.lib.gz'):
   for name,body,_ in blocks(gzip.open(lib,'rt').read(),'cell'):
    if name in types:
     ffs=list(blocks(body,'ff'))+list(blocks(body,'latch'));sem={p:prop(ffs[0][1],p) for p in ['clear','preset','next_state','clocked_on']} if ffs else None
     lib_arcs[(corner,name)]={'semantics':sem,'pins':{pin:sorted({prop(t,'timing_type') for _,t,_ in blocks(bod,'timing') if prop(t,'timing_type')}) for pin,bod,_ in blocks(body,'pin')}}
 for typ,name,body in re.findall(r'^\s*(\w+)\s+(\\\S+|[\w$]+)\s+\((.*?)\);',raw.decode(),re.M|re.S):
  if typ not in types:continue
  conn={p:n.strip() for p,n in re.findall(r'\.(\w+)\s*\(([^()]*)\)',body)};sem=lib_arcs[('SS',typ)]['semantics']
  for pin,net in conn.items():
   if uses(sem['clear'],pin) or uses(sem['preset'],pin):
    endpoint.append(dict(instance=name,cell_type=typ,pin=pin,net=net,classification='actual asynchronous cell pin',sequential_semantics=sem,constraint_types={corner:lib_arcs[(corner,typ)]['pins'].get(pin,[]) for corner in ['SS','FF']},routed_SS_FF_recovery_removal=None,global_reset_driver=None))
 (out/'actual_async_cell_pins.json').write_text(json.dumps(endpoint,indent=2)+'\n')
 pins=json.loads((out/'pins.json').read_text());ack=[n for n in pins['pins'] if n=='rst_ack' or n.startswith('rst_ack[')];assert len(ack)==(7 if top=='dsfd_mtp_hrow_hub' else 1)
 resets=[p for p in spec['reset_ports'] if p in pins['pins']]
 receipt=dict(status='CTS actual ABI/geometry and synthesized mapped cells; routed SSFF/parent OPEN',gate_verdict=g['verdict'],gate_source_commit=b['start_commit'],source_binding_manifest_sha256=b['manifest_sha256'],source_archive_sha256=b['archive_sha256'],tool_image_id=image,source_snapshot_schema=b['schema'],remote_source_snapshot=run+'.source_snapshot.json',remote_netlist=net,netlist_uncompressed_sha256=hashlib.sha256(raw).hexdigest(),mapped_sequential_cells=sum(types.values()),mapped_sequential_cell_types=dict(types),mapped_ack_witness_connected_cells=witness,mapped_distinct_ack_witness_ff=len(witness),actual_async_cell_pin_count=len(endpoint),ack_pin_names=ack,actual_reset_pin_names=resets,actual_pin_receipt_sha256=hashlib.sha256((out/'pins.json').read_bytes()).hexdigest(),clock=g['clock'],actual_native_clock_source=None,actual_native_reset_source=None,actual_native_reset_phase=None,SS_FF_async_check_receipts=None,qualification='No routed or global delivery claim. ACK timing includes real combinational RN/live gating after registered witness; raw epoch reaches actual async witness cells.')
 (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');summary[kit]={k:v for k,v in receipt.items() if k not in ['mapped_ack_witness_connected_cells','clock']};summary[kit]['clock_sinks']=g['clock']['max_root_sinks']
(OUT/'cts_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({k:{'status':v['status'],'mapped_sequential_cells':v.get('mapped_sequential_cells'),'clock_sinks':v.get('clock_sinks')} for k,v in summary.items()},indent=2))
