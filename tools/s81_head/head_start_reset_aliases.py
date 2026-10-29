#!/usr/bin/env python3
"""Expose actual existing raw relay Qs as uniform type ports for START reset.

Apply after landing compose and to the corresponding generated type RTL. No
source net is fabricated: the RTL patch requires an existing registered driver.
"""
import copy,re


def declare(plan,exports):
    out=copy.deepcopy(plan)
    for tn,rows in exports['types'].items():
        t=out['partition_types'][tn]
        pins=t.setdefault('clock',{}).setdefault('landing_contract',{}).setdefault('pins',[])
        existing={p['name'] for p in pins}
        for r in rows:
            if r['port'] in existing:raise ValueError(f"{tn}: duplicate reset export {r['port']}")
            pins.append(dict(name=r['port'],dir='out',kind='ctl',layer='M7',xy_um=r['xy_um'],epoch=False,
                source_instance=r['instance'],source_net=r['net'],source_registered=True))
        t['reset_start_raw_exports']=copy.deepcopy(rows)
    return out


def patch_rtl(text,rows):
    if not rows:return text
    m=re.search(r'\bmodule\s+\w+\s*\((.*?)\);',text,re.S)
    if not m:raise ValueError('type module header not found')
    if any(re.search(r'\b'+re.escape(r['port'])+r'\b',text) for r in rows):raise ValueError('reset export already exists')
    for r in rows:
        # Accept only the recorded actual relay instance driving the recorded
        # Q net. An arbitrary same-spelled combinational alias is insufficient.
        if not re.search(r'\b'+re.escape(r['instance'])+r'\s*\([^;]*\.q\(\s*'+re.escape(r['net'])+r'\s*\)',text,re.S):
            raise ValueError(f"raw reset source is not the recorded registered relay: {r['instance']}.{r['net']}")
    ansi=bool(re.search(r'\b(input|output)\b',m[1]))
    header=m[1].rstrip()+',\n'+',\n'.join('    '+('output wire ' if ansi else '')+r['port'] for r in rows)+'\n'
    text=text[:m.start(1)]+header+text[m.end(1):]
    end=text.rfind('endmodule')
    body=('' if ansi else ''.join('    output wire '+r['port']+';\n' for r in rows))+''.join('    assign '+r['port']+' = '+r['net']+';\n' for r in rows)
    return text[:end]+body+text[end:]
