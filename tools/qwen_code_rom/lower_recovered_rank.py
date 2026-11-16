#!/usr/bin/env python3
"""Lower a completed raw TP8 rank into genuine candidate transformer+HEAD tables.

Read actual36-layer plus HEAD inventory; partial chunk receipt labels are not a
completion authority. Missing stages stop before any table output. No fabricated
coefficients, zero-filled missing stages, code-mask build or installation.
"""
import argparse,hashlib,json,os,sys,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/qwen_layerbench'),str(ROOT/'tools/qwen_tokfunc/current_path')]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2)+'\n')

def inventory(banks,rank):
    stages=[];missing=[];revision=set();locks=set()
    for layer in list(range(36))+['head']:
        d=banks/(f'head_images/rank{rank}'if layer=='head'else f'images/layer{layer}/die{rank}')
        p=d/('head_rom.json'if layer=='head'else f'layer{layer}_rom.json')
        if not p.is_file():missing.append(str(p));continue
        
        try:m=json.loads(p.read_text())
        except json.JSONDecodeError:
            missing.append(str(p)+' [metadata write in progress]');continue
        if m['die']!=rank or m['tp']!=8 or (layer!='head'and m['layer']!=layer):raise ValueError('actual raw stage/rank geometry mismatch')
        revision.add(m['checkpoint_revision']);locks.add(m['checkpoint_lock_sha256'])
        files={}
        required=['matrix_int8.hex','matrix_scale_bf16.hex']if layer=='head'else['program.hex','segments.hex','crom.hex','matrix_int8.hex','matrix_scale_bf16.hex']
        for name in required:
            f=d/name
            if not f.is_file():missing.append(str(f));continue
            if name not in m['image_sha256']:raise ValueError('actual raw manifest lacks emitted file identity')
            files[name]=dict(bytes=f.stat().st_size,sha256_from_emitter=m['image_sha256'][name])
        stages.append(dict(stage=37 if layer=='head'else layer+1,metadata=str(p),metadata_sha256=sha(p),files=files))
    if missing:return dict(status='WAITING_ACTUAL_RAW_INPUTS',rank=rank,missing=missing,stages_present=len(stages))
    if len(revision)!=1 or len(locks)!=1:raise ValueError('mixed raw checkpoint identities')
    return dict(schema='opentallas.qwen.complete-raw-rank-inventory.v1',status='ACTUAL36_PLUS_HEAD_PRESENT',
                rank=rank,stages=stages,checkpoint_revision=revision.pop(),checkpoint_lock_sha256=locks.pop(),
                completion_authority='actual36 layer metadata+all emitted files andactualHEAD; partial chunk labels ignored')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--banks',type=Path,required=True);ap.add_argument('--rank',type=int,choices=range(8),required=True)
    ap.add_argument('--snapshot',type=Path);ap.add_argument('--attention-contract',type=Path)
    ap.add_argument('--lowering-commit');ap.add_argument('--out',type=Path)
    ap.add_argument('--selected-identity',type=Path,help='pinned current-candidate loader identities; proposal only')
    ap.add_argument('--inventory-only',action='store_true');a=ap.parse_args()
    inv=inventory(a.banks,a.rank)
    if a.inventory_only:print(json.dumps(inv));return 0 if inv['status']=='ACTUAL36_PLUS_HEAD_PRESENT' else 2
    if inv['status']!='ACTUAL36_PLUS_HEAD_PRESENT':print(json.dumps(inv));return 2
    if not all([a.snapshot,a.attention_contract,a.lowering_commit,a.out]):ap.error('lowering requires snapshot,attention-contract,lowering-commit,out')
    if a.out.exists():raise ValueError('output already exists; preserve prior results and use a fresh destination')
    contract=json.loads(a.attention_contract.read_text());att=contract['owners']
    if att!=[0,1,3,5]or contract.get('final_bound_adoption')is not False:raise ValueError('explicit native r6 candidate owner contract required')
    if len(a.lowering_commit)!=40 or any(c not in'0123456789abcdef'for c in a.lowering_commit):raise ValueError('exact committed lowering source required')
    if a.snapshot.name!=inv['checkpoint_revision']:raise ValueError('HEAD and transformer snapshot identities differ')
    os.environ.update(QWEN_O4_TP='8',QWEN_O4_GROUPS='3072',QWEN_O4_AR_WORDS='256',HDC_SU_WIDTH='64',DV2_S8DIE='1')
    import checkpoint_table_streams as C,programme_lower as L,programme_store as P
    import dv_lower as D,head_boot_data as HB,head_norm_object as HN,head_source_lease as HL
    temp=a.out.with_name(a.out.name+f'.building_{os.getpid()}');temp.mkdir(parents=True,exist_ok=False)
    try:
        dump(temp/'raw_inventory.json',inv);dump(temp/'attention_owner_candidate.json',contract)
        own=D.ownership(slice_rtl='s8');stages=[]
        for layer in range(36):
            stage=C.lower_image(a.banks/f'images/layer{layer}/die{a.rank}',layer,a.rank,own,att)
            stages.append(stage);print('LOWERED_REAL_STAGE',a.rank,layer+1,flush=True)
        streams=dict(schema='opentallas.qwen.native-table-streams.v1',
            source=dict(lowering_commit=a.lowering_commit,checkpoint_sha256=inv['checkpoint_lock_sha256']),
            rank=a.rank,attention_owners=att,attention_contract_sha256=sha(a.attention_contract),
            attention_scope='ANALYTICAL_NATIVE_S8_ZERO_PARENT_CANDIDATE; final bound adoption false',
            ownership=own,btab_compact=1,stages=stages)
        dump(temp/'streams.json',streams)
        manifest,cert=L.compile_inputs(streams,btab_compact=1)
        # programme_lower hashes the exact sorted-key serialization of this certificate.
        (temp/'user_relocation36.json').write_text(json.dumps(cert,sort_keys=True)+'\n')
        dump(temp/'mu_table_input36.json',manifest)
        report=HL.census(temp/'mu_table_input36.json');alloc=HL.allocation([report])
        dump(temp/'source_lease.json',dict(status='CANDIDATE_SOURCE_ONLY',allocation=alloc,actual_source_census=report))
        hd=a.banks/f'head_images/rank{a.rank}';meta=json.loads((hd/'head_rom.json').read_text())
        plan=json.loads((D.ROOT/D.PLAN).read_text())
        if any(meta['geometry'][k]!=plan['head_geometry'][k]for k in ['rows','columns','split','rounds','tiles_per_round']):raise ValueError('actual HEAD geometry differs from source ownership')
        bt,_=HB.head_tables(meta,hd/'matrix_scale_bf16.hex',own)
        bits,norm_source=HB.final_norm(a.snapshot)
        gain=temp/'head_final_norm_crom.hex';gain.write_text(''.join(f'{v:016x}\n'for v in bits))
        head_meta=dict(rank=a.rank,checkpoint_revision=meta['checkpoint_revision'],norm_source=norm_source)
        HN.gains(gain,head_meta) # exact original tensor bytes, no invented gain values
        obj=HN.build(bits,own);obj['sources']=dict(checkpoint_revision=meta['checkpoint_revision'],recovered_gain_tensor=norm_source,gain_words_sha256=sha(gain),ownership=own['sources'])
        stage37=HL.link_stage(obj,bt,alloc)
        dump(temp/'head_boot_data.json',head_meta);dump(temp/'head_btab.json',bt);dump(temp/'head_norm_object.json',obj);dump(temp/'head37_stage.json',stage37)
        full,head_cert=HL.assemble_manifest(manifest,stage37,alloc,parent_manifest_sha256=sha(temp/'mu_table_input36.json'),lowering_commit=a.lowering_commit)
        raw=(json.dumps(head_cert,sort_keys=True,separators=(',',':'))+'\n').encode();(temp/'user_relocation.json').write_bytes(raw)
        dump(temp/'mu_table_input.json',full)
        images=P.logical_images(full,head_stage37=True);masks=temp/'masks';masks.mkdir();hashes={}
        for sid,words in enumerate(images):
            for k in range(4):
                name=f'table_s{sid}_m{k}.viamap.hex';p=masks/name
                p.write_text(''.join(f'{x:0532x}\n'for x in P.physical_rows(words,k)));hashes[name]=sha(p)
        if a.selected_identity:
            import table_roms as T
            identity=json.loads(a.selected_identity.read_text())
            dump(temp/'selected_source_identity.json',identity)
            dump(temp/'physical_mask_assignment.json',T.physical_assignment(identity,hashes))
        receipt=dict(schema='opentallas.qwen.recovered-native-rank-tables.v1',status='COMPLETE_GENUINE_SOURCE_TABLES_CANDIDATE_ONLY',
            rank=a.rank,actual_stages=37,images=hashes,manifest_sha256=sha(temp/'mu_table_input.json'),
            source_commit=a.lowering_commit,raw_inventory_sha256=sha(temp/'raw_inventory.json'),
            checkpoint_lock_sha256=inv['checkpoint_lock_sha256'],attention_owners=att,
            attention_contract_sha256=sha(a.attention_contract),final_bound_adoption=False,
            complete_transformer_programme=True,HEAD_STAGE37_enabled_in_RTL=False,mask_installation=False,
            qualification='Genuine37-stage tables only; source/body/window/clock/bound calendar qualification remains separate')
        dump(temp/'receipt.json',receipt);temp.rename(a.out)
        print('REAL_RANK_TABLES_READY',a.rank,'masks48 stages37 candidate_only',flush=True)
    except BaseException:
        (temp/'failure.txt').write_text(traceback.format_exc());raise
    return 0
if __name__=='__main__':raise SystemExit(main())
