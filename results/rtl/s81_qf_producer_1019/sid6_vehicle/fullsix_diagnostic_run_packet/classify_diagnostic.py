#!/usr/bin/env python3
"""Observational identity/tag/EF classification; never drives DUT state."""
from pathlib import Path
import re,json,collections
b=Path.cwd();s=(b/'diagnostic.log').read_text();ident=json.load(open('diagnostic_expected_identity.json'))
lookup={(r['frame'],r['configured_row14']):r for r in ident['rows']};seen=collections.Counter();unknown=[];rowtags=collections.defaultdict(set)
lane_frames=['u_f_3L01','u_f_3L02','u_f_3L03','u_f_3R01','u_f_3R02','u_f_3R03']
returns=[]
for t,l,w in re.findall(r'^FRAME_RETURN t=(-?\d+) lane=(\d+) word=([0-9a-f]+)',s,re.M):
 l=int(l);w=int(w,16);tag=(w>>3)&0xffffffff;row=(tag>>13)&65535;key=(lane_frames[l],row&16383)
 rec=dict(t=int(t),lane=l,word=f'{w:018x}',row16=row,op_tag=row>>14,frame_fault=(w>>69)&1,err=(w>>67)&1)
 if key not in lookup:unknown.append(rec)
 else:
  r=lookup[key];seen[r['semantic_row']]+=1;rowtags[r['epoch']].add(row>>14);rec.update(semantic_row=r['semantic_row'],epoch=r['epoch'])
 returns.append(rec)
capture=[dict(t=int(t),id=i,bank=int(k),sampled=int(a),captured=int(c)) for t,i,k,a,c in re.findall(r'^ACTUAL_TAG_CAPTURE t=(-?\d+) id=(\S+) bank=(\d+) sampled=(\d+) captured=(\d+)',s,re.M)]
gox=collections.Counter();faults=[]
for line in s.splitlines():
 if line.startswith('CFG7_TRACE '):
  i=re.search(r' id=(\S+)',line).group(1)
  if ' go_x=1 ' in line:gox[i]+=1
  st=re.search(r' st=([01]+)',line)
  if st and (int(st.group(1),2)&2):faults.append(line) # st={fault,ld_busy}; busy is normal
 if line.startswith('Q_LIFETIME ') and ' fault=1' in line:faults.append(line)
all_ids=ident['all72_ids'];missing=[r for r in ident['rows'] if seen[r['semantic_row']]==0];dups={str(k):v for k,v in seen.items() if v!=1}
source_error=re.findall(r'FULLSIX_SOURCE_CHECK errors=(\d+)',s)
causes=[int(v,16) for v in re.findall(r' causes=([0-9a-f]+)',s)];cause=0
for v in causes:cause|=v
result=dict(scope='Original reset-CAP/F9 diagnostic classification only; never healthy numerical qualification',raw_source_check_errors=int(source_error[-1]) if source_error else None,actual_tag_captures=capture,captured_sample_mismatches=[r for r in capture if r['sampled']!=r['captured']],CFG7_GO_X_counts=dict(gox),expected_source_broadcasts_per_pair=15,CFG7_missing_or_extra={i:gox[i] for i in all_ids if gox[i]!=15},expected_configured_backend_pair_GOs=ident['expected_placement_pair_GOs'],actual_backend_captures=len(capture),backend_count_is_metadata_check_not_numeric=True,frame_return_words=returns,expected_semantic_rows_total=512,missing_semantic_rows=missing,duplicate_counts=dups,unknown_row_identities=unknown,actual_op_tags_by_identity_epoch={str(e):sorted(v) for e,v in rowtags.items()},tag_sequence_assumed=False,EF_or_Q_fault_observations=faults,CAP_sticky_causes=f'{cause:04x}',expected_F9_if_complete_rows_return=bool(cause&(1<<8)),CAP_CW_events=len(re.findall(r'^ACTUAL_CW ',s,re.M)),CAP_reset_expected_CW_events=0,active_CFG_injected=False,source_check_complete='FULLSIX_PREPARATORY_TRACE_END' in s,numerical_PASS=None,native_phase=None,whole_token_deadline_PASS=None,healthy_CAP_and_VP_drain=None)
(b/'diagnostic_classification.json').write_text(json.dumps(result,indent=2)+'\n')
print('RESET_CAP_DIAGNOSTIC_CLASSIFIED','returns',len(returns),'missing',len(missing),'duplicates',len(dups),'unknown',len(unknown),'CAPcause',f'{cause:04x}','NO_NUMERIC_PASS')
