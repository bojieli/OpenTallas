#!/usr/bin/env python3
"""Compile native187-bit VM selectors/owners from one quarter's SU image.

This is a source-defined calendar, never a trace-derived answer. The caller
must supply the fixed first serial command and bridge epoch in the bench's
reset-relative counters. 2422-bit pgslice commands are decoded exactly as the
native PGP/pgslice; the fixed four-edge drain, 3:4 bridge slots, two-edge LG
request path, and ten-edge host-leaf/target/calendar publication are priced.
The old sw5e clocks/10,7 returns remain a diagnostic profile only.
"""
import argparse,hashlib,json,shutil
from pathlib import Path
from sm_images import cal_word,prog_row

def compile_calendar(commands, *, first_serial, bridge_serial, bridge_stream,
                     host_launch, rows=128, host_publication=10, request_lane_edges=0,
                     request_lane_edges_by_bank=None, write_lane_edges_by_bank=None):
    if not isinstance(request_lane_edges,int) or request_lane_edges<0: raise ValueError('request lane depth must be a nonnegative integer')
    if request_lane_edges_by_bank is not None:
        if len(request_lane_edges_by_bank)!=8 or any(type(x) is not int or x<0 for x in request_lane_edges_by_bank):
            raise ValueError('per-bank request depths require eight nonnegative integers')
    if write_lane_edges_by_bank is not None:
        if len(write_lane_edges_by_bank)!=8 or any(type(x) is not int or x<0 for x in write_lane_edges_by_bank):
            raise ValueError('per-bank write depths require eight nonnegative integers')
    if first_serial < bridge_serial: raise ValueError('command before bridge epoch')
    if not 1<=rows<=1024: raise ValueError('native calendar PCW10 capacity')
    fields=[{} for _ in range(rows)];events=[]
    first_calendar=host_launch+host_publication
    for e,word in enumerate(commands):
        if not 0<=word<1<<2422: raise ValueError('quarter word overflow')
        for b in range(8):
            for kind,base,width,vbit,lag,sel,owner in (
                ('read',440,30,29,0,'lg_local_read','rslot_v'),
                ('write',128,39,38,4,'lg_local_write','wslot_v')):
                lane_edges=(write_lane_edges_by_bank[b] if kind=='write' and write_lane_edges_by_bank is not None else
                            request_lane_edges if request_lane_edges_by_bank is None else request_lane_edges_by_bank[b])
                cmd=word>>(base+width*b)&((1<<width)-1)
                if not cmd>>vbit:continue
                sector=(cmd>>(13 if kind=='read' else 8))&65535
                if sector&7!=b:raise ValueError(f'{kind} bank{b} names sector{sector:04x}')
                serial=first_serial+e+lag; n=serial-bridge_serial
                # event(n).lg_issue in su_multirate_compile.py; no dynamic wait.
                lg=bridge_stream+(4*n+6)//3+1
                at=lg-first_calendar
                if not 0<=at<at+2+lane_edges<rows:raise ValueError(f'{kind} edge{lg} outside resident calendar')
                fields[at][sel]=fields[at].get(sel,0)|1<<b
                fields[at+2+lane_edges][owner]=fields[at+2+lane_edges].get(owner,0)|1<<b
                # Native VM owner0 is the SU face. Remaining selector fields
                # stay zero: face_response returns by pipelined owner d_p;
                # client/response fields feed the separate hub/router path.
                events.append(dict(kind=kind,bank=b,command=e,serial_capture=serial,
                                   lg_sample=lg,vm_pin_sample=lg+2+lane_edges))
    words=[prog_row(i,cal_word(**f),187) for i,f in enumerate(fields)]
    return words,dict(schema='opentallas.native_su_calendar.v1',qualified=False,
        first_serial=first_serial,bridge_serial=bridge_serial,bridge_stream=bridge_stream,
        host_launch=host_launch,host_publication=host_publication,rows=rows,
        calendar_row0_consumer=first_calendar,owner=0,lg_to_vm_pin_edges=2+request_lane_edges if request_lane_edges_by_bank is None else [2+x for x in request_lane_edges_by_bank],request_lane_edges=request_lane_edges,
        **({} if request_lane_edges_by_bank is None else dict(request_lane_edges_by_bank=request_lane_edges_by_bank)),
        **({} if write_lane_edges_by_bank is None else dict(write_lane_edges_by_bank=write_lane_edges_by_bank)),
        events=events,unused_fields='hub/router client/response/ring paths unused by native SU face')

def add_host_replay(source,boundary,output,words,meta, *, stream_limit=3700,
                    serial_limit=2774,hbm_limit=3010):
    source,output=Path(source),Path(output)
    ports=[e for e in json.loads(Path(boundary).read_text())['inputs']
           if e['driver'].split('.')[0]!='<die_pin>']
    byname={p['name']:i for i,p in enumerate(ports)}
    arrays=[[int(s,16) for s in (source/(n+'.mem')).read_text().split()]
            for n in ('hdr','val','msk')]
    if len({len(a)for a in arrays})!=1:raise ValueError('array length mismatch')
    capacity=len(arrays[0]);limits=[stream_limit,serial_limit,hbm_limit]
    original=list(zip(*arrays));events=[e for e in original if e[0]>>62 in (1,2)
        and (e[0]&0xffffffff)<=limits[(e[0]>>60)&3]]
    kept=list(events)
    def drive(cycle,suffix,value):
        pi=byname['host_cp_ingress__'+suffix]
        events.append(((1<<62)|(pi<<44)|cycle,value,(1<<ports[pi]['width'])-1))
    # Direct output of the host ingress is the slice's documented boundary.
    # All target/leaf/descriptor installation logic remains actual RTL.
    for suffix,value in [('cfg_target',96),('cfg_v',1)]:drive(100,suffix,value)
    for i,word in enumerate(words):
        drive(100+i,'cfg_addr',i);drive(100+i,'cfg_data',word)
    drive(100+len(words),'cfg_v',0)
    desc=100+len(words)+10
    for suffix,value in [('desc_base',0),('desc_limit',len(words)),('desc_loops',1),('desc_v',1)]:drive(desc,suffix,value)
    drive(desc+1,'desc_v',0)
    drive(meta['host_launch'],'launch_v',1);drive(meta['host_launch']+1,'launch_v',0)
    if len(events)>capacity:raise ValueError('compiled event capacity exceeded')
    events.sort(key=lambda e:((e[0]>>60)&3,e[0]&0xffffffff,e[0]>>62))
    # An additive replay may omit only events after the observation window.
    # Check identities include their original expected values and masks.
    assert all(e in events for e in kept)
    events.extend([(3<<62,0,0)]*(capacity-len(events)))
    output.mkdir(parents=True,exist_ok=False)
    for col,name in enumerate(('hdr','val','msk')):
        (output/(name+'.mem')).write_text(''.join(f'{e[col]:x}\n'for e in events))
    shutil.copyfile(source/'vm_pre.txt',output/'vm_pre.txt')
    meta.update(original_events_kept=len(kept),added_events=sum(e not in kept for e in events if e[0]>>62!=3),
                window_limits=limits,capacity=capacity,preload_sha256=hashlib.sha256((output/'vm_pre.txt').read_bytes()).hexdigest(),
                policy='all original drives and numeric checks in the observation window retained byte-for-byte; only later events omitted')
    (output/'calendar_model.json').write_text(json.dumps(meta,indent=2)+'\n')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('commands',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--first-serial',type=int,required=True);p.add_argument('--bridge-serial',type=int,required=True)
    p.add_argument('--bridge-stream',type=int,required=True);p.add_argument('--host-launch',type=int,required=True)
    p.add_argument('--request-lane-edges',type=int,default=0);p.add_argument('--rows',type=int,default=128);p.add_argument('--replay',type=Path);p.add_argument('--boundary',type=Path)
    a=p.parse_args();words,meta=compile_calendar([int(x,16)for x in a.commands.read_text().split()],first_serial=a.first_serial,
        bridge_serial=a.bridge_serial,bridge_stream=a.bridge_stream,host_launch=a.host_launch,rows=a.rows,request_lane_edges=a.request_lane_edges)
    if a.replay:add_host_replay(a.replay,a.boundary,a.output,words,meta)
    else:a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'calendar.mem').write_text(''.join(f'{v:064x}\n'for v in words))
    (a.output/'calendar_model.json').write_text(json.dumps(meta,indent=2)+'\n')
if __name__=='__main__':main()
