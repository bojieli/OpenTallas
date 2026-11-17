#!/usr/bin/env python3
"""Pack genuine HEAD37-only table masks and a relocatable LOCAL4 reservation.

Stages1..36 remain absent, with invalid records. This is never a full programme
or an installed image. It cannot enable HEAD_STAGE37 or choose upstream dates.
"""
import argparse,gzip,hashlib,json
from pathlib import Path
import programme_store as P

STAGE_SHA='03fa2dcff20b67032c63cf05f92f52454bc3d6bb9700d979a67f69038f482117'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def pack(stage):
    if stage.get('stage')!=37 or sorted(s['slice'] for s in stage['slices'])!=list(range(12)):
        raise ValueError('genuine complete HEAD37 cohort required')
    images=[[0]*P.DEPTH for _ in range(12)];counts=[]
    for s in stage['slices']:
        sid=s['slice'];pu=s['prog_users']
        if len(pu)!=4 or any(len(rows)!=1 or rows[0]['addr']!=8 for rows in pu):
            raise ValueError('resident apply-H pair8 must be explicit for all4 users')
        if len(s['btab'])!=P.HEAD_BTAB_COUNTS[sid] or len(s['crom'])!=P.HEAD_CROM_COUNTS[sid]:
            raise ValueError('actual native HEAD slice shape differs')
        groups=[(3,u*P.PROG,P.PROG,pu[u])for u in range(4)]
        groups += [(2,24,P.HEAD_BTAB,s['btab']),(1,24+P.HEAD_BTAB,P.HEAD_CROM,s['crom'])]
        for kind,start,cap,records in groups:
            if len({r['addr']for r in records})!=len(records) or len(records)>cap:
                raise ValueError('overlapping or oversized native table cohort')
            for i,r in enumerate(records):
                word=P.encode(kind,r['addr'],r['payload_hex'],head=True)
                if kind==1 and not 68<=r['addr']<92:raise ValueError('resident gain68..91 required')
                images[sid][3816+start+i]=word
        counts.append(dict(slice=sid,valid_records=sum(bool(x)for x in images[sid]),
                           user_load_valid_counts=[1+len(s['btab'])+len(s['crom'])]*4))
    return images,counts

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stage',type=Path,required=True);ap.add_argument('--identity',type=Path,required=True)
    ap.add_argument('--lease',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--rom-top',default='tb_headtable.u_qc');a=ap.parse_args()
    if sha(a.stage)!=STAGE_SHA:raise ValueError('genuine committed HEAD stage identity differs')
    ident=json.loads(a.identity.read_text());lease=json.loads(a.lease.read_text())
    if sorted(r['slice']for r in ident['loaders'])!=list(range(12)):raise ValueError('actual12 selected source identities required')
    if lease['allocation']['gain_base']!=1088 or lease['allocation']['apply_pidx']!=16:
        raise ValueError('actual source footprint allocation differs')
    stage=json.loads(a.stage.read_text());images,counts=pack(stage)
    a.out.mkdir(parents=True,exist_ok=False);m=a.out/'head37_only_masks';m.mkdir();hashes={};compressed={}
    for sid,words in enumerate(images):
        for lane in range(4):
            rows=P.physical_rows(words,lane)
            # Check every actual logical word against the physical bit-interleave.
            for addr,word in enumerate(words):
                row=rows[addr//8];got=sum(((row>>(8*i+addr%8))&1)<<i for i in range(266))
                if got!=(word>>(266*lane))&((1<<266)-1):raise AssertionError('mask bit mapping differs')
            name=f'table_s{sid}_m{lane}.viamap.hex';data=(''.join(f'{r:0532x}\n' for r in rows)).encode()
            hashes[name]=hashlib.sha256(data).hexdigest();z=gzip.compress(data,mtime=0)
            (m/(name+'.gz')).write_bytes(z);compressed[name+'.gz']=hashlib.sha256(z).hexdigest()
    scopes={f'{a.rom_top}.{r["actual"]}.u_tload.u_ld.m{k}':f'table_s{r["slice"]}_m{k}.viamap.hex'for r in ident['loaders']for k in range(4)}
    if len(scopes)!=48 or len(set(scopes.values()))!=48:raise ValueError('distinct actual-scope mask mapping required')
    (a.out/'selected_source_identity.json').write_text(json.dumps(ident,indent=2)+'\n')
    (a.out/'scope_binding.json').write_text(json.dumps(dict(schema='opentallas.qc-head37-mask-scope.v1',scopes=scopes,
         source_identity_sha256=sha(a.identity),native_release_identity_valid=ident['native_release_identity_valid'],
         simulation_scope_only=True,global_programme_complete=False),indent=2)+'\n')
    window=dict(schema='opentallas.qwen.head37-local4-window.v1',status='RELOCATABLE_NOT_EXECUTABLE',
        stage=37,user='separate invocation for each0..3; one stored opcode',opcode_hex=f'{((14<<112)|(37<<4)|9):029x}',
        local_range=dict(first=1012,count=1,required_nent=1013,maximum_nent=1023),
        table_records=dict(first=3816,end_exclusive=3922,reads_per_user=88,valid_records_by_slice=counts),
        selected_source_profile=dict(CAPTURE_STAGE=0,LOCAL_JOIN=0,WE_COPIES=34,HEAD_STAGE37=0,
            defines=['OT_QFD_UP4_CK_ENTRIES','OT_S8_CROM_ALIGN','OT_QC_SRAM_MIF'],
            authority='treeJ/physical/die_plan/qwen_compute/qc_start_1106/runtime/asbuilt_sw2_pv.json',
            authority_sha256='86ede4003ca435effaa41f06b0bc9701744fe1340d173f8b1d8f3b8694f8cc34'),
        relative_loader_write_contract=dict(origin='native qfd_dv_table_rom_loader start sample',first=3,last=90,
             authority='qfd_dv_slice_tload source contract; selected C0/LOCAL0/WE34',reservation='exclusive through final write; no stream-origin table write during loader window'),
        requires_opt_in=['CTLM LOCAL4 acceptance37 in actual source-complete selected wrapper','HEAD_STAGE37 in each selected loader',
            'current source/profile native HEAD37 install witness','actual per-slice mask assignment or simulation scope overlay'],
        unresolved=['absolute LOCAL37 CALR start and per-user window','actual transport from CALR to loader start',
            'last local table write to native VM/CROM/PROG visibility','final residual X/RSTD lease and apply-H issue join'],
        upstream_stages_absent=list(range(1,37)),global_HEAD_STAGE37_enabled=False)
    (a.out/'local4_window.json').write_text(json.dumps(window,indent=2)+'\n')
    receipt=dict(schema='opentallas.qwen.genuine-head37-only-mask-packet.v1',status='SOURCE_ONLY_NOT_INSTALLED',
        stage_sha256=sha(a.stage),lease_sha256=sha(a.lease),identity_sha256=sha(a.identity),rank=0,
        logical_rows=[3816,3922],images=hashes,compressed_images=compressed,
        invalid_absent_stage_range=[0,3816],absent_stages=list(range(1,37)),
        complete_transformer_programme=False,native_release_identity_valid=ident['native_release_identity_valid'],
        qualification='Packing and actual selected-source identity only; HEAD37 loader/CTLM enable remains off')
    (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('HEAD37_ONLY_PACKET_READY masks48 distinct_scope48 stages1_36_ABSENT release_identity_BLOCKED')
if __name__=='__main__':main()
