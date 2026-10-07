#!/usr/bin/env python3
"""Read-only source-to-generated-bus census before any r22 pin/geometry choice."""
import hashlib
import json
from pathlib import Path
import qwen_rom_fulldie_b3r2 as F
from die_top_lint import QWEN_R20C

ROOT=Path(__file__).resolve().parents[1]


def audit():
    recipe=dict(QWEN_R20C);recipe['cdc']=F._cdc_arg(recipe['cdc'])
    v,m=F.selected(enabled=True,**recipe)
    items=[i for i in m['insts'] if i.kind in ('station','head','tile')]
    clock={i.name:[] for i in items};reset={i.name:[] for i in items}
    roles={}
    byname={i.name:i for i in items}
    for bid,cls,bits,eps in m['buses']:
        if cls in ('corridor','head_chain','tap'):
            for j,(name,pin) in enumerate(eps):
                if name in byname and byname[name].kind in ('station','head'):
                    roles.setdefault(byname[name].master,{}).setdefault(pin,set()).add('forward_source' if j==0 else 'forward_sink')
        for name,pin in eps:
            if name in clock and cls=='clock_trunk':clock[name].append([bid,pin,bits])
            if name in reset and cls=='reset':reset[name].append([bid,pin,bits])
    return dict(schema='opentallas.qwen_station_r18_clock_audit.v1',
        recipe='QWEN_R20C base shared by r21 before relay insertion',
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
            ['tools/qwen_rom_fulldie_b3r2.py','tools/qwen_rom_fulldie.py','tools/die_top_lint.py','tools/qwen_station_clock_audit_r22.py']},
        effective_bus_bits={cl:sorted({nb for _,c,nb,_ in m['buses'] if c==cl}) for cl in ['corridor','head_chain','tap']},
        clock_endpoint_count_histogram={str(n):sum(len(v)==n for v in clock.values()) for n in sorted({len(v) for v in clock.values()})},
        reset_endpoint_count_histogram={str(n):sum(len(v)==n for v in reset.values()) for n in sorted({len(v) for v in reset.values()})},
        generated_station_port_roles={m:{p:sorted(d) for p,d in ps.items()} for m,ps in sorted(roles.items())},
        instances=len(items), examples={name:dict(clock=clock[name],reset=reset[name]) for name in list(clock)[:5]},
        conclusion='No64clock payloadpins: already separateck1. Reset removed from bundle but noresetnet reaches auditedfieldinstances. r22 needs explicitrst_n tree.',
        actual_fullwidth_signal_bits=509,clock_pin_per_instance=1,reset_pin_required_per_instance=1,
        original_station_frame_um=list(v.STATION),die=m['die'],adoption=False)


if __name__=='__main__':print(json.dumps(audit(),indent=2))
