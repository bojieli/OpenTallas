#!/usr/bin/env python3
"""Emit exact address/mask ROM only. No payload/checkpoint or phase events."""
import json,hashlib
from pathlib import Path
from qwen_hbm_controller_calendar_r2 import BASE,PROGRAM,kv_rows,kv_read_rows,weight_ranges,bankmap
from qwen_hbm_controller_events_r1 import ROOT,pinned

def emit(path):
    raw=pinned(ROOT,BASE,PROGRAM);g=json.loads(raw);op=g['instructions'][10]
    w=[kv_rows(g,op,p) for p in (0,1)];r=kv_read_rows(g,op,1)
    assert [len(x) for x in w]==[272,272] and len(r)==288
    ranges=next(x for x in weight_ranges(g) if x['instruction']==17)['ranges']
    span=next(s for e in ranges for s in e['stacks'] if s['stack']==0 and s['line_count']>=8192)
    lo=span['first_local_sector'];hi=lo+(span['line_count']-1)*4+3
    base=next(a for a in range(lo,min(hi-31,lo+32768)) if bankmap(a)['pc']==bankmap(a+16)['pc'])
    lines=[f"localparam logic [33:0] BURST_BASE=34'd{base};"]
    for name,bits,key in [('writer_sector',34,'sector'),('writer_stack',2,'stack'),('writer_mask',32,'mask')]:
        lines+=[f'function automatic [{bits-1}:0] {name}(input integer pos,i);', 'begin case(pos*272+i)']
        for pos in (0,1):
            for i,x in enumerate(w[pos]):lines.append(f"{pos*272+i}:{name}={bits}'d{x[key]};")
        lines += [f'default:{name}=0;','endcase end endfunction']
    for name,bits,key in [('reader_sector',34,'sector'),('reader_stack',2,'stack')]:
        lines+=[f'function automatic [{bits-1}:0] {name}(input integer i);','begin case(i)']
        for i,x in enumerate(r):lines.append(f"{i}:{name}={bits}'d{x[key]};")
        lines += [f'default:{name}=0;','endcase end endfunction']
    path.write_text('\n'.join(lines)+'\n')
    return dict(program_commit=BASE,program_path=PROGRAM,program_SHA256=hashlib.sha256(raw).hexdigest(),writers_position0=272,writers_position1=272,readers=288,die=op['attributes']['die'],BURST_BASE=base,weight_instruction=17,burst_issue_scope='Explicit finite diagnostic client phase; not actual opcode17 execution/prefetch',payload=False,metadata_ROM_SHA256=hashlib.sha256(path.read_bytes()).hexdigest())

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(emit(a.output),indent=2,sort_keys=True))
