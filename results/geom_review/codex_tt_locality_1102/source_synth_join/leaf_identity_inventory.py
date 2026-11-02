"""Read-only actual133 leaf identity/pin/Liberty join; no initial-state/equivalence claim."""
from pathlib import Path
import json,sys,hashlib
P=Path('/work/producer');sys.path.insert(0,str(P/'tools/die_plan/tt_regional_origin'))
from native_inventory import L
x=json.loads((P/'residual_anonymous_cone.json').read_text())
def leaves(e):
 if e[0] in ('ff_output','macro_output','port','const','internal_state'):return {tuple(e)}
 if e[0] in ('and','or'):return set().union(*(leaves(z) for z in e[1]))
 return set().union(*(leaves(z) for z in e[1:]))
a,b=leaves(x['old_ast']),leaves(x['new_ast'])
if a!=b or len(a)!=133 or any(z[0]!='ff_output' or z[1].startswith('_') for z in a):raise ValueError('Residual leaf interface is not the actual133 literal named FF outputs')
names={z[1] for z in a}
def stream(path):
 cells={};pins={}
 with open(path) as f:
  for line in f:
   z=line.rstrip('\n').split('\t')
   if len(z)>1 and z[1] in names:
    if z[0]=='CELL':cells[z[1]]=dict(master=z[2],width_um=float(z[3]),height_um=float(z[4]))
    elif z[0]=='PIN':pins.setdefault(z[1],{})[z[2]]=dict(direction=z[3],signal=z[4],net=z[5])
 if set(cells)!=names or set(pins)!=names:raise ValueError('Missing actual literal named leaf')
 return cells,pins
oc,op=stream('/old/actual_old_reference.tsv');nc,np=stream(P/'actual_synth.tsv');readset=json.loads((P/'actual_source_readset.json').read_text());libs=[Path(p) for p in readset['inputs'] if '.lib' in p];models=L.read_liberty(libs);rows=[]
for n in sorted(names):
 om,nm=models[oc[n]['master']],models[nc[n]['master']]
 if not om.get('ff') or om['ff']!=nm.get('ff'):raise ValueError('Actual leaf FF transition primitive differs')
 cp=om['ff']['clocked_on']
 if cp!='CLK' or op[n][cp]['net']!='clk' or np[n][cp]['net']!='clk':raise ValueError('Actual leaf clock/root differs')
 if om['ff'].get('clear') or om['ff'].get('preset'):raise ValueError('Unmodeled asynchronous leaf control')
 outputs={p:q.get('function') for p,q in om['pins'].items() if q.get('direction')=='output'}
 if outputs!={p:q.get('function') for p,q in nm['pins'].items() if q.get('direction')=='output'}:raise ValueError('Actual state-output polarity differs')
 rows.append(dict(name=n,old_cell=oc[n],fresh_cell=nc[n],ff_primitive=om['ff'],output_functions=outputs,old_pins=op[n],fresh_pins=np[n],reset_enable_context='D-encoded; same selected frozen RTL, no reset/enable/initial constraint added',initial_relation='UNPROVED: no initial value or None/None comparison accepted'))
sha=readset['inputs']['/work/rtl/qfd_dv_typed_witness_control_frozen.sv']
expected='737c772b892baf869ed19a58665d7792ef3a0281d82632a053f35af8fc0afac7'
if sha!=expected:raise ValueError('Selected frozen control source changed from exact old kit')
result=dict(status='PASS_STATIC_LEAF_PIN_SOURCE_JOIN_ONLY',old_source_host='intel2',old_source='/srv/opentallas-scratch2/claude/die-qc-61/tt_ctlm_C/gen/tt_ctlm/rtl/qfd_dv_typed_witness_control_frozen.sv',old_source_sha256=expected,new_source_sha256=sha,leaf_count=133,rows=rows,anonymous_alias_dependencies=0,all_leaf_bits_free_in_proposed_comb_miter=True,native_base_proved=False,leaf_initial_values_constrained=False,accepted_anonymous_alias=False,physical_release=False,whole_source_credit=False)
(P/'residual_leaf_identity_inventory.json').write_text(json.dumps(result,indent=1)+'\n');print('RESIDUAL_LEAF_STATIC_JOIN133 literal FFs; explicit actual CLK/FF/Q functions; BASE unproved',flush=True)
