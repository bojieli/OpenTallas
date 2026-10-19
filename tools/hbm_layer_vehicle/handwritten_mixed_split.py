#!/usr/bin/env python3
"""Concrete unchanged-literal single/split programme ABI and independent cost."""
import json,math,hashlib,argparse
from pathlib import Path
import smb_unit as S
from attention_mode_contract import analyse


def make():
    commands=[(0xa2<<184)|(m<<181) for m in (0,4,0)]
    single=S.Store(0)
    single_range=single.add([S.svg_word(c&((1<<83)-1),retire=i==2) for i,c in enumerate(commands)], [c>>83 for c in commands])
    split=S.Store(0)
    split_ranges=[split.add([S.svg_word(c&((1<<83)-1),retire=True)],[c>>83]) for c in commands]
    profiles=[]
    for banked in (False,True):
        calendar_extra=2 if banked else 0
        command_extra=calendar_extra+2
        for block_lines in (1,64):
            block_bytes=((136*block_lines+127)//128)*128
            busy=6+calendar_extra+2
            fetch=(200*block_lines+63)//64+4+22
            spacing=max(1+busy,fetch)
            gos=[542+i*spacing for i in range(3)]
            single_desc=S.desc_row(0,row_base=0,landing=0,epoch=1,rows=block_lines,tag_base=0,prog_base=single_range[0],prog_limit=single_range[1],go_at=542,mode=0)
            desc=[S.desc_row(i,row_base=8*i,landing=i,epoch=1+i,rows=block_lines,tag_base=0,prog_base=pb,prog_limit=pl,go_at=gos[i],mode=(commands[i]>>181)&7) for i,(pb,pl) in enumerate(split_ranges)]
            model=analyse(commands,block_lines=block_lines,calendar_extra=calendar_extra,command_only_extra=2)
            assert model['extra_hbm_bytes_conservative']==2*block_bytes
            assert model['added_idle_stream_edges_lower_bound']==2*busy
            profiles.append(dict(banked_calendar=banked,block_lines=block_lines,
                native_padding=22,read_admission=7,read_pin_latency=6+calendar_extra,command_latency=7+command_extra,
                programme_done_extra=calendar_extra,residual_tail=2,
                single_descriptor=f'{single_desc:064x}',split_descriptors=[f'{x:064x}' for x in desc],
                single_go=[542],split_go=gos,
                go_spacing_lower_bound=1+busy,go_spacing_selected=spacing,
                selected_spacing_basis='max(one-word body+BUSY6+calendar extra+cache residual, ceil(200*block_lines/64)+PACE_ADD4+padding22)',
                extra_go_count=2,extra_descriptors=2,
                extra_idle_lower_bound=2*busy,extra_idle_selected=2*(spacing-1),
                hbm_bytes_before=block_bytes,hbm_bytes_after=3*block_bytes,extra_hbm_bytes=2*block_bytes,
                single_install_ingress_edges=2*single.top+2,split_install_ingress_edges=2*split.top+6,
                status='source-bound conservative schedule recipe; not a whole-service timing receipt'))
    return dict(source_words=[f'{x:048x}' for x in commands],
        literal_sha256=hashlib.sha256(b''.join(c.to_bytes(24,'little') for c in commands)).hexdigest(),
        meaning='dense mode0 -> attention mode4 -> dense mode0; no configure, packet, consume or outstanding converter state',
        actual_frontend_proof='tb_actual_front_modes: contiguous frontend accepts, constant descriptor guard rejects; split with idle8/10 accepts with matching class',
        single=dict(programme_words=single.top,svg={a:f'{w:034x}' for a,w in single.svg.items()},xc={a:f'{w:044x}' for a,w in single.xc.items()},ranges=[single_range]),
        split=dict(programme_words=split.top,executed_words=3,svg={a:f'{w:034x}' for a,w in split.svg.items()},xc={a:f'{w:044x}' for a,w in split.xc.items()},ranges=split_ranges),
        profile=profiles,
        qualification='component decoder and explicit ABI/cost recipe only; parent owns actual issuer/banked/cache/HBM composition and throughput proof')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
    Path(a.out).write_text(json.dumps(make(),indent=2)+'\n');print('HANDWRITTEN_MIXED_SPLIT_PASS')
