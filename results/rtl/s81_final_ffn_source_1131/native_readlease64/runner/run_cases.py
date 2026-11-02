from pathlib import Path
import json,re,subprocess
R=Path('.');records={}
def run(issue,mutant=False):
 name=('mut_payload_' if mutant else 'issue_')+str(issue)
 with (R/(name+'.log')).open('w') as f:p=subprocess.run(['obj/Vtb_current_native_leaf','+ISSUE='+str(issue),*(['+mut_payload'] if mutant else [])],stdout=f,stderr=subprocess.STDOUT)
 text=(R/(name+'.log')).read_text();match=re.search(r'LEASE_RESULT (.*) clock833',text);assert match,(name,p.returncode)
 fields={k:int(v) for k,v in re.findall(r'([a-z]+)(-?\d+)',match[1])}
 fields['returncode']=p.returncode;fields['qualified']=('NATIVE_READ_LEASE_PASS' in text and p.returncode==0)
 fields['read_events']=[dict(bank=int(b),edge=int(e),row=int(a)) for b,e,a in re.findall(r'^READ bank(\d) edge(\d+) row(\d+)',text,re.M)]
 fields['native_publication_edges']=[int(e) for e in re.findall(r'^LO_NATIVE edge(\d+)',text,re.M)]
 fields['public_publication_edges']=[int(e) for e in re.findall(r'^LO_PUBLIC edge(\d+)',text,re.M)]
 fields['physical_same_address_read_write_qualified']=False
 records[name]=fields;(R/'cases.json').write_text(json.dumps(records,indent=2)+'\n');return fields
safe=run(31);assert safe['qualified'] and not safe['collisions']
early=run(0);assert not early['qualified'] and early['stale']>0
lo,hi=0,31
while hi-lo>1:
 mid=(lo+hi)//2;r=run(mid)
 if r['qualified']:hi=mid
 else:lo=mid
safe=records['issue_'+str(hi)];previous=records['issue_'+str(lo)]
assert safe['qualified'] and not safe['collisions'] and not previous['qualified']
fault=run(31,True);assert not fault['qualified'] and fault['errors']>0
assert safe['reads']==16 and safe['writes']==64 and safe['native']==safe['public']==8
assert sorted((r['bank'],r['row']) for r in safe['read_events'])==[(bank,row) for bank in range(2) for row in range(112,120)]
result=dict(status='PASS_SELECTED_NATIVE64_READ_LEASE',clock_ps=833,source_words=64,RDOUT_pairs=8,earliest_safe_issue_index=hi,preceding_rejected_issue_index=lo,
 safe=safe,previous=previous,early_old_version_control_caught=early['stale']>0,payload_control_caught=fault['errors']>0,
 observed_registered_CV_to_first_SRAM_read_edges=safe['firstread']-safe['rdreg'],observed_registered_CV_to_last_SRAM_read_edges=safe['lastread']-safe['rdreg'],
 observed_registered_CV_to_native_LO_edges=[e-safe['rdreg'] for e in safe['native_publication_edges']],physical_same_address_read_during_write_qualified=False,
 same_address_collision_runs_excluded=True,global_source_or_issuer_epochs_qualified=False,all80profiles_qualified=False,added_rtl_cycles=0,full_token=False)
(R/'check.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],hi,lo,flush=True)
