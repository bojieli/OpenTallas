from pathlib import Path
import re,json,collections,math
pairs=[('qkd_d2d_static_r7w','qkd_d2d_static_r7w_s1'),('qkd_d2d_static_ovl_m1','qkd_d2d_static_ovl_s1')]
for old,new in pairs:
    olddir=Path('physical/ref_tile')/old
    newdir=olddir.with_name(new)
    newdir.mkdir(parents=True,exist_ok=True)
    (newdir/'local_reset_capture.tcl').write_text((olddir/'local_reset_capture.tcl').read_text())
    s=json.loads((olddir/'spec.json').read_text())
    s['name']=new
    s['params']['SAFE_RC']=1
    s['route']['macro_halo_x_um']=20
    s['route']['macro_halo_um']=5.4
    s['io_tcl']=str(newdir/'assigned_pins.tcl')
    s['pin_hook_before_flops']=[str(newdir/'local_reset_capture.tcl')]
    s['job']['branch']='codex/d2d-safe-1019'
    s['job']['tag']='s1'
    s['job']['views_to']=str(newdir/'views')
    s['job']['record_to']='results/rtl/ref_tile/'+new
    s['macros']=[dict(s['macros'][0],at=[x,y]) for y in [43.2,172.8] for x in [43.2,259.2]]
    for b in s['job']['benches']:
        b['cmd']='KRC=1 '+b['cmd']
        if 'fail_witness' in b:
            b['fail_witness']=b['fail_witness'].replace(old+'_codec2',new)
    s['structural_change']='Safe structural successor: four SRAM macros on43.2 lattice with44.712um horizontal/51.816um vertical channels and full-width stdcell band; exact pins uniformly spread across full faces <=6pins/um actual usedspan. Same475.2x280.8 outline, portfaces, productioncodec2.16 and functional edges. SAFE_RC1 uses7 KEPT equal-depth reset regions; distinct TX/control/slot/RX resets reuse compute NRC mechanism without added release/data edges. Parent frame777.576x518.376 confirmed KV lead; new LEF coordinates must regenerate parent binding.'
    s['reroute_reason']={'kind':'rtl_change','params':{'TXDP':'0x03030416','SAFE_RC':1},'source':'root safe-design instruction and KV lead confirmed codec2/frame','cell':s['top'],'fix':s['structural_change'],'why':'New unclosedMU/OVL signoff requires actual43.2 origins and full-face spread; explicitparallel safekit authorized root. Prior source gates preserved as diagnostic evidence.'}
    (newdir/'spec.json').write_text(json.dumps(s,indent=1)+'\n')
    groups=collections.defaultdict(list)
    rx=r'place_pin -pin_name \{([^}]+)\} -layer (M\d) -location \{([\d.]+) ([\d.]+)\} -pin_size \{([\d.]+) ([\d.]+)\}'
    for name,layer,x,y,w,h in re.findall(rx,(olddir/'assigned_pins.tcl').read_text()):
        x,y=float(x),float(y)
        face='E' if x>475 else 'W' if x<.1 else 'N' if y>280 else 'S'
        groups[face].append((y if face in 'EW' else x,name,layer,w,h))
    lines=['# Safe full-face exact pins; source geometry preserved only for portface and relative bit ordering.']
    metrics={}
    for face,v in groups.items():
        v.sort()
        clk=[t for t in v if t[1]=='ck']
        v=[t for t in v if t[1]!='ck']
        if clk:
            v.insert(len(v)//2,clk[0])
        length=280.8 if face in 'EW' else 475.2
        pitch=.144 if face in 'EW' else .096
        offset=.012 if face in 'EW' else .06
        t0=math.ceil((2.16-offset)/pitch)
        t1=math.floor((length-2.16-offset)/pitch)
        coords=[]
        for i,(_,name,layer,w,h) in enumerate(v):
            pos=(t0+round((t1-t0)*i/(len(v)-1)))*pitch+offset
            coords.append(pos)
            if face in 'EW':
                x,y=(.042 if face=='W' else 475.158),pos
            else:
                x,y=pos,(.042 if face=='S' else 280.758)
            lines.append(f'place_pin -pin_name {{{name}}} -layer {layer} -location {{{x:.6f} {y:.6f}}} -pin_size {{{w} {h}}}')
        density=len(v)/(max(coords)-min(coords))
        metrics[face]={'pins':len(v),'span':max(coords)-min(coords),'pins_per_um':density}
        assert density<=6
    (newdir/'assigned_pins.tcl').write_text('\n'.join(lines)+'\n')
    (newdir/'pin_geometry_plan.json').write_text(json.dumps(metrics,indent=1)+'\n')
    print(new,metrics)
