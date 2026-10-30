#!/usr/bin/env python3
"""Exact bit-cone diagnosis, NOT full core equivalence or observable refinement."""
import collections,hashlib,itertools,json,pathlib,re
R=pathlib.Path(__file__).resolve().parents[3]
S=R/'physical/die_plan/hbm_arch_cores/native_1030'
src=(S/'ot_hdc_v41x_exp.sv').read_text()
rows=re.findall(r"8'd(\d+)\s*:\s*ln2_nk\s*=\s*\{32'h([0-9a-fA-F]+),\s*32'h([0-9a-fA-F]+)\}",src)
values={int(n):int(lo,16) for n,hi,lo in rows};assert len(values)==254
assert all((v>>30)&1==0 for v in values.values())
assert 'default: ln2_nk = 64\'d0' in src
assert '.D(LA)) d_lo' in src and 'r1, {~lo_d[31], lo_d[30:0]}' in src
# The source cone contains six unreset states: a_lo30, line30/62/94/126, rd71.
# b_exp7 = b_field7 = b30, including the zero-field exponent substitution (8'd1 has top bit0).
assert all((((f if f else 1)>>7)&1)==((f>>7)&1) for f in range(256))
traces=[]
for init in itertools.product((0,1),repeat=6):
 state=list(init);trace=[state[:]]
 for edge in range(1,8):state=[0]+state[:-1];trace.append(state[:])
 traces.append(trace)
settled={name:next(e for e in range(8)if all(t[e][i]==0 for t in traces))for i,name in enumerate(['a_lo30','line30','line62','line94','line126','rd71'])}
assert settled['line126']==5 and settled['rd71']==6
j=json.load(open(pathlib.Path(__file__).with_name('original_lec.json')))
assert len(j['failing'])==54 and all(x['point'].startswith('ff:')for x in j['failing'])
report=dict(scope='SOURCE_BIT_CONE_DIAGNOSIS_ONLY_NO_FULLCORE_EQ_OR_OUTPUT_REFINEMENT',source_hashes={n:hashlib.sha256((S/n).read_bytes()).hexdigest()for n in ['ot_hdc_v41x_exp.sv','ot_hdc_delay.sv','ot_hdc_fp32_add_lat.sv','ot_hdc_w11_cut.sv']},lut_explicit_rows=len(values),lut_domain=256,lut_default0=True,bit30_all_inputs0=True,all64_symbolic_initial_assignments_enumerated=True,settles_after_edges=settled,counterexample_initial_all1=traces[-1],native_reset_edges=j['reset_contract']['used'],failing_points=54,physical_PO_failures=0,internal_FF_failures=54,outer_kept_registers=j['kept_registers'],cone_missing_counts=dict(collections.Counter(k for x in j['failing']for k in x['cone_unmatched_keys'])),next='Preserve exact native startup FFs through synthesis with narrow early KEEP; no reset extension or dropped proof points. Native observable refinement not established.')
pathlib.Path(__file__).with_name('bit_cone_receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in ['scope','settles_after_edges','physical_PO_failures','internal_FF_failures']}))
