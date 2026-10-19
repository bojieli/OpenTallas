"""Source-bound static table-port and lifetime certificate. No runtime waits.

An installation reserves the actual common write port, including all88 reads
and measured visibility: firstROMout3,lastROMout90, target readage2. Every
consumer supplies its last table-read edge; reinstallation of its user bank is
illegal until that lifetime retires. Other users have disjoint compact banks.
"""
import hashlib,json


def validate(windows, table_manifest_sha256):
    if len(table_manifest_sha256)!=64:
        raise ValueError('exact table payload source required')
    int(table_manifest_sha256,16)
    seen=set();port=[];lives={u:[] for u in range(4)}
    for w in windows:
        u,s=w['user'],w['stage']
        if u not in range(4) or s not in range(1,37) or (u,s) in seen:
            raise ValueError('invalid duplicate stage/user load')
        seen.add((u,s))
        if w['manifest_sha256']!=table_manifest_sha256 or len(w['consumer_sha256'])!=64:
            raise ValueError('unbound payload or consumer')
        int(w['consumer_sha256'],16)
        start,consume,retire=w['start'],w['first_read'],w['last_read']+1
        if not 0<=start or w['read_slots']!=88 or consume<start+92 or retire<=consume:
            raise ValueError('bad count or late table installation')
        # Conservative93edge measured-pipeline reservation stays explicit.
        for a,b in port:
            if max(a,start)<min(b,start+93):raise ValueError('table write-port collision')
        port.append((start,start+93))
        lives[u].append((start,start+93,consume,retire,s))
    if seen!={(u,s) for u in range(4) for s in range(1,37)}:
        raise ValueError('all36 stages/fourusers required')
    for user,events in lives.items():
        for i,a in enumerate(events):
            for j,b in enumerate(events):
                if i!=j and max(a[0],b[2])<min(a[1],b[3]):
                    raise ValueError('install overwrites live user table')
    payload=json.dumps(windows,sort_keys=True,separators=(',',':')).encode()
    return dict(schema='opentallas.qwen.static-table-load-windows.v1',windows=144,
                manifest_sha256=table_manifest_sha256,windows_sha256=hashlib.sha256(payload).hexdigest(),
                write_port_reserved_edges=144*93,per_user_36stage_edges=36*93,
                qualification='STATIC CERTIFICATE ONLY; actual calendar/consumer source required')
