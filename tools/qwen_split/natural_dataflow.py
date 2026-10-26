#!/usr/bin/env python3
"""Source-current directed traffic requirements; never invent activity or routes."""
import argparse,gzip,hashlib,json,re,subprocess
from collections import defaultdict
from pathlib import Path


def main():
 p=argparse.ArgumentParser();p.add_argument('join',type=Path);p.add_argument('out',type=Path);a=p.parse_args();d=json.loads(gzip.decompress(a.join.read_bytes())if a.join.suffix=='.gz'else a.join.read_text());a.out.mkdir(parents=True,exist_ok=True)
 assembly=[dict(name='coll_return_'+name,source=['io',port],select=None,bits=bits,sinks=[['seq','cc']],sink_select=select,provenance='qfd_native_compute_join.sv:1157 actual concatenation, IO source ports2181+; omitted from original64simplejoin list')for name,port,bits,select in [('data','out_data',512,[511,0]),('last','out_last',1,[512,512]),('rank','out_rank',3,[515,513]),('error','out_err',1,[516,516]),('valid','out_valid',1,[517,517])]]
 if d.get('directed_edges'):
  assembly=[dict(name=r['name'],source=r['source'],select=r.get('source_select'),bits=r['bits'],sinks=[r['sink']],sink_select=r.get('sink_select'),provenance='Authoritative source manifest15165619c actual concatenation')for r in d['directed_edges']if r.get('assembly')]
 data=[]
 for r in d['joins']+assembly:
  row=dict(r);row.update(active_edges_per_token=None,serialized_physical_bits_per_edge=None,source_registered_age=d.get('source_register_edges',{}).get(r['name']),actual_routed_length_um=None,actual_required_clock_phase=None,bandwidth_demand='bits × active_edges; activity/calendar required, not width alone',physical_cut=None)
  if r['name'].startswith(('su_a_','su_vm_a_')):row['structural_issue']='A-operand gateway crosses sequencer boundary on request and return; candidate extract existing function near local SU/VM'
  elif r['name'].startswith(('su_vm_','me_vm_','seq_vm_')):row['structural_issue']='Map actual address-dependent bank/rotation/dispatch producer for each scheduled read; no fixed octet-to-bank ownership; activity split by operand'
  elif r['name'].startswith(('native_kv_','vm_native_','native_vm_','native_q_')):row['structural_issue']='KV/VM ownership/commit is a real dependency; keep formatter/commit state near actual memory face and justify external return'
  elif r['name'].startswith(('coll_',)):row['structural_issue']='Collective transport has real reserved calendars, face codecs and PHY capacity; keep local ingress near source read face and clock-boundary storage'
  else:row['structural_issue']='Place by real producer-consumer dependency and measured activity; preserve source register ages'
  data.append(row)
 external_inputs=[e for e in d['external_ports']if e['direction']=='input']
 clocks=[e for e in external_inputs if (e.get('role')=='clock'if 'role'in e else re.fullmatch(r'ck(?:_.+)?|clk(?:_.+)?|.+_ck',e['port']))]
 resets=[e for e in external_inputs if (e.get('role')=='reset'if 'role'in e else e['port']in ('rst_n','rsi'))]
 incoming=[e for e in external_inputs if e not in clocks and e not in resets]
 assert sum(e['bits']for e in clocks)==sum(d['actual_clock_roots'].values()), 'Clock port types must account for actual root width' 
 constraints=dict(schema='opentallas.qwen.natural-dataflow-requirements.v1',source_join_sha256=hashlib.sha256(a.join.read_bytes()).hexdigest(),source_nodes=d['nodes'],source_clock_roots=d['actual_clock_roots'],source_root_total=sum(d['actual_clock_roots'].values()),simple_source_joins=len(d['joins']),derived_source_assembly_joins=assembly,joins=data,external_ports=d['external_ports'],unbound_external_functional_inputs=incoming,external_input_classification=dict(total_input_ports=len(external_inputs),clock_ports=len(clocks),clock_bits=sum(e['bits']for e in clocks),reset_ports=len(resets),functional_input_ports=len(incoming),legacy_ck_prefix_only_count=len([e for e in external_inputs if not e['port'].startswith('ck')and e['port']not in('rst_n','rsi')]),warning='Clock types are explicit; naive ck-prefix filtering misclassified IO clocks in earlier950snapshot'),critical_unassigned=d['critical_unassigned'],successor=dict(SU347_root_module='qfd_sp_su64_sfu_glue_entries',copy_split_already_in_source=d['actual_clock_roots']['su']==347,system_root_total=sum(d['actual_clock_roots'].values()),gateway_single_new_root_total=sum(d['actual_clock_roots'].values())+1,gateway_eight_new_root_total=sum(d['actual_clock_roots'].values())+8,status='No physical/source-current activity qualification inherited from earlier snapshots'),qualification=False,missing_for_ranking=['Actual current programme activity per join/operand/command class','Real physical child pins, homes, clocks phi-R and boundary obstructions','Per-pair critical path slack and registered ages','Native58/59 transport, KV visibility and external HOST/PHY/calendar source binding','All shared-vs-duplicated storage macro/glue/clock/area/preload costs','Physical allocated routes and all-direction cut capacity <=0.60'])
 (a.out/'directed_traffic.json').write_text(json.dumps(constraints,indent=2)+'\n')
 grouped=defaultdict(list)
 for r in data:
  for sn,sp in r['sinks']:grouped[r['source'][0],sn].append(r)
 titles={'tt':'TT controller / ME issue','seq':'Sequencer + existing A gateway','su':f'SU: eight source octets; {d["actual_clock_roots"]["su"]} roots','vm':'VM: actual bank/commit hierarchy; 488 roots','native':'Native formatter / service / ownership','embed':'Retained embedding code + scale','io':f'Collective + five faces + actual gearbox; {d["actual_clock_roots"]["io"]} roots'}
 dot=['digraph actual {','graph [rankdir=LR, bgcolor="white", label="Current actual Qwen producer→consumer graph: topology, not a physical floorplan\nSOURCE_ROOTS source roots; 64 simple + 5 IO return assembly joins; FUNC_INPUTS functional inputs unbound. Activity, real routes and cuts unmeasured.", labelloc=t, fontsize=16];','node [shape=box,style="rounded,filled",fillcolor="#e9f0f5",fontname="Arial",fontsize=11];','edge [fontname="Arial",fontsize=9,color="#526374"];']
 for n,title in titles.items():dot.append(f'{n} [label={json.dumps(title)}];')
 for (source,sink),edges in grouped.items():
  names=[f"{e['name']} {e['bits']}b"for e in edges];label='\\n'.join(names)
  color='#c86925'if any(e['name'].startswith(('su_a_','su_vm_a_'))for e in edges)else'#526374'
  dot.append(f'{source} -> {sink} [label="{label}",color="{color}"];')
 dot+=['kv [label="KV/system die + actual HBM\n583b boundary / visibility ages open",fillcolor="#fff2dc"];','fields [label="ME ROM fields / DVM / BAND trees\nactual cohort and source binding required",fillcolor="#fff2dc"];','phy [label="Licensed collective PHY1043 + SerDes\nshared capacity / clock gearbox open",fillcolor="#fff2dc"];','crom [label="Real constant/cache SRAM groups\n64 external interface ports",fillcolor="#fff2dc"];','native -> kv [style=dashed,label="actual transport/calendar joins open"];','tt -> fields [style=dashed,label="real commands / broadcasts / returned reductions"];','fields -> vm [style=dashed,label="actual ME values and memory dependencies"];','crom -> su [style=dashed,label="real per-octet constant memory; no ideal source"];','io -> phy [style=dashed,label="5 faces, shared1043 mux / fixed gearbox; not KV583"];','}']
 dot=[line.replace('SOURCE_ROOTS',str(sum(d['actual_clock_roots'].values()))).replace('FUNC_INPUTS',str(len(incoming)))for line in dot]
 (a.out/'current_flow.dot').write_text('\n'.join(dot)+'\n');subprocess.run(['dot','-Tsvg',str(a.out/'current_flow.dot'),'-o',str(a.out/'current_flow.svg')],check=True)
 proposal='''digraph proposal {
 graph [rankdir=TB,bgcolor="white",labelloc=t,label="Structural adjacency proposal from actual dataflow — no physical homes or timing qualification",fontsize=16];
 node [shape=box,style="rounded,filled",fillcolor="#e8f1f5",fontname="Arial"];
 seq [label="Shared programme / epoch / schedule\nexisting state retained"];
 emb [label="One actual retained code/scale provider\nno extra row SRAM for gateway extraction"];
 vm [label="VM striped row-bank / commit faces\n16 banks per operand; address-dependent ownership"];
 rowrouter [label="Existing coarse/fine rotation + 64-lane selection\n3×2048 output FF; source/physical partition open",fillcolor="#dedede"];
 subgraph cluster_octet { label="Repeat 8× with existing lane/reduction identities";color="#b7cdd8";
  ag [label="Extract existing local A gateway\nrequest mask / decode / return selection\nactual source state and ages required",fillcolor="#f8d8ad"];
  align [label="2 × existing 4-lane alignment leaves"];
  lanes [label="8 lane cohorts\nhead / exp / rcp / rsq / relay"];
  red [label="Existing 8-lane regional reducer\nno arithmetic reorder"];
  ag -> align [label="256b selected A / octet; activity unknown"];
  align -> lanes [label="local operand/constant returns"];
  lanes -> red [label="local reduction inputs"];
 }
 fmt [label="Actual KV/VM formatter + ownership\nnear producer/commit faces"];
 coll [label="Local collective read/landing storage\nnear actual digital transport face"];
 kv [label="KV/system HBM/head groups\ncompiler-paced acquisition / visibility"];
 phy [label="P/R shared1043 + separate SerDes faces\nreal codecs / FIFO / gearboxes / clocks"];
 seq -> lanes [label="existing instruction / metadata distribution"];
 seq -> ag [label="existing control/epoch state only"];
 emb -> ag [label="512b code + 16b scale; shared code / local decode"];
 ag -> vm [label="200b A mask/address per octet"];
 vm -> rowrouter [label="actual selected rows / phases; address-dependent"];
 rowrouter -> ag [label="256b selected A / octet; no fixed bank owner"];
 rowrouter -> align [label="512b selected B/C / octet"];
 lanes -> fmt [label="456b KV writes / octet; 3648b total"];
 vm -> fmt [label="524b Q + 975b commit + status"];
 fmt -> vm [label="actual committed write/epoch"];
 fmt -> kv [label="long external path justified by actual transfer ownership"];
 seq -> coll [label="compiled command / payload source ownership"];
 vm -> coll [style=dashed,label="evaluate local read/copy dispatch; preserve source calendar"];
 coll -> phy [label="actual five-face reserved slots;1043b shared PHY"];
}
'''
 (a.out/'proposed_adjacencies.dot').write_text(proposal);subprocess.run(['dot','-Tsvg',str(a.out/'proposed_adjacencies.dot'),'-o',str(a.out/'proposed_adjacencies.svg')],check=True)
 print(json.dumps(dict(joins=len(data),actual_source_roots=constraints['source_root_total'],unbound_external_functional_inputs=len(incoming),ranked=False)))
if __name__=='__main__':main()
