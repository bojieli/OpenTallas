"""Read-only inventory for the current parent; absent STA evidence stays absent."""
import hashlib,json,re,sys
from pathlib import Path

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
 return h.hexdigest()
kit=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
base=kit/'run/results/asap7/kl_dsdv_bksel_q_signed_source/base'
netlist=base/'1_synth.v';text=netlist.read_text();master='ot_s81ph_native_sel_hist_bank'
instances=[]
for m in re.finditer(r'\b'+master+r'\s+(\\\S+|\w+)\s*\((.*?)\);',text,re.S):
 connections=dict(re.findall(r'\.(\w+)\s*\((.*?)\)(?:\s*,|\s*$)',m.group(2),re.S))
 instances.append({'instance':m.group(1).lstrip('\\'),'master':master,'clock_pin':'clk','clock_net':connections.get('clk','').strip(),'reset_pin':'rst_n','reset_net':connections.get('rst_n','').strip(),'named_port_count':len(connections)})
libs={c:{'path':str(kit/'macros'/f'{master}_{c}.lib'),'sha256':sha(kit/'macros'/f'{master}_{c}.lib')} for c in ['tt','ff']}
receipts=list(kit.glob('signoff/*/libraries.json'))
d={'schema':'opentallas.parent_clock_fixture_inventory.v1','scope':'READ_ONLY_SOURCE_AND_SELECTED_LIBRARIES_NOT_PARENT_STA',
   'kit':str(kit),'parent_top':'dsdv_bksel_q','mapped_netlist':{'path':str(netlist),'sha256':sha(netlist)},
   'hist_instances':instances,'selected_libraries':libs,
   'artifacts_present':{name:(base/name).is_file() for name in ['3_place.odb','3_place.def','4_cts.odb','6_final.odb']},
   'parent_sta_library_receipts':[str(p) for p in receipts],
   'parent_consumption':'SELECTED_INPUTS_ONLY_NOT_STA' if not receipts else 'RECEIPTS_REQUIRE_ACTUAL_PATH_AND_CLOCK_JOIN',
   'parent_coverage':'UNEXPANDED_CHILD_ETM',
   'missing_for_parent_path_composition':['Actual TT/FF parent consumed-library receipts','Actual child clock ITerm source/edge and early/late arrival witness','Related parent setup/hold data paths with exact interface bits and counterpart native data/clock IDs','Actual parent data slack; no inferred aggregate or CPPR credit']}
assert len(instances)==16 and all(x['clock_net']=='ck' for x in instances),'current clock connection changed'
(out/'parent_fixture.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps({'instances':len(instances),'all_clk_to_ck':True,'mapped_sha':d['mapped_netlist']['sha256'],'artifacts':d['artifacts_present'],'sta_receipts':len(receipts)}))
