#!/usr/bin/env python3
"""Source component proof from legitimate entry rows, with no norm oracle input."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--shipping-manifest',type=Path,required=True)
    p.add_argument('--entry-image',type=Path,required=True)
    p.add_argument('--native-programme',type=Path,required=True)
    p.add_argument('--fixtures',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--stage-only',action='store_true')
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    image=json.loads(a.entry_image.read_text());shipping=json.loads(a.shipping_manifest.read_text())
    native=json.loads(a.native_programme.read_text())
    assert native['die_sha256']=='8ef3b748e5b14da4446d29576702d2828a056943481c650a65b5f5b18bf84838'
    assert native['input_sources']==image['input_sources'] and native['normr_count']==80
    assert native['eps_fp32_bits']=='1e3ce508'
    assert sha(a.fixtures/'meta.json')==image['fixture_meta_sha256']
    for rel,rec in image['input_sources'].items():assert sha(a.fixtures/rel)==rec['sha256'],rel
    # Independently reconstruct every H/pre/gain native SRAM half row from
    # legitimate inputs. Neither ops/norm nor any expected rstd/y/q is loaded.
    import numpy as np
    files=json.loads((a.fixtures/'files.json').read_text())
    def arr(rel):
        rec=files[rel]
        return np.fromfile(a.fixtures/rel,dtype=np.dtype(rec['dtype'])).reshape(rec['shape'])
    h=arr('io/h_in.bin').view(np.uint32)
    gain=arr('weights/attn_norm.bin').copy().view('<u2').reshape(5120).astype(np.uint32)<<16
    pre=arr('io/pre_in.bin').view(np.uint32)
    assert h.shape==(4,5120) and not np.any(h&65535)
    pack=lambda values,bits:sum(int(v)<<(bits*i) for i,v in enumerate(values))
    contexts=[]
    for sid in range(16):
        for leaf in range(5):
            start=320*sid+64*leaf
            hh=[pack([h[c,start+8*j+4*hf+l]>>16 for c in range(4) for l in range(4)],16)
                for j in range(8) for hf in range(2)]
            gg=[pack(gain[start+8*j:start+8*j+8],32) for j in range(8)]
            expected={r:(hh[r//2]>>(128*(r%2)))&((1<<128)-1) for r in range(32)}
            expected.update({64+r:(gg[r//2]>>(128*(r%2)))&((1<<128)-1) for r in range(16)})
            expected[1008]=pack(pre,32)
            rows=[w for w in image['writes'] if w['sid']==sid and w['leaf']==leaf]
            assert len(rows)==49 and [w['row'] for w in rows]==list(expected)
            assert all(int(w['data128'],16)==expected[w['row']] for w in rows)
            directory=a.out/f'sid{sid}_leaf{leaf}';directory.mkdir()
            (directory/'native_sw128.hex').write_text(''.join(f'{expected[w["row"]]:032x}\n' for w in rows))
            command=[c for c in native['commands'] if c['kind']=='NORMR' and c['sid']==sid and c['leaf']==leaf]
            assert len(command)==1
            payload=int(native['templates'][command[0]['template']]['payload186'],16)
            body=payload>>26
            assert body==7|(1008<<4)|((5*sid+leaf)<<14)|(1<<24)
            assert payload&65535==1<<sid and (payload>>21)&31==1<<leaf
            (directory/'native_normr160.hex').write_text(f'{body:040x}\n')
            contexts.append(dict(sid=sid,leaf=leaf,global_beat=5*sid+leaf,global_start=start,
                input_sha256=sha(directory/'native_sw128.hex'),directory=str(directory.resolve())))
    listed=(a.source_root/'rtl/dsrom_sys/s81_dv/slice/test/leaf_bench.f').read_text().split()
    extras=['rtl/hdc/v41x/ot_hbm_norm_split.sv','rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv']
    for name in ['128x256_m1_r2c2','512x128_m4_r2c2']:
        extras.append(f'physical/asap7_memory_macros_v2/ot_sram_1r1w_{name}/ot_sram_1r1w_{name}.v')
    sources=sorted(set(listed+extras))
    pins={rel:sha(a.source_root/rel) for rel in sources}
    for rel,digest in pins.items():assert shipping.get(rel)==digest,('source absent/changed from shipping manifest',rel)
    bench=Path(__file__).with_name('tb_norm_leaf_source.sv')
    receipt=dict(schema='opentallas.s81.norm_leaf_source.v1',status='STAGED',contexts=contexts,
        source_sha256=pins,bench_sha256=sha(bench),entry_image_sha256=sha(a.entry_image),
        native_programme_sha256=sha(a.native_programme),eps_fp32_bits=native['eps_fp32_bits'],
        entry_image_die_identity_qualification='ROW DATA ONLY; original G7 image identity not asserted as G8 programme',
        input_sources=image['input_sources'],VN_parameters=dict(G=8,D=64,N=8,LM=5,LA=6),VQ_AQ_XMEM=2,
        scope='80 sequential reset contexts of actual VP native ingress -> VN -> VQ; common component clock',
        physical_clocks_qualified=False,MU72_transport_qualified=False,global_epochs_qualified=False,
        expected_norm_input=False,actual_rstd_input=False,actual_partials=[])
    def save():(a.out/'receipt.json').write_text(json.dumps(receipt,indent=1)+'\n')
    save()
    if a.stage_only:return
    v=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
    obj=a.out/'obj'
    cmd=[str(v),'--binary','--timing','-O1','-fno-dfg','--unroll-count','4','-Wno-fatal','-Wno-WIDTH',
        '--top-module','tb_norm_leaf_source','-Mdir',str(obj.resolve()),'-j','2',
        *[str((a.source_root/s).resolve()) for s in sources],str(bench.resolve()),'-CFLAGS','-O1']
    receipt.update(status='BUILDING',argv=cmd);save()
    with (a.out/'build.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
    if r.returncode:receipt.update(status='BUILD_FAIL',exit_code=r.returncode);save();sys.exit(1)
    guard_dir=Path.home()/'.local/opentallas-tools/verilator-5.050/share/ot_nba_guard'
    sys.path.insert(0,str(guard_dir));import verilator_nba_guard as G
    guard=G.scan(str(obj));(a.out/'nba_guard.json').write_text(json.dumps(guard,indent=1)+'\n')
    if guard['findings']:receipt['status']='NBA_GUARD_FAIL';save();sys.exit(86)
    for context in contexts:
        args=[str((obj/'Vtb_norm_leaf_source').resolve()),f'+DIR={context["directory"]}',
              f'+SID={context["sid"]}',f'+LEAF={context["leaf"]}']
        r=subprocess.run(args,capture_output=True,text=True)
        log=r.stdout+r.stderr;(Path(context['directory'])/'partial.log').write_text(log)
        matches=re.findall(r'LEAF_PARTIAL sid=(\d+) leaf=(\d+) cycle=(\d+) data=([0-9a-fA-F]+)',log)
        if r.returncode or len(matches)!=1 or 'LEAF_SOURCE_PASS' not in log:
            receipt.update(status='PARTIAL_FAIL',failed_context=context,exit_code=r.returncode);save();sys.exit(1)
        sid,leaf,cycle,data=matches[0];assert (int(sid),int(leaf))==(context['sid'],context['leaf'])
        receipt['actual_partials'].append(dict(sid=int(sid),leaf=int(leaf),cycle=int(cycle),data32=data,
            log_sha256=sha(Path(context['directory'])/'partial.log')))
        save()
    receipt['status']='ACTUAL_LEAF_PARTIALS_COLLECTED_COMPONENT_ONLY';save()
    print(json.dumps(dict(status=receipt['status'],count=len(receipt['actual_partials']))))


if __name__=='__main__':main()
