#!/usr/bin/env python3
"""Extract the protected-hierarchy diagnostic soft region, with strict boundaries."""
import argparse,hashlib,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('dest',type=Path);a=p.parse_args()
s=a.source.read_text();mods={m[1]:m.group() for m in re.finditer(r'(?ms)^module\s+(\S+)\s*\(.*?^endmodule',s)}
assert 'native_soft' in mods and 'qkd_hr_ingest_qm' in mods
protected=[n for n in mods if 'ot_link_afifo' in n or 'ot_host_reset_bank' in n or 'ot_reset_sync' in n]
assert len(protected)>=4,('reviewed FIFO/reset hierarchy was flattened',protected)
soft=mods['native_soft'];assert not re.search(r'^\s+\\?\S*(?:ot_link_afifo|ot_host_reset_bank|ot_reset_sync|ot_sram)\S*\s+\\?\S+\s*\(',soft,re.M)
names=['native_soft']+sorted(n for n in mods if n.startswith('qkd_host_native_engine_n32_cell_') or n=='qkc_ingest_take_copy')
a.dest.write_text('\n\n'.join(mods[n] for n in names)+'\n')
print(json.dumps(dict(source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),extracted_sha256=hashlib.sha256(a.dest.read_bytes()).hexdigest(),protected=protected,modules=names),indent=1))
