import json,sys
for n in sys.argv[1:]:
    d=json.load(open(f'/srv/opentallas-scratch2/claude/proto1025/geom/{n}.json'))['types']
    fails={k:v for k,v in d.items() if v['verdict']=='FAIL'}
    print(f'### {n}: PASS {len(d)-len(fails)} FAIL {len(fails)}')
    for k,v in sorted(fails.items()):
        if 'error' in v: print(f'{k}|ERROR {v["error"][:120]}'); continue
        f=v['footprints']; worst=max(v['failures'],key=lambda x:x['max_hop_um'],default=None)
        parts=[]
        if v['over_reach_bits']: parts.append(f"reach max {v['max_hop_um']:.0f}um ({v['over_reach_bits']} bits >405; worst {worst['slot'] if worst else ''})")
        if v['st_in_core']: parts.append(f"{v['st_in_core']} station sites in cores")
        if f['core_intersections']: parts.append(f"{f['core_intersections']} cell envelopes x cores")
        if f['overlaps']: parts.append(f"{f['overlaps']} cell overlaps")
        if f['outside_outline']: parts.append(f"{f['outside_outline']} outside outline")
        print(f'{k}|'+'; '.join(parts))
