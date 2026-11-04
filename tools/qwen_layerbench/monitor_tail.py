"""Opt-in source candidate for invariant native monitor copies; no loader/caller adoption."""
import argparse
import hashlib
import json
from pathlib import Path
import programme_store as P

TAIL = P.STAGES * P.STRIDE
SOURCE_PC = (3, 3, 11, 10)


def tails(manifest, *, head_stage37=False):
    if manifest.get('parameters') != P.NATIVE_COMPACT_PARAMETERS:
        raise ValueError('actual native compact four-user ABI required')
    P.logical_images(manifest, head_stage37=head_stage37)  # Reject malformed native records, padding and missing source fields.
    stages = sorted((s for s in manifest['stages'] if s['stage'] <= 36), key=lambda s: s['stage'])
    if head_stage37:
        for st in manifest['stages']:
            if st['stage'] == 37 and any(r['addr'] in (6,7) for sl in st['slices'] for pu in sl['prog_users'] for r in pu):
                raise ValueError('HEAD PROG overlaps monitor pair reservation6/7')
    if [s['stage'] for s in stages] != list(range(1, 37)):
        raise ValueError('all36 actual stages required')
    baseline = {}
    for stage in stages:
        if sorted(s['slice'] for s in stage['slices']) != list(range(12)):
            raise ValueError('all12 native slices required')
        for sl in stage['slices']:
            if len(sl['prog_users']) != 4:
                raise ValueError('four actual user programme images required')
            for user, records in enumerate(sl['prog_users']):
                pairs = {r['addr']: int(r['payload_hex'], 16) for r in records}
                if len(records) != 6 or set(pairs) != set(range(6)):
                    raise ValueError('six distinct native programme pairs required')
                words = tuple((pairs[pc // 2] >> (512 * (pc % 2))) & ((1 << 457)-1) for pc in SOURCE_PC)
                key = sl['slice'], user
                if key in baseline and baseline[key] != words:
                    raise ValueError(f'noninvariant monitor source slice/user {key} stage{stage["stage"]}')
                baseline[key] = words
    result = {}
    for sid in range(12):
        result[sid] = []
        for user in range(4):
            words = baseline[sid, user]
            for pair in range(2):
                payload = words[2*pair] | (words[2*pair+1] << 512)
                result[sid].append(P.encode(3, 6+pair, f'{payload:0256x}'))
    return result


def physical_tail(words, lane):
    """Eight logical columns occupy exactly one physical MUX8 row."""
    if len(words) != 8 or lane not in range(4):
        raise ValueError('one native eight-column row required')
    row = 0
    for col, word in enumerate(words):
        part = (word >> (266*lane)) & ((1 << 266)-1)
        for shift, mask in P._SPREAD_MASKS:
            part = (part | (part << shift)) & mask
        row |= part << col
    return row


def repack(data, words, lane, *, tail_base=TAIL):
    """Insert eight logical columns even when their base crosses a MUX8 row."""
    if len(words) != 8 or lane not in range(4) or tail_base not in (3816,3922):
        raise ValueError('qualified eight-word native tail location required')
    rows = data.decode().splitlines()
    if len(rows) != 512:
        raise ValueError('native tail reservation is not empty')
    values = [int(row,16) for row in rows]
    for r in range(tail_base//8,512):
        cols = range(tail_base%8,8) if r == tail_base//8 else range(8)
        mask = sum(1 << (8*bit+col) for bit in range(266) for col in cols)
        if values[r] & mask:
            raise ValueError('native tail reservation is not empty')
    for col, word in enumerate(words):
        addr = tail_base+col
        part = (word >> (266*lane)) & ((1<<266)-1)
        for shift, mask in P._SPREAD_MASKS:
            part = (part | (part << shift)) & mask
        values[addr//8] |= part << (addr%8)
    for r in range(tail_base//8,(tail_base+7)//8+1):
        rows[r] = f'{values[r]:0532x}'
    return ('\n'.join(rows)+'\n').encode()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--images',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--emit-masks',action='store_true')
    ap.add_argument('--head-stage37',action='store_true')
    a=ap.parse_args();raw=a.manifest.read_bytes();manifest=json.loads(raw);tail=tails(manifest,head_stage37=a.head_stage37)
    tail_base=(P.STAGES+int(a.head_stage37))*P.STRIDE
    receipt=json.loads((a.images/'receipt.json').read_text())
    if receipt['manifest_sha256'] != hashlib.sha256(raw).hexdigest() or receipt['used_rows'] != tail_base:
        raise ValueError('original image receipt is not bound to this native manifest')
    a.out.mkdir(parents=True,exist_ok=False)
    images={}
    for sid in range(12):
        for lane in range(4):
            name=f'table_s{sid}_m{lane}.viamap.hex';data=(a.images/name).read_bytes()
            if hashlib.sha256(data).hexdigest() != receipt['images'][name]:
                raise ValueError('original mask differs from source receipt: '+name)
            new=repack(data,tail[sid],lane,tail_base=tail_base);images[name]=hashlib.sha256(new).hexdigest()
            if a.emit_masks:(a.out/name).write_bytes(new)
    result=dict(schema='opentallas.qwen.monitor-tail-candidate.v1',
        qualification='SOURCE PACKING ONLY; loader90read, source-window, monitor/caller and physical gates OPEN',
        manifest_sha256=hashlib.sha256(raw).hexdigest(),original_receipt_sha256=hashlib.sha256((a.images/'receipt.json').read_bytes()).hexdigest(),
        emit_masks=a.emit_masks,stage_stride=106,used_rows=tail_base+8,free_rows=4096-tail_base-8,
        changed_physical_row=tail_base//8,changed_physical_rows=list(range(tail_base//8,(tail_base+7)//8+1)),tail_base=tail_base,head_stage37=a.head_stage37,reads_per_user_window=90,added_occupied_edges=2,
        global_pidx_rule='128*user+[12,13,14,15]; only actual selected monitor calls may be remapped',
        source_pidx=SOURCE_PC,images=images,
        tail_words={str(sid):[f'{w:0266x}' for w in words] for sid,words in tail.items()})
    (a.out/'candidate.json').write_text(json.dumps(result,indent=2)+'\n')
    print('MONITOR_TAIL_SOURCE_CANDIDATE masks',48 if a.emit_masks else 0,'used_rows',tail_base+8,'global_window_OPEN')


if __name__=='__main__':main()
