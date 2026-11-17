"""Loadable CAP/XR payload words with explicit unassigned mission timing."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from lower_vs import ctl_payload

FIELDS = dict(obase=(0,12), ops=(12,12), np=(24,3), fmt=(27,2),
              rbase=(29,16), rcnt=(45,11), rsplit=(56,16), lo32=(72,1), hi32=(73,1))

def checked_word(cfg):
    if set(cfg) != set(FIELDS):
        raise ValueError('CAP configuration fields differ from native ABI')
    word = 0
    for name, (shift, width) in FIELDS.items():
        value = cfg[name]
        if type(value) is not int or not 0 <= value < 1 << width:
            raise ValueError('CAP field out of range: '+name)
        word |= value << shift
    if (cfg['fmt'] != 2 or cfg['ops'] or cfg['np'] or cfg['rsplit'] or
            cfg['lo32'] or cfg['hi32'] or not 0 < cfg['rcnt'] <= 320 or
            cfg['rbase']+cfg['rcnt'] > 1280 or
            cfg['obase'] not in range(512,897,64)):
        raise ValueError('unsupported capture-only FFN configuration')
    return word

def payload_files(record, calendar):
    """Return native word images, never a scheduled or installed programme."""
    if not record.get('capture_only',{}).get('enabled') or record.get('faults') != 0:
        raise ValueError('passing capture-only producer required')
    if record.get('pairing_slot_collisions'):
        raise ValueError('CAP pairing slot collisions remain unqualified')
    bound = record.get('bound_source',{})
    digest = bound.get('netlist_sha256','')
    if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('strict selected bound-source identity required')
    phases=record['phases'];dates=calendar['phases']
    if (calendar.get('op') != 'ffn.down' or calendar.get('layer') != record.get('layer') or
            len(phases) != len(dates) or len(phases) != calendar.get('nphases')):
        raise ValueError('selected per-op phase calendar differs')
    ids=[d['phase']for d in dates]
    if any(type(x)is not int or not 0<=x<1024 for x in ids) or ids!=sorted(set(ids)):
        raise ValueError('field phase identities must be ordered unique10-bit IDs')
    lines={sid:dict(cfg=[],ctl=[],beat=[],index=[])for sid in range(16)}
    row_tags={}
    for ordinal,(phase,date)in enumerate(zip(phases,dates)):
        if phase['op']!='ffn.down' or sorted(x['slice_index']for x in phase['slices'])!=list(range(16)):
            raise ValueError('one complete sixteen-slice FFN phase required')
        for sl in phase['slices']:
            sid=sl['slice_index'];cfg=sl['cfg'];word=checked_word(cfg)
            if sl['cfg_d']!=f'{word:040x}':
                raise ValueError('declared CAP word differs from native encoding')
            tags=[t for frame in sl['frame_tags'].values()for t in frame]
            if (len(tags)!=len(set(tags)) or any(type(t)is not int or
                    not cfg['rbase']<=t<cfg['rbase']+cfg['rcnt']for t in tags)):
                raise ValueError('rank-local frame tags violate selected capture range')
            key=(phase['mat'],sid)
            state=row_tags.setdefault(key,dict(cfg=cfg,tags=[]))
            if state['cfg']!=cfg:raise ValueError('matrix capture configuration changes between chunks')
            state['tags'].extend(tags)
            payload=ctl_payload(1<<sid,3,0,word)
            beat=1|(4<<9)|(payload<<21)
            lines[sid]['cfg'].append(f'{word:040x}\n')
            lines[sid]['ctl'].append(f'{payload:047x}\n')
            lines[sid]['beat'].append(f'{beat:0276x}\n')
            lines[sid]['index'].append(dict(row=ordinal,field_phase=date['phase'],
                field_tag=date['tag'],source_phase_ordinal=phase['phase'],
                matrix=phase['mat'],chunk=phase['chunk'],issue_cycle=None))
    for state in row_tags.values():
        cfg=state['cfg']
        if sorted(state['tags'])!=list(range(cfg['rbase'],cfg['rbase']+cfg['rcnt'])):
            raise ValueError('complete matrix rank-tag coverage required')
    files={}
    for sid,sl in lines.items():
        for key,name in [('cfg','cfg_d.hex'),('ctl','ctl_payload.hex'),('beat','line_ctl.hex')]:
            files[f's{sid:02d}/'+name]=''.join(sl[key])
    manifest=dict(schema='opentallas.s81.capture-only-payload-images.v1',
        status='PREPARATORY_NATIVE_WORDS_MISSION_UNQUALIFIED',
        bound_netlist_sha256=digest,layer=record['layer'],op='ffn.down',
        cfg_word_bits=160,ctl_payload_bits=186,line_beat_bits=1104,
        target=3,slices=16,rows_per_slice=len(phases),total_descriptors=16*len(phases),
        issue_epoch=None,install_admitted=False,mission_schedule_qualified=False,
        row_leases_qualified=False,native_RD_layout_admitted=False,
        source_record_sha256=hashlib.sha256(json.dumps(record,sort_keys=True).encode()).hexdigest(),
        phase_calendar_sha256=hashlib.sha256(json.dumps(calendar,sort_keys=True).encode()).hexdigest(),
        source_phase_rows={sid:sl['index']for sid,sl in lines.items()},
        missing='actual CAP CFG lifetime/issuer routes, frame-return joins, mission epoch and row leases',
        file_sha256={name:hashlib.sha256(text.encode()).hexdigest()for name,text in files.items()})
    files['manifest.json']=json.dumps(manifest,indent=2)+'\n'
    return files

def write_images(record, calendar, destination):
    files=payload_files(record,calendar)
    destination=Path(destination)
    destination.mkdir(parents=True,exist_ok=False)
    for name,text in files.items():
        path=destination/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
    return json.loads(files['manifest.json'])
