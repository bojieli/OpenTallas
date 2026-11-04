#!/usr/bin/env python3
"""Prepare one native SU/VM plus real stream-tile HEAD component packet.

Uses the completed residual2 native projection unchanged, replacing only its
bench and adding the production stream tile. No job or image is activated.
"""
import argparse,hashlib,json,shutil
from pathlib import Path
import programme_store as P
import dv_lower as D
import dv_lower_vec as V


def prepare(base,stage,stream,out):
    m=json.loads(stage.read_text())
    if m.get('stage')!=37 or sorted(s['slice']for s in m['slices'])!=list(range(12)):
        raise ValueError('complete actual HEAD37 linked stage required')
    out.mkdir(parents=True,exist_ok=False);dest=out/'input';dest.mkdir();sources=[];hashes={}
    for i,name in enumerate((base/'source.f').read_text().splitlines()):
        src=Path(name)
        if not src.exists():src=base/'input'/src.name
        if src.name=='tb_mu_native.sv':continue
        p=dest/f'{i:03d}_{src.name}';shutil.copy2(src,p);sources.append(p);hashes[src.name]=hashlib.sha256(p.read_bytes()).hexdigest()
    p=dest/'qfd_dv_stream_tile.sv';shutil.copy2(stream,p);sources.append(p)
    initial=[]
    for sl in m['slices']:
        s=sl['slice'];n=len(sl['crom'])*16
        initial.append(f'nwords[{s}]={n};')
        for u,records in enumerate(sl['prog_users']):
            if len(records)!=1 or records[0]['addr']!=8:raise ValueError('actual resident pair8 required')
            payload=int(records[0]['payload_hex'],16);f=D.su_unpack(payload&((1<<457)-1))
            if payload>>512 or f['c']!=1088+2048*u or f['b']!=400+4096*u or f['a']!=4096*u or f['nin']*f['nout']!=n or f['ma']!=V.MA_AB or not f['mc'] or not f['csrc']:
                raise ValueError('linked native HEAD instruction or allocation differs')
            initial.append(f"prog[{s}][{u}]=1024'h{payload:0256x};")
            raw=dict(f);raw.update(ma=0,mc=0)
            initial.append(f"rawprog[{s}][{u}]=1024'h{D.su_word(**raw):0256x};")
        for r in sl['crom']:
            P.encode(1,r['addr'],r['payload_hex']);row=r['addr']-68
            if row<0 or row>=24:raise ValueError('HEAD resident row bounds')
            initial.append(f"gains[{s}][{row}]=1024'h{r['payload_hex']};")
            val=int(r['payload_hex'],16)
            for j in range(16):
                g=(val>>(64*j))&0xffffffff
                if not 0<(g>>23)&255<250:raise ValueError('finite normal model gain required')
                # X=2**(u+1), RSTD=0.5: first product is exactly2**u;
                # scaling each normal FP32 checkpoint gain changes exponent only.
                initial.append(f"gold[{s}][{row*16+j}]=32'h{g:08x};")
    tb=Path(__file__).with_name('tb_head_apply_native.sv').read_text().replace('// SOURCE_INITIALIZERS','\n'.join(initial))
    p=dest/'tb_mu_native.sv';p.write_text(tb);sources.append(p)
    (out/'source.f').write_text(''.join(str(p.relative_to(out))+'\n'for p in sources))
    shutil.copy2(base/'defines.f',out/'defines.f')
    shutil.copy2(Path(__file__).with_name('run_head_apply_gate.sh'),out/'run_gate.sh')
    receipt=dict(status='PREP_ONLY_NOT_LAUNCHED',unchanged_native_sources=hashes,
        stage_sha256=hashlib.sha256(stage.read_bytes()).hexdigest(),stream_source_sha256=hashlib.sha256(stream.read_bytes()).hexdigest(),
        source_files=len(sources),source_bytes=sum(p.stat().st_size for p in sources),cases=48,words=16384,
        controls=['MUT_GAIN','MUT_USER','MUT_RAW_X'],
        boundary='actual native SU/VM and production stream tile; command/table/VM fixture adapters, external initialized RSTD; no ROOT, calendar, multi-slice transport or whole token')
    (out/'preparation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    files=sorted(p for p in out.rglob('*')if p.is_file())
    (out/'packet.sha256').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(out))+'\n'for p in files))
    return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('base','stage','stream','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();r=prepare(a.base,a.stage,a.stream,a.out)
    print(json.dumps({k:r[k]for k in ('status','source_files','source_bytes','cases','words')}))
