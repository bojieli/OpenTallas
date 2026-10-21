from pathlib import Path
import json,subprocess,re,hashlib
w=Path('/home/ubuntu/wt/codex-smh-r5-reset-1340-1021');out=w/'results/arch/hbm_smh_r5_reset_1021/clock_target_model';out.mkdir(exist_ok=True)
def blob(p):return subprocess.check_output(['git','-C',str(w),'show','27cecb44b:'+p])
def group(s,start):
 i=s.index('{',start);depth=1;j=i+1
 while depth:
  if s[j]=='{':depth+=1
  elif s[j]=='}':depth-=1
  j+=1
 return s[i+1:j-1]
rows=[];bindings=json.loads((w/'results/arch/hbm_smh_r5_reset_1021/qualified_hard_lib_binding.json').read_text())['sources']
for b in bindings:
 p=b['path'];raw=blob(p);assert hashlib.sha256(raw).hexdigest()==b['actual_native_sha256'];s=raw.decode();clock=group(s,re.search(r'pin\s*\(\s*"?clk"?\s*\)',s).start());vals={}
 for ty in ['min','max']:
  x=re.search(r'timing_type\s*:\s*'+ty+r'_clock_tree_path\s*;',clock);tail=clock[x.end():];v=re.findall(r'values\s*\(\s*"([0-9.]+)"\s*\)',tail);assert len(v)>=2
  vals[ty+'_rise_ps']=float(v[0]);vals[ty+'_fall_ps']=float(v[1])
 corner='tt' if p.endswith('_tt.lib') else 'ff';ins=json.loads(blob(str(Path(p).parent/'insertion.json')));bound=ins[corner].get('child_flop',{}).get('boundary',ins[corner]['boundary']);allref=ins[corner].get('child_flop',{}).get('all',ins[corner]['all']);target=(vals['max_rise_ps']+vals['max_fall_ps'])/2
 rows.append(dict(path=p,sha256=b['actual_native_sha256'],master=Path(p).name.removesuffix('_'+corner+'.lib'),corner=corner,clock_pin='clk',**vals,generic_CTS_max_average_ps=target,r4_spine_max_rise_target_ps=vals['max_rise_ps'],exported_boundary=bound,exported_all=allref,ideal_full_Lib_balance_boundary_relative_to_glue_ps=[bound['min']-target,bound['max']-target],centred_boundary_target_ps=(bound['min']+bound['max'])/2))
lookup={(r['master'],r['corner']):r for r in rows};delta=json.loads((w/'results/arch/hbm_smh_r5_reset_1021/clock_topology_delta.json').read_text());regions={}
for form,f in delta['forms'].items():
 spec=json.loads((w/f'physical/ref_tile/smh_rp5{form}/spec.json').read_text());byinst={x['inst']:Path(x['view']).name for x in spec['children']};regions[form]={}
 for region,kids in f['real_hard_children_by_region'].items():
  regions[form][region]={}
  for corner in ['tt','ff']:
   selected=[lookup[byinst[k],corner] for k in kids];lo=min([0.]+[r['ideal_full_Lib_balance_boundary_relative_to_glue_ps'][0] for r in selected]);hi=max([0.]+[r['ideal_full_Lib_balance_boundary_relative_to_glue_ps'][1] for r in selected]);centerhalf=max([(r['exported_boundary']['max']-r['exported_boundary']['min'])/2 for r in selected]+[0])
   regions[form][region][corner]=dict(real_hard_instances=kids,glue_reference_target_ps=0,ideal_Lib_balance_envelope_ps=[lo,hi],ideal_Lib_balance_span_ps=hi-lo,centred_boundary_ideal_envelope_ps=[-centerhalf,centerhalf],centred_boundary_ideal_span_ps=2*centerhalf)
r=dict(grade='PINNED_CTS_TARGET_MODEL_NOT_ACTUAL_R5_CLOCK_PROOF',source_commit='27cecb44b',pinned_OpenROAD='26Q3-1510-g6cb3f2b704',all14_actual_Lib_targets=rows,regions=regions,derate=dict(config_argument=0.75,actual_semantics_in_this_revision='Stored/reported/reset but NO operational C++ consumer. Neither macro insertion nor residual buffer delay is multiplied by this argument in the pinned CTS source.',source_inventory='25 files in exact src/cts/src; getDelayBufferDerate references are its CtsOptions getter plus SWIG reporting getter only; no operational C++ callsite.',computeInsertionDelay='Uses unscaled arithmetic average of max-clocktree rise/fall delay, converts to equivalent length for HTree.',LatencyBalancer='Uses actual rising/max parent clock arrival plus unscaled max-rise/fall average for hard sinks; worst=max(arrival+insertion). For a residual Δ=worst-nodearrival computes floor(Δ/bufferDelay), estimates added wirecap from source/sink spacing, recomputes bufferDelay and floor(Δ/newDelay), inserts differences across children. No0.75 factor.'),limitations=['Region envelope is ideal FULL per-leaf Liberty target equalization including glue; an algebraic diagnostic, NOT measured skew or a physical lowerbound. Real HTree grouping/geometry/quantization/resizer may change node arrival.','TT and FF ideal envelopes are independently normalized by their own libraries, NOT one physical tree passing two corners.','Raw376-vs288 difference is NOT asserted as effective88ps physical skew. Actual parent delivery and ALLexportedboundaryrefs remain mandatory.','Leaf internal allspan/STA qualification retained explicitly; no new internal<=80 rule, no Liberty/SDC/reference edits.'],disposition='MAIN X/M and FB X/C have poor ideal Lib-target boundary margins; need a credible boundary-aware structural clock target/delivery plan or actual source-bound justification before four gates. No gate launch authorized by this model.')
(out/'model.json').write_text(json.dumps(r,indent=2)+'\n')
manifest=json.loads(Path('/home/ubuntu/scratch/codex-smh-r5-clock-delta-1021/pinned_cts/manifest.json').read_text());(out/'pinned_cts_source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(out/'target_model.py').write_text(Path(__file__).read_text());print('ALL14_TARGETS_BOUND',len(rows));print(json.dumps(regions,indent=1))
