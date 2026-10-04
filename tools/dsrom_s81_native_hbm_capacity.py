#!/usr/bin/env python3
"""Address-only retained source census; never constructs/copies history payload."""
import argparse, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def census(path, paired):
    h=hashlib.sha256(); count=0; maximum=-1; cursor=None
    with path.open('rb') as f:
        for raw in f:
            h.update(raw);fields=raw.split()
            if not fields:continue
            if paired:
                if len(fields)!=2:raise ValueError(f'{path}: expected address/data')
                a=int(fields[0],16)
            else:
                if fields[0].startswith(b'@'):
                    cursor=int(fields[0][1:],16);continue
                if cursor is None:raise ValueError('sparse payload before address')
                a=cursor;cursor+=1
            maximum=max(maximum,a);count+=1
    if count==0:raise ValueError(f'empty source {path}')
    return dict(path=str(path),sha256=h.hexdigest(),sectors=count,max_sector=maximum)

def model(base):
    inputs=[]
    for rank in range(4):
        for stack in range(4):
            for path,paired in [
                (base/f'ctx1048576_s20260930_r{rank}'/f'hbm_s{stack}.hex',False),
                (base/f'ctx1048576_s20260930_L20_r{rank}'/f'hbm_s{stack}.hex',False),
                (base/'ctx1048576_s20260930_L20'/f'r{rank}'/f'ckv_s{stack}.hex',True)]:
                rec=census(path,paired);rec.update(rank=rank,stack=stack);inputs.append(rec)
    # Native selected source placement: gid[5:4] die, gid[7:6] stack,
    # ((gid>>8)<<4)|(gid&15) local, nine sectors per row.
    gid=1048575;local=((gid>>8)<<4)|(gid&15);current_last=4194304+9*local+8
    maximum=max(current_last,max(i['max_sector'] for i in inputs));words=maximum+1
    backing=4*words*32
    return dict(schema='dsrom_s81_native_hbm_capacity.v1',inputs=inputs,
        current_native_write=dict(gid=gid,rank=(gid>>4)&3,stack=(gid>>6)&3,
            local=local,base=4194304,first_sector=4194304+9*local,last_sector=current_last,
            bound='selected 1M context; native nw_gid=nw_addr>>9, complete nine-sector write'),
        max_history_sector=max(i['max_sector'] for i in inputs),mem_words=words,
        backing_bytes_per_four_stack_rank=backing,backing_GiB_per_rank=backing/2**30,
        backing_GiB_TP4=4*backing/2**30,
        launch_peak_GiB=4,
        peak_basis=dict(single_rank_runtime_backing_GiB=backing/2**30,
            two_compiler_process_allowance_GiB=2,link_framework_allowance_GiB=.5,
            streamed_init_metadata_allowance_GiB=.25,rounding_reserve_GiB=.68),
        scope='same existing 4-stack WINDOW/CKV backend, indexer B inactive; no IK16M inference',
        source_pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [
            'rtl/dsrom_sys/c8/ot_chip_v41x_ckv_die_service_c8.sv',
            'rtl/chip/ot_chip_v41x_ckv_selected_dma.sv']},
        generated_payload_bytes=0,zero_fill_substitute=False,physical_or_bandwidth_credit=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,default=Path('/home/ubuntu/w17work/die'));p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    x=model(a.base);a.out.write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({k:x[k] for k in ['mem_words','max_history_sector','current_native_write','backing_GiB_per_rank','backing_GiB_TP4','launch_peak_GiB']},indent=2))
