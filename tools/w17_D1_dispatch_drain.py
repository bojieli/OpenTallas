#!/usr/bin/env python3
"""Freeze one pinned make dispatcher, drain its workers, and preserve inputs.
No compiler/frontend/runtime launch. Execution requires an explicit owner GO.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
OLD=Path('/tmp/w17-D1-incremental-native-20261002-r1')
MASTER=704063
SUPERVISOR=703938
UNIT='w17-D1-incremental-native-20261002-r1.service'

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()

def identity(pid):
    p=Path('/proc')/str(pid);text=(p/'stat').read_text();fields=text[text.rindex(')')+2:].split()
    return {'pid':pid,'state':fields[0],'ppid':int(fields[1]),'start_ticks':int(fields[19]),'cmdline':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip(),'cwd':str((p/'cwd').resolve()),'cgroup':(p/'cgroup').read_text().strip()}

def check_identity(expected,actual):
    for key in ('pid','start_ticks','cmdline','cwd','cgroup'):
        if expected[key]!=actual[key]:raise ValueError('Owner identity changed: '+key)

def live_workers(members,master,supervisor):
    return [x for x in members if x['pid'] not in (master,supervisor) and x['state']!='Z']

def members(group):
    rows=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdecimal():continue
        try:
            x=identity(int(p.name))
            if x['cgroup']==group:rows.append(x)
        except (FileNotFoundError,ProcessLookupError,PermissionError):pass
    return rows

def valid_object(path):
    with Path(path).open('rb') as f:b=f.read(64)
    if not (len(b)==64 and b[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<HH',b,16)==(1,62)):return False
    offset=struct.unpack_from('<Q',b,40)[0];width,count=struct.unpack_from('<HH',b,58)
    return offset>=64 and width==64 and count>0 and Path(path).stat().st_size>=offset+width*count

def check_GO(go,packet,head):
    if go.get('authorized') is not True or go.get('phase')!='FREEZE_DRAIN_NATIVE_DISPATCH':raise ValueError('No owner GO')
    if go.get('source_head')!=head or go.get('packet_SHA256')!=packet:raise ValueError('GO source/packet mismatch')
    if go.get('remote_ready') is not True or go.get('fleet_lease_verified') is not True:raise ValueError('Remote not ready/leased')
    if go.get('runtime_authorized') is not False:raise ValueError('Runtime forbidden')
    if any(go.get(x) is not None for x in ('wall_limit','per_process_AS','per_file_limit')):raise ValueError('Forbidden restriction')

def prepare(out):
    m,s=identity(MASTER),identity(SUPERVISOR)
    if m['ppid']!=SUPERVISOR or m['cwd']!=str(OLD/'obj') or m['cgroup']!=s['cgroup'] or UNIT not in m['cgroup']:raise ValueError('Unexpected original owner')
    record={'master':m,'supervisor':s,'owner_members':members(m['cgroup']),'classes_SHA256':sha(OLD/'obj/Vtb_D1_scope_core_classes.mk'),'live_wrapper_SHA256':sha(OLD/'cxx'),'source_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'UTC_epoch':time.time(),'source_engine':'4e38326d6f361bc85e660f48c59c355e2bb95274','source_old':'966eca710dd35786be462e595f7d8f9392fbcc4b','signals_sent':0}
    out.mkdir(exist_ok=False);(out/'owner_packet.json').write_text(json.dumps(record,indent=2)+'\n')
    return record

def execute(packet_path,go_path,out):
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT):raise ValueError('Dirty source')
    packet=json.loads(packet_path.read_text());go=json.loads(go_path.read_text());check_GO(go,sha(packet_path),head)
    check_identity(packet['master'],identity(MASTER));check_identity(packet['supervisor'],identity(SUPERVISOR))
    if packet['classes_SHA256']!=sha(OLD/'obj/Vtb_D1_scope_core_classes.mk') or packet['live_wrapper_SHA256']!=sha(OLD/'cxx'):raise ValueError('Source changed')
    fd=os.pidfd_open(MASTER);check_identity(packet['master'],identity(MASTER))
    out.mkdir(exist_ok=False);events=[];frozen=False;retired=False
    def event(kind,**extra):
        events.append(dict(kind=kind,UTC_epoch=time.time(),**extra));(out/'events.json').write_text(json.dumps(events,indent=2)+'\n')
    try:
        signal.pidfd_send_signal(fd,signal.SIGSTOP);frozen=True;event('MAKE_ONLY_SIGSTOP',pid=MASTER,start_ticks=packet['master']['start_ticks'])
        while True:
            check_identity(packet['master'],identity(MASTER))
            if identity(MASTER)['state'] not in ('T','t'):
                time.sleep(.01);continue
            rows=members(packet['master']['cgroup']);workers=live_workers(rows,MASTER,SUPERVISOR)
            (out/'drain_progress.json').write_text(json.dumps({'live_workers':workers,'objects_present':len(list((OLD/'obj').glob('*.o'))),'wall_limit':None,'UTC_epoch':time.time()},indent=2)+'\n')
            if not workers:break
            time.sleep(5)
        bad=[str(p) for p in (OLD/'obj').glob('*.o') if not valid_object(p)]
        if bad:raise ValueError('Completed object invalid: '+str(bad))
        inventory={str(p.relative_to(OLD/'obj')):{'SHA256':sha(p),'bytes':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns} for p in sorted((OLD/'obj').iterdir()) if p.is_file()}
        (out/'quiescent_input_inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
        event('DRAIN_COMPLETE_EVERY_OBJECT_PCH_PRESERVED',objects=len(list((OLD/'obj').glob('*.o'))),PCH=len(list((OLD/'obj').glob('*.gch'))))
        # Exact paused dispatcher only: recipes have finished, avoiding any cc1 kill.
        signal.pidfd_send_signal(fd,signal.SIGKILL);retired=True;event('PAUSED_MASTER_RETIRED',pid=MASTER)
        while True:
            rows=members(packet['master']['cgroup'])
            if not [x for x in rows if x['state']!='Z']:break
            time.sleep(5)
        event('ORIGINAL_SUPERVISOR_TERMINAL',compiler_launches=0)
        if not (OLD/'verdict.json').exists():raise ValueError('Original terminal receipt absent')
        (out/'original_terminal_receipt.json').write_bytes((OLD/'verdict.json').read_bytes())
        event('READY_FOR_DISJOINT_SHARDS',snapshot_SHA256=sha(out/'quiescent_input_inventory.json'),runtime=False)
    finally:
        # Before retirement no shard has been admitted by this controller. A failed
        # pre-transfer check restores the original dispatcher instead of stranding it.
        if frozen and not retired:
            signal.pidfd_send_signal(fd,signal.SIGCONT)
            event('PRETRANSFER_FAILURE_ORIGINAL_DISPATCH_RESTORED',compiler_launches=0)
        os.close(fd)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',action='store_true');p.add_argument('--packet',type=Path);p.add_argument('--GO',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.prepare:prepare(a.out)
    elif a.packet and a.GO:execute(a.packet,a.GO,a.out)
    else:p.error('Use --prepare, or explicit --packet and --GO')
