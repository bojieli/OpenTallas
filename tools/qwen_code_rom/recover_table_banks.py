#!/usr/bin/env python3
"""Recover raw native TP8 banks for genuine table lowering; never build code masks.

Use the released emitters unchanged. A layer subset is an explicit admission
pilot, not a complete programme. Existing emitted files must match their saved
manifest before reuse. Run under the fleet admission guard.
"""
import argparse,hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/qwen_code_rom')]
import recover_rank as R


def verify_existing(directory,manifest_name,snapshot,guard):
    guard(snapshot)
    p=directory/manifest_name
    if not p.exists():return False
    record=json.loads(p.read_text())
    if record['checkpoint_revision']!=snapshot.name:
        raise ValueError(f'existing image has different checkpoint {p}')
    for name,want in record['image_sha256'].items():
        f=directory/name
        if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=want:
            raise ValueError(f'existing image differs; preserve and diagnose {f}')
    if manifest_name!='head_rom.json':
        # A pinned manifest from the same checkpoint can still contain the
        # emitter's wrong instruction defaults. Reuse only the selected native ABI.
        import hdc_qwen_fullshape_program_w12 as F
        profile=F.profile(record['die'],matrix_rows=record['matrix_layout'],
                          post_scale_bases=record['post_tp_scale_bases'])
        for name,key in [('program.hex','program_hex'),('segments.hex','descriptor_hex')]:
            native=('\n'.join(profile[key])+'\n').encode()
            if hashlib.sha256(native).hexdigest()!=record['image_sha256'][name]:
                raise ValueError(f'existing image uses a different native instruction profile; preserved {p}')
    return True


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--snapshot',type=Path,required=True);ap.add_argument('--banks',type=Path,required=True)
    ap.add_argument('--rank',type=int,choices=range(8),required=True)
    ap.add_argument('--layers',help='explicit comma-separated admission pilot; default all36')
    ap.add_argument('--skip-head',action='store_true',help='explicit layer-only pilot; not complete recovery')
    ap.add_argument('--receipt',type=Path,required=True);a=ap.parse_args()
    layers=list(range(36))if a.layers is None else [int(v)for v in a.layers.split(',')]
    if not layers or len(set(layers))!=len(layers)or any(v not in range(36)for v in layers):ap.error('distinct legal layers required')
    os.environ['QWEN_O4_TP']='8';os.environ['QWEN_O4_GROUPS']='3072'
    # These are part of the protected native TP8 instruction ABI, not emitter defaults.
    os.environ['QWEN_O4_AR_WORDS']='256';os.environ['HDC_SU_WIDTH']='64'
    import hdc_qwen_layer0_rom_w12 as L
    import qwen_o4_head_rom_w12 as H
    guard=R.validate_once(a.snapshot,L.LOCK,L.pinned_snapshot);L.pinned_snapshot=guard;H.pinned_snapshot=guard
    stages=[]
    for layer in layers:
        d=a.banks/f'images/layer{layer}/die{a.rank}'
        reused=verify_existing(d,f'layer{layer}_rom.json',a.snapshot,guard)
        if not reused:L.emit(a.snapshot,d,a.rank,layer,True)
        stages.append(dict(layer=layer,metadata=str(d/f'layer{layer}_rom.json'),reused=reused))
        print('RAW_LAYER_READY',a.rank,layer,'REUSED'if reused else'EMITTED',flush=True)
        guard(a.snapshot)
    if not a.skip_head:
        d=a.banks/f'head_images/rank{a.rank}'
        reused=verify_existing(d,'head_rom.json',a.snapshot,guard)
        if not reused:H.emit(a.snapshot,d,a.rank)
        print('RAW_HEAD_READY',a.rank,'REUSED'if reused else'EMITTED',flush=True)
    guard(a.snapshot)
    r=dict(schema='opentallas.qwen.raw-table-bank-recovery.v1',checkpoint_revision=a.snapshot.name,
           source_lock_sha256=hashlib.sha256(L.LOCK.read_bytes()).hexdigest(),rank=a.rank,
           complete_raw_rank=sorted(layers)==list(range(36))and not a.skip_head,
           native_profile=dict(QWEN_O4_TP=8,QWEN_O4_GROUPS=3072,QWEN_O4_AR_WORDS=256,HDC_SU_WIDTH=64),
           layers=stages,head_included=not a.skip_head,code_masks_generated=False,
           next_pass='tools/qwen_layerbench/checkpoint_table_streams.py using actual selected attention owners',
           scope='Genuine emitted data recovery only; no programme installation or RTL verdict')
    a.receipt.parent.mkdir(parents=True,exist_ok=True);a.receipt.write_text(json.dumps(r,indent=2)+'\n')
    print('RAW_TABLE_BANK_RECOVERY_READY',flush=True)
if __name__=='__main__':main()
