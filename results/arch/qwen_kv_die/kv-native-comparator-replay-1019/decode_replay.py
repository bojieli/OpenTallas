"""Decode preserved WaveJSON; this script never runs a proof or changes a property."""
import collections, hashlib, json, pathlib, re
p=pathlib.Path(__file__).resolve().parent
raw=(p/'replay_cex.json').read_text()
normalized=re.sub(r'"name": "([^"\n]*)"',lambda m:'"name": '+json.dumps(m[1]),raw)
(p/'name_only_normalized_replay.json').write_text(normalized)
def decode(s):
    vals=[];di=0;v=None
    for i,c in enumerate(s['wave']):
        if c=='=':v=s['data'][di];di+=1
        elif c in '01xz':v=c
        elif c=='4':
            v=None
            if s.get('data'):assert s['data'][di]=='';di+=1
        elif c!='.':raise ValueError(c)
        if i:vals.append(v)
    assert di==len(s.get('data',[])) and len(vals)==10
    return vals
s={x['name']:decode(x) for x in json.loads(normalized)['signal']}
cs={n:v for n,v in s.items() if n.startswith('cmp_')}
assert len(cs)==10993
meta={n:v for n,v in cs.items() if n.startswith('cmp_S__proof_meta_')}
assert len(meta)==95 and all(v[6:]==['1']*4 for v in meta.values())
bad={str(t+1):[n for n,v in cs.items() if v[t]=='0'] for t in range(10)}
assert len(bad['7'])==213 and all(not bad[str(t)] for t in [8,9,10])
assert all(re.fullmatch(r'cmp_S__g_n_[0-7]__u_a_u_cc_g_r_r_\d+_',n) for n in bad['7'])
trace=[]
for step,name in [(7,'u_cc_g_r_r_64_'),(6,'s2_code_31_'),(5,'u_cd_g_r_r_101_'),(4,'u_cb_g_r_r_95_'),(3,'s1_code_31_'),(2,'u_ca_g_r_r_114_')]:
    n='S__g_n_7__u_a_'+name;g=s[n][step-1];c=cs['cmp_'+n][step-1]
    assert g=='0' and c=='0'
    trace.append(dict(step=step,comparison='cmp_'+n,gold=g,gate='1',gate_derivation='Scalar equality=0 and gold=0 imply gate=1'))
summary={'raw_sha256':hashlib.sha256(raw.encode()).hexdigest(),'signal_count':len(s),'comparison_count':len(cs),'original_comparison_count':10898,'metadata_comparisons':95,'all_380_checked_metadata_comparisons_equal':True,'checked_steps':[7,8,9,10],'checked_mismatch_counts':{k:len(bad[k]) for k in ['7','8','9','10']},'trigger':s['trigger'],'all_mismatches_by_step':bad,'concrete_old_data_trace':trace,'reset_at_first_checked_mismatch':{n:v[6] for n,v in s.items() if n=='rst_n' or n.startswith('S__u_rr_rst_n_')},'interpretation':'Valid completion of retained witness; unspecified x/blank remained free. No claim of unique original failing comparator. All213 mismatches are simultaneous at first checked step7; representative path chosen, no arbitrary ordering claimed. Low valid does not waive predicate; step8 convergence does not revise reset assumptions or qualify physical reset.'}
(p/'decoded_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(p/'decoded_replay_signals.json').write_text(json.dumps(s,indent=2)+'\n')
print('10993 flags decoded; step7 original data mismatches213; steps8-10 mismatches0; metadata380/380 equal.')
