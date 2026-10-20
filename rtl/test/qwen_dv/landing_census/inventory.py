#!/usr/bin/env python3
"""Count actual generated generic landing readers and unique shared writers."""
import re,json,collections,hashlib,sys
from pathlib import Path
result={}
for name in ('qfd_dv_s5_lp','qfd_dv_s5b_lp'):
 p=Path(f'rtl/qwen_dv/s5/lp/{name}.sv');source=p.read_text();items=[];reader_widths=[]
 for line in source.splitlines():
  if not any(n in line for n in ('ot_pl_land_w #','ot_pl_land_r #')):continue
  m=re.search(r'\.W\(\(\((\d+)\) - \((\d+)\) \+ 1\)\)',line)
  width=int(m[1])-int(m[2])+1 if m else int(re.search(r'\.W\((\d+)\)',line)[1])
  if 'ot_pl_land_r #' in line:reader_widths.append(width);continue
  depth=int(re.search(r'\.D\((\d+)\)',line)[1]);instance=re.search(r'\) (u_\w+) ',line)[1]
  items.append({'width':width,'D':depth,'bank_bits':width*depth,'instance':instance})
 result[name]={'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'reader_count':len(reader_widths),'reader_width_sum':sum(reader_widths),'writer_count':len(items),'width_sum':sum(i['width'] for i in items),'bank_bits':sum(i['bank_bits'] for i in items),'oversize_count':sum(i['bank_bits']>2048 for i in items),'oversize_bank_bits':sum(i['bank_bits'] for i in items if i['bank_bits']>2048),'width_histogram':dict(sorted(collections.Counter(i['width'] for i in items).items())),'storage_count_rule':'once per shared writer, not per reader','writers':items}
Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+'\n')
