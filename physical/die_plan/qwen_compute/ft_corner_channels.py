#!/usr/bin/env python3
"""Keep CBN rsf turns in actual N/S macro-free bands; preserve every stage/pin.

The existing first transition enters the upper A0 corner before reaching the
left/central channel. Move the same FF bank above the macro; turn back to the
output below the bottom macro. Per-bit X coordinates stay fixed except a formerly mid-gap FF bank shifted
6.48um into the actual central channel; identity, stage counts,
parent endpoints and pin windows remain unchanged. Existing reset/run R4 crossings
are a separate explicit blocker; this helper does not mask them.
"""


def apply(raw):
    if raw.get('die',{}).get('name')!='qwen_compute':raise ValueError('QC only')
    reports=[]
    for tn,k in (('cbn_q00',10),('cbn_q01',9)):
        t=raw['partition_types'][tn]
        slot=next(s for s in t['ft_slots'] if s['name']=='rsf')
        if slot['stations']!=k or len(slot['bit_sites_um'])!=k-1:raise ValueError('changed stage contract')
        targets=[round(2566.08-j*362.88,4) for j in range(8)]
        if tn=='cbn_q00':targets=[2566.08]+targets
        old_regs=[list(xy) for xy in slot['regs_um']]
        old_width=slot['width'];old_sites=slot['bit_sites_um']
        for j,(bank,target) in enumerate(zip(old_sites,targets),1):
            delta=target-old_regs[j][1]
            for xy in bank:xy[1]=round(xy[1]+delta,4)
            if tn=='cbn_q00' and j>=2:
                # Stage6 was in the horizontal mid-gap and spread left of the
                # central channel. Its new y is beside a macro: keep whole cells
                # inside the actual channel rather than sliding them over a core.
                import math
                half=t['outline_um'][0]/2
                left=max(c['origin_um'][0]+c['outline_um'][0] for c in t['hard_cores']
                         if c['origin_um'][0]+c['outline_um'][0]/2<half)+2
                right=min(c['origin_um'][0] for c in t['hard_cores']
                          if c['origin_um'][0]+c['outline_um'][0]/2>half)-2
                dx=max(0,math.ceil((left-min(x for x,y in bank))/2.16-1e-8)*2.16)
                if max(x for x,y in bank)+dx+slot['bit_site_cell_um'][0]>right:
                    raise ValueError('whole FF bank cannot fit central channel')
                for xy in bank:xy[0]=round(xy[0]+dx,4)
                slot['regs_um'][j][0]=round(slot['regs_um'][j][0]+dx,4)
            slot['regs_um'][j][1]=target
        if slot['width']!=old_width:raise ValueError('bus width changed')
        maximum=0
        for a,b in zip(slot['bit_sites_um'],slot['bit_sites_um'][1:]):
            maximum=max(maximum,max(abs(p[0]-q[0])+abs(p[1]-q[1]) for p,q in zip(a,b)))
        if maximum>405:raise ValueError('actual internal bit-pair reach exceeded')
        top=max(c['origin_um'][1]+c['outline_um'][1] for c in t['hard_cores'])
        bottom=min(c['origin_um'][1] for c in t['hard_cores'])
        n=2 if tn=='cbn_q00' else 1
        if any(y<top+2 for bank in slot['bit_sites_um'][:n] for x,y in bank):raise ValueError('N turn enters macro')
        if any(y+.27>bottom-2 for x,y in slot['bit_sites_um'][-1]):raise ValueError('S turn enters macro')
        reports.append(dict(type=tn,slot='rsf',stations=k,first_corner_um=targets[0],last_corner_um=targets[-1],
                            max_internal_actual_bit_pair_um=round(maximum,4),data_cycles_added=0,
                            R4_reset_run_crossings='OPEN separate source-traced structural repair'))
    return dict(schema='opentallas.qc-ft-corner-channels.v1',changed=reports,FF_added=0,data_cycles_added=0,
                token_cycles_added=0,pins_or_widths_changed=False,core_geometry_changed=False)
