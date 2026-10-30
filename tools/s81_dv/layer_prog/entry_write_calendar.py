#!/usr/bin/env python3
"""Lower actual entry target5 writes into job-local native command calendars.

The caller selects relative issuer dates. No KS, global START, store readiness,
KIT, END or SEAL is invented. Pages leave two of128rows for the eventual real
retirement contract; each page is accepted by the current bound-control/boot
compiler once its exact source routes and timings are supplied.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE.parent),str(HERE)]
import dv_layer_compile as D
from lower_head import row_write_body


def compile_pages(entry, *, first_issue, issue_stride, page_commands=126):
    if entry.get('schema')!='opentallas.s81.entry_input_rows.v1':
        raise ValueError('actual entry_input_rows source required')
    if type(first_issue)is not int or first_issue<0:
        raise ValueError('explicit nonnegative issuer-relative first issue required')
    if type(issue_stride)is not int or issue_stride<2:
        raise ValueError('target5 issue stride must preserve the qualified two-edge cadence')
    if type(page_commands)is not int or not 1<=page_commands<=126:
        raise ValueError('reserve two native rows for actual KIT/END; command pages fit126')
    if D.SEQ['done_v']!=5:
        raise ValueError('native V ACK contract changed; source timing qualification required')
    writes=entry.get('writes')
    if not isinstance(writes,list)or not writes or entry.get('row_count')!=len(writes):
        raise ValueError('complete nonempty actual entry write table required')
    if not re.fullmatch('[0-9a-f]{64}',entry.get('die_sha256','')):
        raise ValueError('entry source die identity required')
    identities=set()
    for w in writes:
        sl,sid,leaf,row=w['slice'],w['sid'],w['leaf'],w['row']
        if (type(sid)is not int or not 0<=sid<16 or type(leaf)is not int or not 0<=leaf<5
            or type(row)is not int or not 0<=row<1024):
            raise ValueError('entry target5 identity outside native field width')
        if sl!=f'u_s_{sid//2}{"N"if sid&1 else"S"}' or w['engine']!=('VN'if sid&1 else'VS'):
            raise ValueError('actual slice/SID/engine identity differs')
        key=(sid,leaf,row)
        if key in identities:raise ValueError('duplicate target5 leaf row')
        identities.add(key)
        data=int(w['data128'],16);payload=int(w['ctl_payload186'],16)
        if not 0<=data<1<<128 or not 0<=payload<1<<186:
            raise ValueError('entry word outside native payload width')
        expected=D.ctl_payload(1<<sid,5,1<<leaf,row_write_body(row,data))
        if payload!=expected:raise ValueError('actual target5 payload differs from source row identity/data')
    source_hash=hashlib.sha256(json.dumps(writes,sort_keys=True).encode()).hexdigest()
    pages=[]
    for first in range(0,len(writes),page_commands):
        group=writes[first:first+page_commands];rows=[];cmd=[];templates=[]
        for i,w in enumerate(group):
            issue=first_issue+i*issue_stride;done=issue+5;eng=D.ENG[w['engine']]
            if done>=1<<24:raise ValueError('native issue/ACK field overflow')
            templates.append(dict(i=i,name=f'entry.{w["region"]}.{w["sid"]}.{w["leaf"]}.{w["row"]}',
                                  payload186=w['ctl_payload186'],source_write_index=first+i))
            rows.append(dict(eng=eng,issue=issue,done=done,arg=i,tix=i,
                             row76=f'{D.pack_row(done,issue,eng,i):019x}'))
            cmd.append(dict(kind='TARGET5',slice=w['slice'],sid=w['sid'],leaf=w['leaf'],row=w['row'],
                            issue=issue,template=i,source_write_index=first+i,region=w['region']))
        pages.append(dict(schema='opentallas.s81.entry_write_command_page.v1',status='UNSEALED_PROTOTYPE',
            die_sha256=entry['die_sha256'],fixture_meta_sha256=entry.get('fixture_meta_sha256'),
            input_sources=entry.get('input_sources'),commands=cmd,templates=templates,rows=rows,
            source_write_indices=[first,first+len(group)],source_row_count=len(writes),
            source_write_table_sha256=source_hash,
            timebase='issuer-relative age0 command; not a physical START or KS pin event',
            issue_stride_edges=issue_stride,ack_edges=5,reserved_retirement_rows=2,
            holds=['actual target5 leaf-store commit and HLOAD/GAIN/readiness records',
                   'actual per-page KIT, END, retirement and reload/start bookings',
                   'selected current bound control routes, local timings and host/reset transport',
                   'actual stage/phase and MU initialization before BEGIN/SEAL'],
            native_job_sealed=False,host_boot_complete=False,full_stage=False,full_token=False,added_rtl_cycles=0))
    return pages



def encode_unsealed(page):
    """Use the actual515b CSR/PW ABI; omit BEGIN/SEAL until real bookings exist."""
    rows=page['rows'];words=[D.csr_len(len(rows))]
    for i,r in enumerate(rows):
        value=D.pack_row(r['done'],r['issue'],r['eng'],r['arg'])
        if value!=int(r['row76'],16):raise ValueError('actual row76 differs')
        words.extend(D.csr_pw(a,d)for a,d in D.pw_row_words(i,value))
    words.extend(D.csr_template(t['i'],int(t['payload186'],16))for t in page['templates'])
    if any(type(w)is not int or not 0<=w<1<<515 for w in words):
        raise ValueError('native HOST word overflow')
    return words


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--entry-rows',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--first-issue',type=int,required=True);p.add_argument('--issue-stride',type=int,required=True)
    a=p.parse_args();entry=json.loads(a.entry_rows.read_text())
    pages=compile_pages(entry,first_issue=a.first_issue,issue_stride=a.issue_stride)
    a.out.mkdir(parents=True,exist_ok=False)
    files=[]
    for i,page in enumerate(pages):
        name=f'job{i:03d}.json';host=f'job{i:03d}.unsealed.host_boot.memh'
        words=encode_unsealed(page)
        page=dict(page,host_boot_file=host,host_word_count=len(words),begin_emitted=False,seal_emitted=False)
        (a.out/name).write_text(json.dumps(page,indent=1)+'\n')
        (a.out/host).write_text(D.memh(words,515));files.append(name)
    (a.out/'manifest.json').write_text(json.dumps(dict(schema='opentallas.s81.entry_write_calendars.v1',
        source_entry_sha256=hashlib.sha256(a.entry_rows.read_bytes()).hexdigest(),pages=files,
        command_count=sum(len(p['commands'])for p in pages),native_job_sealed=False,full_token=False),indent=1)+'\n')
    print('ENTRY_WRITE_CALENDARS',len(pages),'pages',sum(len(p['commands'])for p in pages),'commands UNSEALED')


if __name__=='__main__':main()
