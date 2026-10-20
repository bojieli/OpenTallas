#!/usr/bin/env python3
"""Inventory logical landing families and immutable-LEF coordinate phases.
No synthesis, simulation, macro edit, storage waiver, or gate is performed.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(ROOT/'tools/landed_parent'))
import check_macro_track_alignment as C
import lp
OUT=ROOT/'results/arch/kv_ahub6_1020'
record=json.loads((OUT/'qkd_ahub_static_dw_g6_lp_record.json').read_text())
spec=json.loads((ROOT/'physical/ref_tile/qkd_ahub_g6a/spec.json').read_text())
rtl=(ROOT/spec['sources'][0]).read_text()
mod=lp.parse_module(lp.preprocess(rtl,[]),spec['top'])
_,_,instances=lp.parse_body(mod['body']);instances={i['inst']:i for i in instances}
rows=[];families={}
for l in record['landings']:
 w=l['width'];chunks=(w+1)//2
 row=dict(name=l['name'],net=l['net'],writer_clock='ck_'+l['src_region'],reader_clock='ck_'+l['dst_region'],
          W=w,D=record['D'],K=record['K'],ring_payload_bits=w*record['D'],reader_output_bits=w,
          physical_chunks=chunks,physical_metadata_FFs=33*chunks,
          physical_epoch_history_bits=12*chunks,physical_valid_history_bits=4*chunks,
          write_ports=1,read_ports=1,read_policy='one selected history slot each reader edge; other slots not concurrently computed',
          write_policy='one rotating slot written on every released writer edge',
          source_nodes=l['src_nodes'],consumer_pins=l['readers'],parallel_compute_exception=False)
 rows.append(row)
 key='ck_'+l['src_region']
 f=families.setdefault(key,dict(writer_clock=key,depth=4,slot_policy='identical rotating wc/write_oh phase after same-depth reset',landings=[],
                                width_bits=0,ring_payload_bits=0,reader_roots=[],parallel_compute_exception=False))
 f['landings'].append(l['name']);f['width_bits']+=w;f['ring_payload_bits']+=4*w;f['reader_roots'].append(row['reader_clock'])
 f['physical_epoch_history_bits']=f.get('physical_epoch_history_bits',0)+12*chunks
 f['physical_valid_history_bits']=f.get('physical_valid_history_bits',0)+4*chunks
for f in families.values():
 f['reader_roots']=sorted(set(f['reader_roots']));f['concurrent_reader_clocks']=len(f['reader_roots'])
 f['physical_payload_plus_history_bits']=f['ring_payload_bits']+f['physical_epoch_history_bits']+f['physical_valid_history_bits']
 f['storage_status']='HOLD_NEEDS_REAL_SRAM_BACKEND' if f['ring_payload_bits']>2048 else 'UNDER_2KB_PAYLOAD_FAMILY'
summary=dict(schema='opentallas.ahub6.logical_storage_audit.v1',source_sha256=hashlib.sha256(rtl.encode()).hexdigest(),
             status='HOLD',reason='core-c D4 logical history family5444bits exceeds2kb; two-bit implementation chunks are not an exemption',
             totals=dict(payload_ring_bits=sum(r['ring_payload_bits'] for r in rows),reader_output_bits=sum(r['W'] for r in rows),
                         physical_metadata_FFs=sum(r['physical_metadata_FFs'] for r in rows),
                         physical_epoch_history_bits=sum(r['physical_epoch_history_bits'] for r in rows),
                         physical_valid_history_bits=sum(r['physical_valid_history_bits'] for r in rows)),
             landings=rows,families=list(families.values()),
             other_parent_state={'core_lm_data_bits':512,'core_seen_bits':512,'role':'independent core scoreboard/capture state, not a landing-ring partition'},
             macro_children='Existing four Z children and reciprocal are separate immutable hard views; their storage is not reclassified as parent soft FFs')
(OUT/'logical_storage_audit.json').write_text(json.dumps(summary,indent=1)+'\n')
phase=[]
for child in spec['children']:
 view=ROOT/child['view'];lef=next(view.glob('*.lef'));raw=lef.read_bytes();macro=C.parse_lef(raw.decode())[0]
 x,y=[round(v*1000) for v in child['at']];old=child.get('orient','R0');new='R0'
 before=C.check_placement(macro,old,x,y);after=C.check_placement(macro,new,x,y)
 pincoords=[]
 for pin in macro['pins']:
  if pin['use'] in ('POWER','GROUND'):continue
  for layer,rect in pin['rects']:
   a=C.transform_rect(rect,old,macro['W'],macro['H']);b=C.transform_rect(rect,new,macro['W'],macro['H'])
   pincoords.append(dict(pin=pin['name'],layer=layer,
                        old_global_rect_nm=[a[0]+x,a[1]+y,a[2]+x,a[3]+y],
                        proposed_global_rect_nm=[b[0]+x,b[1]+y,b[2]+x,b[3]+y]))
 phase.append(dict(instance=child['inst'],lef=str(lef.relative_to(ROOT)),lef_sha256=hashlib.sha256(raw).hexdigest(),
                   original_requested_origin_um=child['at'],proposed_origin_um=child['at'],
                   actual_lattice_43p2=all(v%43200==0 for v in (x,y)),old_orientation=old,proposed_orientation=new,
                   logical_connection_map=instances[child['inst']]['conns'],old_pin_track_audit=before,
                   proposed_pin_track_audit=after,pin_coordinate_changes=pincoords))
assert all(p['actual_lattice_43p2'] and sum(v['offtrack'] for v in p['proposed_pin_track_audit']['layers'].values())==0 for p in phase)
(OUT/'r0_lattice_proposal.json').write_text(json.dumps(dict(status='PROPOSAL_NOT_APPLIED',macro_abstracts_unchanged=True,
     warning_cause='MX/MY flip the original12nm preferred-track residue to36nm; inherited generator shifts placement24nm to compensate. R0 uses actual43.2*k origins without changing any LEF pin shape.',
     instances=phase),indent=1)+'\n')
lines=['# AHUB6 semantic storage HOLD','',summary['reason'],'',
       '|Landing|Net|Writer→reader clock|W|D|Payload history bits|Read/write ports|Role|',
       '|---|---|---|---:|---:|---:|---|---|']
for r in rows:lines.append(f"|{r['name']}|{r['net']}|{r['writer_clock']}→{r['reader_clock']}|{r['W']}|4|{r['ring_payload_bits']}|1R/1W|Selected history; no parallel-compute exemption|")
lines+=['','|Logical writer family|W total|Payload history|Epoch history|Valid history|Physical history total|Reader roots|Verdict|','|---|---:|---:|---:|---:|---:|---:|---|']
for f in families.values():lines.append(f"|{f['writer_clock']}|{f['width_bits']}|{f['ring_payload_bits']}|{f['physical_epoch_history_bits']}|{f['physical_valid_history_bits']}|{f['physical_payload_plus_history_bits']}|{f['concurrent_reader_clocks']}|{f['storage_status']}|")
lines+=['','The 903 two-bit implementation chunks do not change these logical families. The 7220 payload-ring FF bits plus1805 reader output bits and29799 replicated metadata FFs give38824 mapped landing FFs. Replicated epoch/valid arrays are also indexed history and remain subject to storage audit:10836 epoch bits and3612 valid bits, including ck_c8172 epoch+2724 valid bits. Physical ck_c payload+epoch+valid history is16340bits. A real backend must also replace this metadata history or prove/remap redundant metadata; none is automatically exempt because it is duplicated. None of this inventory grants a storage exemption.',
        '', 'The core-c family requires a real SRAM backend or a reviewed architecture change. It has six simultaneous related-root reader domains (w,e,z0..z3). A single1R SRAM cannot serve six independent read clocks by assertion; a banked real macro solution must bind ports/clocks and prove the unchanged D4/K2 edge/reset behavior. An existing software/model backend is insufficient.',
        '', 'The R0 lattice proposal preserves exact immutable LEF bytes, bbox origins and logical pin→net mappings. It physically reorients three children and therefore changes their actual global pin rectangles, all recorded in r0_lattice_proposal.json. It does not cosmetically edit an abstract. The proposal is not applied to a kit and no gate is authorized.',
        '', 'Named mapped-band densities: c15511.662/48288.96=32.12%; w1564.624/6894.72=22.69%; e1038.038/6428.16=16.15%; each Z1504.773/6531.84=23.04%. Unnamed logic742.545um2 is unallocated at source; putting all in c raises its conservative source density to33.66%. Post-CTS/repair actual fence fill remains unmeasured.']
(OUT/'SEMANTIC_AUDIT.md').write_text('\n'.join(lines)+'\n')
print(summary['totals']);print([(f['writer_clock'],f['ring_payload_bits'],f['storage_status']) for f in families.values()])
print([(p['instance'],p['old_orientation'],sum(v['offtrack'] for v in p['old_pin_track_audit']['layers'].values()),sum(v['offtrack'] for v in p['proposed_pin_track_audit']['layers'].values())) for p in phase])
