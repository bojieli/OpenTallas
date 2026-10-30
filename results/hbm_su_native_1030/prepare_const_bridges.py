"""Explicit native-parent constant-output bridges for three physical-only SU masters."""
import copy,json,pathlib,re,sys
from pin_plan import ROOT,ports
HERE=pathlib.Path(__file__).parent;BASE=ROOT/'physical/die_plan/hbm_arch_cores';N=json.load(open(HERE/'nocoll_receipt.json'));maps=json.load(open(HERE/'native112_plan_map.json'));receipts=[]
for row in N['rows']:
 full=row['full_native_proof_adapter'];top=row['native_cut'];physical=row['physical_module'];bridge=physical+'__native_bridge';P=ports(top)
 text='`timescale 1ns/1ps\n`default_nettype none\n// Unbound SOURCE PREP native-parent bridge. Physical macro has no constant collision pins.\n// Synthesis maps this explicit native logical0 to parent TIE0; parent physical binding remains required.\nmodule '+bridge+'(\n'+',\n'.join(' '+d+' wire '+(f'[{w-1}:0] 'if w>1 else'')+n for d,n,w in P)+'\n);\n assign lane_coll = 4\'b0000;\n '+physical+' u_phys(\n'+',\n'.join('  .'+('strap_lane_lane_id'if n=='lane_lane_id'else n)+'('+n+')'for d,n,w in P if n!='lane_coll')+'\n );\nendmodule\n`default_nettype wire\n';p=BASE/'wrappers'/(bridge+'.sv');p.write_text(text)
 # All nonconstant boundary wiring is direct and exact, independent of data/state values.
 b=dict(re.findall(r'\.(\w+)\((\w+)\)',text));expected={('strap_lane_lane_id'if n=='lane_lane_id'else n):n for d,n,w in P if n!='lane_coll'};assert b==expected
 assert "assign lane_coll = 4'b0000;"in text and 'lane_coll('not in text
 mutant=text.replace("assign lane_coll = 4'b0000;","assign lane_coll = 4'b0001;");assert "assign lane_coll = 4'b0000;"not in mutant
 receipts.append(dict(native_cut=top,full_proof_adapter=full,physical=physical,parent_bridge=bridge,bridge_source=str(p.relative_to(ROOT)),logical_outputs=1540,physical_output_bits=1536,native_lane_coll_TIE0_bits=4,direct_wiring_bits=sum(w for d,n,w in P if n!='lane_coll'),wrong_TIE1_mutant_rejected=True))
for r in maps['rows']:
 if r['native_module']=='ot_hnx_su_exp__rst3':continue
 old=r['physical_descriptor']['module']
 if '7dd6'in r['native_module']:full='ot_hnx_su_plain4__7dd6a1bbbf47_rst3__id44'
 else:full=old
 row=next(x for x in N['rows']if x['full_native_proof_adapter']==full);bridge=next(x for x in receipts if x['full_proof_adapter']==full)
 r['physical_source_PREP']=dict(module=row['physical_module'],pins_source=row['pin_file'],pins_sha256=row['pins_sha256'],parent_bridge=bridge['parent_bridge'],parent_native_path=r['native_path'],physical_child_native_path=r['native_path']+'.u_phys',explicit_native_TIE0={'lane_coll':{'width':4,'value':0}},physical_leaf_mapping_requires_parent_event=True)
assert sum('physical_source_PREP'in r for r in maps['rows'])==48
(HERE/'native112_plan_map.json').write_text(json.dumps(maps,indent=1)+'\n');(HERE/'constant_bridge_receipt.json').write_text(json.dumps(dict(status='SOURCE_ONLY_UNBOUND_PARENT_BRIDGE_PREP',bridges=receipts,actual_native_cuts=48,native_TIE0_outputs=192,constant_induction='KIND0: c1=0,c4=0, coll=c1|c4; r_coll reset0 andnext0 =>nativecoll0 aftertruePOR for everyinputhistory. No physicalconstantpin/exemption.',remaining='Parent chooses exact inline or u_phys hierarchy mapping, applies privatepin/ID/TIE0 event andnativebinding gates; noPNR'),indent=1)+'\n');print('PREP3native bridges for48cuts/192logicalTIE0 outputs;112cutmapcomplete')
