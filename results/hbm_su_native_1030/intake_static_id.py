"""Prepare opt-in physical source variants after actual-ID mechanism proof; no plan adoption."""
import hashlib,json,pathlib,shutil
from pin_plan import M,PACK,ROOT
HERE=pathlib.Path(__file__).parent;BASE=ROOT/'physical/die_plan/hbm_arch_cores';OUT=BASE/'id_1030';OUT.mkdir(exist_ok=True)
C=json.load(open(HERE/'static_id/lockstep_results.json'));S=json.load(open(HERE/'static_id/special_lockstep_results.json'));assert C['status']==S['status']=='PASS';assert len(C['bindings'])==240 and len(S['bindings'])==16
masters=dict(M);top_special='ot_hnx_su_plain4__7dd6a1bbbf47_rst3';masters[top_special+'__id44']=top_special
rows=[]
for p in (HERE/'static_id').glob('*__static_id.sv'):
 shutil.copy(p,OUT/p.name)
# Identity-only pinreg variant is invertibly related to raw actual native body.
pin=(OUT/'ot_hbm_su_static_lane_pinreg__static_id.sv').read_text();raw=(PACK/'ot_hbm_su_static_lane_pinreg.sv').read_text()
reverse=pin.replace('module ot_hbm_su_static_lane_pinreg__static_id #(\n    parameter integer STATIC_LANE_ID = 0,','module ot_hbm_su_static_lane_pinreg #(').replace("d_in = {(STATIC_LANE_ID != 0) ? 11'd0 : lane_id,",'d_in = {lane_id,').replace('wire [10:0] q_captured_id;\n    assign q_lane_id = (STATIC_LANE_ID != 0) ? lane_id : q_captured_id;\n    assign {q_captured_id, q_ld_c,','assign {q_lane_id, q_ld_c,')
assert reverse==raw
R=json.load(open(BASE/'recipes_b2.json'))
for physical,top in masters.items():
 p=BASE/'wrappers'/(physical+'.sv');s=p.read_text();original=top+' u_native(';variant=top+'__static_id #(.STATIC_LANE_ID(1)) u_native('
 if variant in s:baseline=s.replace(variant,original)
 else:assert s.count(original)==1;baseline=s;s=s.replace(original,variant);p.write_text(s)
 assert s.replace(variant,original)==baseline
 v=(OUT/(top+'__static_id.sv')).read_text();gold=(PACK/(top+'.sv')).read_text()
 rev=v.replace('module '+top+'__static_id #(parameter integer STATIC_LANE_ID=0) (','module '+top+' (').replace('ot_hbm_su_static_lane_pinreg__static_id #(.STATIC_LANE_ID(STATIC_LANE_ID), ','ot_hbm_su_static_lane_pinreg #(').replace('.read_return()','.read_return({})');assert rev==gold
 rec=R[physical];files=[]
 for source in rec['files']:
  name=pathlib.Path(source).name
  if name=='ot_hbm_su_static_lane_pinreg.sv':source='physical/die_plan/hbm_arch_cores/id_1030/ot_hbm_su_static_lane_pinreg__static_id.sv'
  elif name in(top+'.sv',top+'__synth.sv'):source='physical/die_plan/hbm_arch_cores/id_1030/'+top+'__static_id.sv'
  files.append(source)
 rec['files']=files;rec['top']=top+'__static_id';rec['params']={'STATIC_LANE_ID':1};rec['source']+=' | SOURCE PREP opt-in STATIC_LANE_ID1 proven on all256 current native IDs fromPOR/edge1/coldwarm reset with315output 4-state lockstep andwrongID mutants. Native source default0 unchanged; typed ID bits only bypass packed capture. Parentplan/calendar/nativeLEC/physical gates remain held.'
 rows.append(dict(module=physical,native=top,variant=top+'__static_id',STATIC_LANE_ID=1,wrapper_port_wiring_unchanged=True,native_cut_other_logic_byteidentical=True,native_raw_sha256=hashlib.sha256(gold.encode()).hexdigest()))
(BASE/'recipes_b2.json').write_text(json.dumps(R,indent=1)+'\n')
(HERE/'static_id_intake_receipt.json').write_text(json.dumps(dict(status='SOURCE_VARIANT_PREP_PROVEN_MECHANISM_NO_PLAN_ADOPTION',native_default_STATIC_LANE_ID=0,canonical_bound_IDs=240,special_bound_IDs=16,unique_cases=len(C['results'])+len(S['results']),all315outputs_no_masks=True,pinreg_identity_delta='Mode1 places literal zero in only11 packed ID bits and drives q_lane_id directly; no source ID capture remains. All other input/output registers and native lane body unchanged.',native_cut_and_outer_adapter_reversible_source_proof=rows,holds=['Full actual-native core synthesis LEC at bound IDs before PNR','Parent pinplan/stations/clock/IDTIE and batched root review','Physical face-shell cycles separately priced before adoption']),indent=1)+'\n');print('PREP5physicalsourcevariants,256actualIDbindings128uniquecases;no planadoption')
