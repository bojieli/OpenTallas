#!/usr/bin/env python3
"""Pack immutable candidate HEAD37 table cohorts; never activate a caller.

Every transformer prefix must remain identical to its completed real table
masks. Genuine HEAD BTAB and final gains are linked into unused resident native
regions. Numerical execution, publication dates and canonical adoption are not
claimed by this source-image packer.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import head_source_lease as H
import programme_store as P


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def raw_json(value):return (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--native',type=Path,required=True);ap.add_argument('--head-data',type=Path,required=True)
    ap.add_argument('--object',type=Path,required=True);ap.add_argument('--lease',type=Path,required=True)
    ap.add_argument('--source-commit',required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();obj=json.loads(a.object.read_text());lease=json.loads(a.lease.read_text());alloc=lease['allocation']
    if len(lease['selected_sources'])!=8:raise ValueError('all8 actual source footprints required')
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'.keep').touch();done=[]
    for rank in range(8):
        base=a.native/f'rank{rank}';head=a.head_data/f'rank{rank}'
        mp=base/'lowered/mu_table_input.json';cp=base/'lowered/user_relocation.json'
        manifest=json.loads(mp.read_text());cert=json.loads(cp.read_text());meta=json.loads((head/'head_boot_data.json').read_text())
        if sha(mp)!=lease['selected_sources'][rank]['manifest_sha256'] or sha(cp)!=manifest['source']['user_relocation_certificate_sha256']:
            raise ValueError(f'actual source/certificate changed rank{rank}')
        if meta['rank']!=rank or meta['checkpoint_revision']!=obj['sources']['checkpoint_revision'] or {s['checkpoint_revision'] for s in cert['source_stages']}!={meta['checkpoint_revision']}:
            raise ValueError('native transformer and HEAD checkpoint sources differ')
        if sha(head/'head_final_norm_crom.hex')!=obj['sources']['gain_words_sha256']:
            raise ValueError('HEAD final gains differ between ranks/source object')
        stage=H.link_stage(obj,json.loads((head/'head_btab.json').read_text()),alloc)
        out,certificate=H.assemble_manifest(manifest,stage,alloc,parent_manifest_sha256=sha(mp),lowering_commit=a.source_commit)
        images=P.logical_images(out,head_stage37=True)
        dest=a.out/f'rank{rank}';dest.mkdir();masks=dest/'masks';masks.mkdir()
        (dest/'head37_stage.json').write_bytes(raw_json(stage));(dest/'mu_table_input.json').write_bytes(raw_json(out))
        (dest/'user_relocation.json').write_bytes(raw_json(certificate))
        if sha(dest/'user_relocation.json')!=out['source']['user_relocation_certificate_sha256']:
            raise AssertionError('new certificate serialization differs')
        hashes={}
        for sid,words in enumerate(images):
            for lane in range(4):
                name=f'table_s{sid}_m{lane}.viamap.hex'
                before=(base/'masks'/name).read_text().splitlines()
                after=[f'{w:0532x}' for w in P.physical_rows(words,lane)]
                if len(before)!=512 or before[:477]!=after[:477] or any(int(w,16) for w in before[477:]):
                    raise ValueError(f'completed transformer prefix changed rank{rank}/{name}')
                (masks/name).write_text('\n'.join(after)+'\n');hashes[name]=sha(masks/name)
        result=dict(rank=rank,status='SOURCE_IMAGES_ONLY_NOT_ACTIVATED',masks=len(hashes),
                    transformer_rows_unchanged=3816,head_rows=[3816,3922],monitor_enabled=False,
                    gain_base=alloc['gain_base'],apply_pidx=alloc['apply_pidx'],
                    manifest_sha256=sha(dest/'mu_table_input.json'),certificate_sha256=sha(dest/'user_relocation.json'),
                    images=hashes)
        (dest/'receipt.json').write_bytes(raw_json(result));done.append(result)
        print(f'HEAD37_SOURCE_PACKED rank{rank} masks48 old_prefix3816_exact',flush=True)
    result=dict(schema='opentallas.qwen.native-head-source-volume.v1',status='SOURCE_IMAGES_ONLY_NOT_ACTIVATED',
                ranks=8,masks=384,cohorts=done,source_commit=a.source_commit,
                object_sha256=sha(a.object),lease_sha256=sha(a.lease),
                native_HEAD_arithmetic='NOT_RUN',caller_and_publication_dates='NOT_INSTALLED',canonical_adoption=False)
    (a.out/'receipt.json').write_bytes(raw_json(result));print('HEAD37_SOURCE_VOLUME_PASS masks384 no_activation',flush=True)

if __name__=='__main__':main()
