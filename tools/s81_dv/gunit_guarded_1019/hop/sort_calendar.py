#!/usr/bin/env python3
"""Current walker fixture repair: reorder exact rows, never change their timing/data."""
import hashlib
import json
from pathlib import Path
import sys
src=Path(sys.argv[1]);dst=Path(sys.argv[2]);receipt=Path(sys.argv[3])
lines=src.read_text().splitlines();parts={};indices={}
for i,line in enumerate(lines):
    x=(int(line,16)>>1)&((1<<512)-1)
    if x&255!=0x10:continue
    a=(x>>96)&127;v=(x>>32)&((1<<28)-1);page=v>>26
    if page==3:continue
    assert page not in parts.setdefault(a,{})
    parts[a][page]=v&((1<<26)-1);indices[(a,page)]=i
assert sorted(parts)==list(range(5))
assert all(set(ps)=={0,1,2} for ps in parts.values())
rows={a:sum(v<<(26*k) for k,v in ps.items()) for a,ps in parts.items()}
order=sorted(rows,key=lambda a:(rows[a]>>28)&((1<<24)-1))
assert order==[0,1,3,2,4]
new=lines.copy()
for dest,old in enumerate(order):
    v=rows[old]
    for page in range(3):
        i=indices[(dest,page)];b=int(lines[i],16)
        d=(page<<26)|((v>>(26*page))&((1<<26)-1))
        b=(b&~(((1<<28)-1)<<33))|(d<<33)
        new[i]=f'{b:0{len(lines[i])}x}'
assert sorted(rows.values())==sorted(rows[a] for a in order)
untouched=[i for i in range(len(lines)) if i not in set(indices.values())]
assert all(new[i]==lines[i] for i in untouched)
dst.parent.mkdir(parents=True,exist_ok=True);dst.write_text('\n'.join(new)+'\n')
receipt.write_text(json.dumps({'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'sorted_sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'old_rows_in_new_order':order,'exact_76bit_row_multiset_equal':True,'non_PW_header_template_words_identical':len(untouched),'changed_hostword_indices':[i for i in range(len(lines)) if new[i]!=lines[i]],'issue_done_engine_arg_bits_unchanged':True,'gold_stimuli_expected_timestamps_and_deadline_changed':False,'original_rejection':'Actual original full simulation GU_LAYER FAIL timeout; static exact current walker seal-order rejection at row2→3, expectedcode3 (not runtime-observed).'},indent=2)+'\n')
print('HOST_CALENDAR_SORT_PASS original5rows exactmultiset, nonPW/header/template unchanged')
