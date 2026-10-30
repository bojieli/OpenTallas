from pathlib import Path
r=Path('/srv/opentallas-scratch2/claude/codex-head-start-1851')
p=r/'start_reach.py';t=Path('/srv/opentallas-scratch2/claude/head-start-2/start_reach.py').read_text()
old="        if t is None:missing['tree_driver_not_found']+=1;continue"
new="""        if t is None and s.get('clock_source_root'):
            import re
            m=re.search(r'place_pin -pin_name '+s['clock_net']+r' -layer \\S+ -location \\{([-\\d.]+) ([-\\d.]+)\\}',ct)
            if m is None:missing['root_pin_not_found']+=1;continue
            rootxy=tuple(map(float,m.groups()))
            hops['root_pin->local_clk'].append((round(man(rootxy,ctr[drv[cp]['inst']]),3),s['clock_net'],drv[cp]['inst']))
            continue
        if t is None:missing['tree_driver_not_found']+=1;continue"""
assert old in t;p.write_text(t.replace(old,new))
p=r/'render_reach.py';t=Path('/srv/opentallas-scratch2/claude/head-start-2/render_reach.py').read_text()
old="    t=ydrv.get(c) or ydrv.get(s['clock_net']);lclk.append((ctr(trect[t]),ctr(lrect[ph['stage_clock_drivers'][c]['inst']])))"
new="""    t=ydrv.get(c) or ydrv.get(s['clock_net'])
    if t is None and s.get('clock_source_root'):
        import re
        m=re.search(r'place_pin -pin_name '+s['clock_net']+r' -layer \\S+ -location \\{([-\\d.]+) ([-\\d.]+)\\}',open(ctd+'/ctree.tcl').read())
        assert m, 'missing actual root pin'
        source=tuple(map(float,m.groups()))
    else:source=ctr(trect[t])
    lclk.append((source,ctr(lrect[ph['stage_clock_drivers'][c]['inst']])))"""
assert old in t;p.write_text(t.replace(old,new))
