"""Compile source-owned SOT booking for real SMJ programmes.

All dates are slice-local rising edges. Caller supplies the actual target install
edge and observed/booked SM write edges; this module never guesses die transport.
The resulting frame follows WIN_LOAD and adds one descriptor q frame.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'sm_target'))
from smwire_cal import sot_frame


def booking(owner, se_jid, so_jid, obase, route, install_edge, heads,
            gather_first, gather_last):
    def field(v, bits, name):
        if type(v) is not int or not 0 <= v < 1 << bits:
            raise ValueError(f'{name} outside unsigned {bits}-bit source field')
        return v
    field(owner,20,'owner'); field(se_jid,8,'SE jid'); field(so_jid,8,'SO jid')
    field(obase,14,'obase')
    if route not in (1,2): raise ValueError('one actual gather route required')
    if type(install_edge) is not int or install_edge < 0: raise ValueError('install edge required')
    if set(heads) != set(range(16)): raise ValueError('all sixteen head bookings required')
    relative = {}
    for head, events in heads.items():
        if set(events) != {'first','last','read','retire'}: raise ValueError('four actual head edges required')
        row = {}
        for k,v in events.items():
            if type(v) is not int: raise ValueError('integer rising edges required')
            row[k] = field(v-install_edge,16,f'head {head} {k} relative date')
        if row['first'] > row['last'] or row['read'] <= row['last']+1 or row['retire'] <= row['read']+34:
            raise ValueError('write/read/retire source ordering violated')
        relative[head]=row
    first=field(gather_first-install_edge,16,'gather first relative date')
    last=field(gather_last-install_edge,16,'gather last relative date')
    if first>last: raise ValueError('gather window reversed')
    words=sot_frame(owner,se_jid,so_jid,obase,route,first,last,relative)
    return dict(words=words,descriptor_added_frames=1,owner=owner,install_edge=install_edge,
                heads=relative,gather_first=first,gather_last=last,
                scope='SOT encoding; supplied transport and numerical results retain their own qualification')


def attach_to_job(job, record):
    """Insert the encoded SOT into the actual lower_svc.Job before schedule().

    Job.schedule then counts the new frame in the real descriptor and advances
    following q words by three edges. The caller must book its complete SO
    programme and completion fence as well; adding configuration alone cannot
    qualify the legacy SE/PV-only job.
    """
    frames = job.frames
    if any(name == 'SOT' for name, _ in frames): raise ValueError('SOT already installed')
    matches = [(i,ws) for i,(name,ws) in enumerate(frames) if name == 'WIN_LOAD']
    if len(matches) != 1: raise ValueError('one actual WIN_LOAD required')
    i,ws = matches[0]
    if len(ws)!=1: raise ValueError('actual WIN_LOAD header required')
    win = ws[0]; owner = record['owner']
    if (win>>508)!=2 or ((win>>495)&255)!=(owner&255) or ((win>>449)&1023)!=((owner>>8)&1023):
        raise ValueError('SOT owner differs from actual accepted WIN_LOAD')
    if job.owner is not None and job.owner != owner: raise ValueError('source allocation epoch differs')
    raw=record['words']
    if len(raw)!=3 or any(type(w) is not int or not 0<=w<2**512 for w in raw):
        raise ValueError('encoded SOT header and two rows required')
    job.frames=frames[:i+1]+[('SOT',list(raw))]+frames[i+1:]
    return job


def replay_image(source, out):
    """Book existing real SMJ/dump image for the minimum SM+SOT component.

    The component uses its real decoder (2 edges to SM row observation), the
    measured SMS latency54, and SOT's three-edge drive-to-install path. The full
    die compiler must supply its own exact pin calendar to booking().
    """
    import json, shutil, hashlib
    source,out=Path(source),Path(out)
    out.mkdir(parents=True,exist_ok=True)
    for p in source.iterdir():
        if p.is_file(): shutil.copy2(p,out/p.name)
    cycles=[int(x,16) for x in (source/'qcyc.hex').read_text().split()]
    words=[int(x,16) for x in (source/'qwd.hex').read_text().split()]
    heads={}; i=0
    while i<len(words):
        h=words[i]; n=(h>>480)&4095
        if h>>508==9 and h&(1<<13):
            mask=(h>>14)&65535
            if mask==0 or mask&(mask-1) or n!=32: raise ValueError('actual per-head32-row operand frame required')
            g=mask.bit_length()-1
            heads[g]=dict(first=cycles[i+1]+56,last=cycles[i+n]+56,
                          read=cycles[i+n]+58,retire=cycles[i+n]+98)
        i+=n+1
    # WIN_LOAD and SOT are delivered before the existing SE command at edge20.
    cfg_last=11; install=cfg_last+3
    rec=booking(0,0x21,0x22,int((source/'meta.hex').read_text().split()[2],16),1,install,heads,
                min(x['read']+6 for x in heads.values()),max(x['read']+37 for x in heads.values()))
    win=(2<<508)|(1<<503)  # zero tag/user matches this existing component image
    cycles=[8,9,10,11]+cycles
    words=[win]+list(rec['words'])+words
    (out/'qcyc.hex').write_text(''.join(f'{v:08x}\n' for v in cycles))
    (out/'qwd.hex').write_text(''.join(f'{v:0128x}\n' for v in words))
    meta=(out/'meta.hex').read_text().split();meta[0]=f'{len(words):08x}'
    (out/'meta.hex').write_text('\n'.join(meta)+'\n')
    rec['source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.iterdir() if p.is_file()}
    rec['words']=[f'{w:0128x}' for w in rec['words']]
    (out/'sot_booking.json').write_text(json.dumps(rec,indent=2)+'\n')
    return rec

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('out');a=p.parse_args()
    replay_image(a.source,a.out)
