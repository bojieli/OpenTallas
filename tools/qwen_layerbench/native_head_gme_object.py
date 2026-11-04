#!/usr/bin/env python3
"""Emit native-compatible GME/IB/XPF source objects from actual HEAD programs.

Preserves the four genuine <=8-round ROM descriptors and END. Three legacy
normalization words are removed; native H is a separate qualified producer.
No fixed-issue time, XPF time, programme row or active image is fabricated.
"""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import hdc_isa as ISA
import dv_lower_xhead as X


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def build(plan_path,metadata,boot_metadata):
    plan=json.loads(plan_path.read_text())
    if (plan['tp'],plan['groups'],plan['layers'])!=(8,3072,36):raise ValueError('actual TP8 source plan required')
    ranks=[]
    for rank,profile in enumerate(plan['head_profiles']):
        mp=metadata/f'rank{rank}/head_rom.json';meta=json.loads(mp.read_text())
        boot=json.loads((boot_metadata/f'rank{rank}/head_boot_data.json').read_text())
        if sha(mp)!=boot['source_sha256']['head_rom.json'] or meta['checkpoint_revision']!=boot['checkpoint_revision']:
            raise ValueError('actual recovered weight metadata differs from existing HEAD source')
        if (meta['tp'],meta['groups'],meta['die'],meta['rows'],meta['code_words'],meta['scale_words'])!=(8,3072,rank,18992,1600,1200):
            raise ValueError('complete genuine HEAD bank geometry required')
        words=[int(x,16)for x in profile['program_hex']];fields=[ISA.decode(x)for x in words]
        if [f['unit']for f in fields]!=[2,2,2,1,1,1,1,0]:raise ValueError('actual fourchunk HEAD source required')
        out=[];code_ranges=[];scale_ranges=[];rows=0
        for pc in range(3,7):
            f=fields[pc]
            if f['me_wsrc'] or not f['me_amax'] or f['me_split']!=9 or f['me_k']!=8 or f['me_xbase']!=8192 or not 1<=f['me_tiles']<=8 or any(v for k,v in f.items()if k.startswith('me_d_')):
                raise ValueError('unsupported actual native ROM/X geometry')
            code=sorted({f['me_wbase']+r*f['me_ts']+k*f['me_ks']+(j>>f['me_jsh'])*f['me_js']for r in range(f['me_tiles'])for k in range(f['me_k'])for j in range(8)})
            cr=[min(code),max(code)+1];sr=[f['me_wcs'],f['me_wcs']+f['me_tiles']*6*8]
            if code!=list(range(*cr)) or cr[1]>1600 or sr[1]>1200:raise ValueError('native weight bounds differ')
            if f['me_row0']!=rows or f['me_amc']!=int(pc!=3):raise ValueError('actual chunk row/AMAX continuation differs')
            code_ranges.append(cr);scale_ranges.append(sr);rows+=f['me_nout']
            g=dict(f,me_xbase=0);word=ISA.encode(**g)
            if ISA.decode(word)!=g:raise ValueError('native GME word roundtrip differs')
            footprint={g['me_xbase']+c*g['me_xcs']+k*g['me_xks']for c in range(1<<g['me_split'])for k in range(g['me_k'])}
            if footprint!=set(range(4096)):raise ValueError('HEAD input does not match actual H producer footprint')
            out.append(dict(source_pc=pc,relative_pc=pc-3,unit=1,word_hex=f'{word:0256x}',ib379_hex=f'{X.pack_ib(g):095x}',
                rounds=g['me_tiles'],rows=g['me_nout'],row0=g['me_row0'],amc=g['me_amc'],local_code=cr,local_scale=sr,
                resident_code=[18432+x for x in cr],resident_scale=[29376+x for x in sr],issue_symbol=f'HEAD_GME_CHUNK{pc-3}_ISSUE'))
        if rows!=18992 or code_ranges!=[[0,512],[512,1024],[1024,1536],[1536,1600]] or scale_ranges!=[[0,384],[384,768],[768,1152],[1152,1200]]:
            raise ValueError('actual four chunks do not cover complete HEAD bank exactly')
        out.append(dict(source_pc=7,relative_pc=4,unit=0,word_hex=f'{words[-1]:0256x}',issue_symbol='HEAD_GME_END_ISSUE'))
        x72=X.pack_xpf72(dict(fields[3],me_xbase=0))
        xfixed=(37<<86)|(2<<84)|(17<<72)|x72
        ranks.append(dict(rank=rank,global_vocabulary_row0=meta['row0'],programme_words=out,
            weight_metadata_sha256=sha(mp),genuine_code_image_sha256=meta['image_sha256']['matrix_int8.hex'],genuine_scale_image_sha256=meta['image_sha256']['matrix_scale_bf16.hex'],
            xpf=dict(xpf72_hex=f'{x72:018x}',fixed_low92_hex=f'{xfixed:023x}',producer_pidx=17,stage=37,producer_unit=2,footprint=[0,4096],
                arm_symbol='HEAD_XPF_ARM',producer_issue_symbol='HEAD_MONITORED_APPLY_ISSUE',first_write_symbol='HEAD_FIRST_XTAP_WRITE'),
            GME_slots=5,GME_slot_capacity=8,G_XPF_slots=1,G_XPF_slot_capacity=3))
    if len(ranks)!=8:raise ValueError('eight actual source ranks required')
    return dict(schema='opentallas.qwen.native-head-gme-object.v1',status='RELOCATABLE_NOT_EXECUTABLE',stage=37,ranks=ranks,
        source_plan_sha256=sha(plan_path),legacy_SU_words_removed=3,native_H_producer='qualified native apply-H pidx16, dedicated monitored copy17',
        monitor_contract='actual GI su_obs only observes user0; copy17 is issued once in primary HEAD while other H calls retain16',
        monitor_copy='pair8 upper17 duplicates lower16 only at selected earliest H producer slice; same peruser relocation, zero added ROM pair slots',
        source_bug_avoided='legacy ctlm_image.lm_head_programme uses6 tiles_per_round as me_tiles; actual native descriptor requires four chunks8+8+8+1, not unsupported25fusion',
        programme_append='actual current programme metadata/base and free PW range must be joined before allocation',
        physical_adoption=False,executable=False,missing=['current82190/f79 programme PW/meta source join','perchunk native GO/end/live-X epoch dates','native commandfront/HR/XPF transport and headtap/Xfill lease','actual STN chunk receiver/btab/global vocabulary row mapping','single monitored17 H copy/caller/source installation','native GME/XPF control gate and coherent programme replay'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('plan','metadata','boot-metadata','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();r=build(a.plan,a.metadata,a.boot_metadata);a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(status=r['status'],ranks=len(r['ranks']),GME_slots=5,XPF_slots=1)))
