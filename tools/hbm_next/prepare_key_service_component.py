#!/usr/bin/env python3
"""Stage the smallest actual native memory service + static key transport vehicle.

Explicit synthetic row100/101 allocations are declared component input data.
They are never a production allocation or a whole-die token qualification.
"""
import argparse,hashlib,json,shutil,sys
from pathlib import Path
from key_cohort_programme import compile_allocation


def prepare(tree,out):
    tree,out=Path(tree).resolve(),Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(tree/'tools'));from hbm_svc_packed136_image import sector_address
    sys.path.insert(0,str(tree/'tools/die_plan'));import bind_elab as E;import bind as B
    extra=[str(tree/'rtl/hbm_next/idxn/ot_hnx_idxn_key_serial_chain.sv'),str(tree/'rtl/test/hbm_accel/svg_rel/tb_svg_rel_dram_sparse.sv'),str(tree/'rtl/lib/ot_reset_sync.sv')]
    idx=E.module_index(['rtl','physical/die_plan/hbm/bind/rtl/b2_native'],extra,str(tree))
    need=['ot_hbm_svc_sm_group_rel_id_rc','ot_hbm_svc_vm_kshare_splitstrap','ot_hbm_svc_pc_ctrl_leaf_cfg_h9b','ot_hnx_idxn_key_serial_seed','ot_hnx_idxn_key_serial_merge','ot_hnx_idxn_keybuf_slice','tb_svg_rel_dram_sparse']
    picks={};cl,missing,macros=B.kit_closure(need,idx,extra,picks,views=B.macro_views(str(tree)))
    if missing:raise ValueError('actual service source closure incomplete: '+str(missing))
    sim={m['bb']:m['model'] for m in macros.values() if m.get('bb') and m.get('model')}
    cl=[sim.get(f,f) for f in cl];(out/'src').mkdir(exist_ok=True);rec=[]
    for i,f in enumerate(cl):
        p=Path(f);q=out/'src'/f'{i}_{p.name}';shutil.copy2(p,q)
        rec.append(dict(source=str(p),file=str(q.relative_to(out)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    (out/'sources.f').write_text('\n'.join(str(out/r['file']) for r in rec)+'\n')
    (out/'sources.json').write_text(json.dumps(dict(needed=need,files=rec,picks=picks,missing=missing),indent=2)+'\n')
    a=dict(schema='opentallas.hbm_idx.key_cohort_allocation.v1',physical_stack=2,slots=4,
      packet_from_go_edges=7,relay_cycles=4,pipe_phase=3,go_done_tail_edges=10,query_start_at=2500,
      programme_base=32,descriptor_base=16,occupied_programme_ranges=[[0,32]],occupied_descriptor_ranges=[[0,16]],cohorts=[])
    for c in range(2):
        groups=[]
        for lane in range(8):
            blocks=[]
            for b in range(3):
                go=520+c*840+b*280+lane%4
                blocks.append(dict(row_base=100+c,slot=b,epoch=100+c*10+b,go_at=go,cache_ready_by=go-20))
            groups.append(dict(lane=lane,blocks=blocks))
        a['cohorts'].append(dict(id=c,groups=groups))
    compiled=compile_allocation(a)
    (out/'allocation.json').write_text(json.dumps(a,indent=2)+'\n')
    (out/'programme.hex').write_text('\n'.join(compiled['programme_words'])+'\n')
    (out/'descriptors.hex').write_text('\n'.join(x['descriptor_word'] for x in compiled['source_groups']['svg_NW0'])+'\n')
    words=[];mem={}
    for c in range(2):
        records=[]
        for row in range(171):
            x=0
            for j in range(34):x|=(((0x9e3779b9*(row+1))^(0x7135b92d*(j+1))^(0xa5f13d97*(c+1)))&0xffffffff)<<(32*j)
            records.append(x);words.append(f'{x:0272x}')
        for b,rows in enumerate([64,64,43]):
            raw=b''.join(x.to_bytes(136,'little') for x in records[b*64:b*64+rows]);total=((len(raw)+127)//128)*4;raw+=bytes(32*total-len(raw))
            alloc=dict(pcs=[0,1,2,3],row_base=100+c,stack_bytes=1<<35)
            for o in range(total):
                addr=sector_address(o+512*b,alloc)
                if addr in mem:raise ValueError('synthetic memory allocation alias')
                mem[addr]=int.from_bytes(raw[32*o:32*o+32],'little')
    (out/'records.hex').write_text('\n'.join(words)+'\n')
    (out/'memory.hex').write_text(''.join(f'{k:08x} {v:064x}\n' for k,v in sorted(mem.items())))
    shutil.copy2(tree/'rtl/test/hbm_key_service_chain_1029/tb_key_service.sv',out/'tb_key_service.sv')
    (out/'fixture.json').write_text(json.dumps(dict(scope='explicit synthetic onegroup component, not productionallocation',HBM_sectors=len(mem),physical_stack=2,physical_PC=[0,1,2,3],rows=[100,101],subrow_slots=[0,1,2],refresh_reload=[118,121,126,129],packet_preedge_sample_from_go=7,go_at=[520,800,1080,1360,1640,1920]),indent=2)+'\n')
    return rec


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('tree',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args();print('KEY_SERVICE_STAGED',len(prepare(a.tree,a.out)),'source files')
