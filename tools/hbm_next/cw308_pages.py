#!/usr/bin/env python3
"""Emit bounded native CW308 table pages without increasing the SRAM depth.

Pages retain command order and all move/buffer/epoch bits. Only launch-relative
emit/issue/drain dates are translated by one common origin within a page. The
caller must drain the previous page, install these native cfg words, arm the
existing descriptor, then launch. This is not a whole-programme calendar.
"""
from pathlib import Path
import json
MAX_COMMANDS=128

def pages(commands,*,limit=MAX_COMMANDS,first_emit=32):
    if not 1<=limit<=MAX_COMMANDS or first_emit<0:raise ValueError('native page capacity/date')
    out=[];last=-1
    for index,(at,cmd) in enumerate(commands):
        if type(at)is not int or type(cmd)is not int or not 0<=at<1<<32 or not 0<=cmd<1<<308:raise ValueError('CW308/date width')
        issue=cmd&0xffffffff;drain=cmd>>32&0xffffffff
        if at<=last or issue<at+2 or drain<=issue:raise ValueError('nonmonotonic command or invalid native dates')
        last=at
    for start in range(0,len(commands),limit):
        group=commands[start:start+limit];origin=group[0][0]-first_emit
        records=[];words=[]
        for at,cmd in group:
            emit=at-origin;issue=(cmd&0xffffffff)-origin;drain=(cmd>>32&0xffffffff)-origin
            if min(emit,issue,drain)<0 or max(emit,issue,drain)>=1<<32:raise ValueError('translated date range')
            translated=(cmd&~((1<<64)-1))|issue|(drain<<32)
            entry=(translated<<32)|emit
            words.extend((entry&((1<<256)-1),entry>>256))
            records.append(dict(at=emit,cmd=translated,source_at=at,source_index=start+len(records)))
        out.append(dict(records=records,words=words,origin=origin,descriptor=dict(base=0,limit=len(group),loops=1),
                        # Existing fixture protocol: each native config beat is
                        # followed by an idle edge; guards are explicit caller
                        # reservations, not inferred link bandwidth.
                        host_fixture_config_edges=4*len(group),
                        host_fixture_arm_guard_edges=34))
    return out

def write(commands,out):
    result=pages(commands);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    for i,page in enumerate(result):
        (out/f'page{i}.hex').write_text(''.join(f'{word:064x}\n' for word in page['words']))
        (out/f'page{i}_cmd.hex').write_text(''.join(f"{r['cmd']:077x}\n" for r in page['records']))
        (out/f'page{i}_at.hex').write_text(''.join(f"{r['at']:08x}\n" for r in page['records']))
    meta=dict(schema='opentallas.hbm.cw308_pages.v1',commands=len(commands),pages=len(result),max_page_commands=128,
              cfg_edges=sum(p['host_fixture_config_edges'] for p in result),
              between_page_fixture_config_edges=sum(p['host_fixture_config_edges']+p['host_fixture_arm_guard_edges'] for p in result[1:]),
              launch_relative_target_LEAD=8,host_wire_cost_included=False,
              production_calendar_adopted=False,scope='native cfg/descriptor payloads; physical HOST delivery and global schedule are separate')
    (out/'pages.json').write_text(json.dumps(meta,indent=1)+'\n');return result
