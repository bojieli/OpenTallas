#!/usr/bin/env python3
"""Narrow source-template expansion; never a synthesized netlist qualification."""
import argparse,json,re,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('source');a=p.parse_args();s=Path(a.source).read_text()
bank=int(re.search(r'BANK_BITS=(\d+)',s)[1]);group=int(re.search(r'GROUP_BANKS=(\d+)',s)[1])
# Refuse graph changes this template-specific expansion cannot account for.
checks={'shared_valid_actual_slot_D':'else if(we[s]) slot_valid[s]<=(MUT==4)?1\'b1:ingress_valid;' in s,
 'actual_indexed_write':'if(we[s]) payload[s]<=ingress;' in s,
 'shared_onehot':'assign we[s]=active & dec[s];' in s,
 'read_rotation':'assign read_dec[s]=dec[(s+2+' in s,
 'raw_authority':'raw_rst_n & ((MUT==2)?a0:a1)' in s,
 'distinct_generated_rootpairs':'begin:g_group' in s and 'u_tx_root' in s and 'u_rx_root' in s}
checks['normalized_exact_reviewed_source_identity']=hashlib.sha256(re.sub(r'GROUP_BANKS=\d+', 'GROUP_BANKS=8',s,count=1).encode()).hexdigest()=='f8211325ebd982bccb90083f2c58af6ef2d24c6d1e2d6a5ea6c015a9d5b61b25'
rows=[];totalbanks=groups=payload=0
for w in (268,68):
 widths=[min(bank,w-i) for i in range(0,w,bank)];totalbanks+=len(widths);payload+=4*w
 for first in range(0,len(widths),group):
  bw=widths[first:first+group];groups+=1
  rows.append({'W':w,'first_bank':first,'banks':len(bw),'group_valid_D_mux_loads':4*len(bw),'rx_group_reset_loads':2*len(bw)+2,'max_write_enable_loads':max(bw)+1,'max_phase_decode_loads':max(bw)+2,'max_active_loads':max(bw)+11})
raw=2*groups+groups #per physical reset:2async pins/group plus group AND/group
other=3*(268+68)+2*totalbanks+4*totalbanks+2*totalbanks+groups+8*totalbanks+4*groups
checks.update({'bank_legal':1<=bank<=8,'group_legal':1<=group<=8,'group_valid_fanout':all(r['group_valid_D_mux_loads']<=32 for r in rows),'group_reset_fanout':all(r['rx_group_reset_loads']<=32 for r in rows),'raw_fanout':raw<=32})
r={'classification':'PREOPT_SOURCE_TEMPLATE_CENSUS_NOT_NATIVE','source_sha256':hashlib.sha256(s.encode()).hexdigest(),'checks':checks,'rows':rows,'raw_loads_per_face':raw,'state_bits':{'payload':payload,'other':other,'total':payload+other},'unbound':'constants/tie cells, merging, macro implementation, clock/PG not audited','verdict':'PASS_SOURCE_TEMPLATE' if all(checks.values()) else 'REFUSE_SOURCE_TEMPLATE'}
print(json.dumps(r,indent=2));raise SystemExit(0 if all(checks.values()) else 1)
