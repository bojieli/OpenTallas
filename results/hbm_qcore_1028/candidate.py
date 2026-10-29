"""Same-outline qcore SRAM relocation feasibility and visual plan."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

out=Path(__file__).parent
w,h=224.64,207.36
mw,mh=94.8,41.076
halo=4.32
macros=[('u_fcore.u_red.ma',64.8,133.92),('u_fcore.u_red.mb',64.8,34.56)]
islands=[(146.88,108.,155.52,116.64),(51.84,82.08,60.48,90.72),(164.16,99.36,172.8,108.)]
for _,x,y in macros:
    for a,b,c,d in islands:
        assert x-halo>=c or x+mw+halo<=a or y-halo>=d or y+mh+halo<=b
west=64.8-halo-4.32
east=w-4.32-(64.8+mw+halo)
middle=133.92-(34.56+mh)-2*halo
# Two macros, each ~410 pins per W/E edge, in separate y bands.
# Conservative upper bound allocates both edges' pins to each side corridor.
estimate={'status':'FEASIBLE_TRIAL_ONLY','outline_um':[w,h],
 'macro_um':[mw,mh],'macro_placements':macros,'macro_halo_um':halo,
 'clear_corridors_um':{'west':west,'east':east,'middle':middle},
 'tracks_per_um':36.46,
 'side_escape_upper_bound':820/(min(west,east)*36.46),
 'middle_945_net_bound':945/(middle*36.46),
 'unchanged':['RTL','clock/reset island cells and ports','outline','external pin table','latency'],
 'limits':'Analytic track budget only; GRT50 after placement decides actual congestion.'}
assert estimate['side_escape_upper_bound']<.6
assert estimate['middle_945_net_bound']<.6
(out/'estimate.json').write_text(json.dumps(estimate,indent=2)+'\n')
fig,ax=plt.subplots(figsize=(8,8))
ax.add_patch(Rectangle((0,0),w,h,fill=False,lw=2))
for n,x,y in macros:
    ax.add_patch(Rectangle((x-halo,y-halo),mw+2*halo,mh+2*halo,color='orange',alpha=.2))
    ax.add_patch(Rectangle((x,y),mw,mh,facecolor='lightgrey',edgecolor='black',hatch='//'))
    ax.text(x+mw/2,y+mh/2,n.rsplit('.',1)[1],ha='center')
for a,b,c,d in islands:
    ax.add_patch(Rectangle((a,b),c-a,d-b,color='royalblue',alpha=.7))
ax.plot(151.176,112.32,'*',color='red',ms=12,label='unchanged clock entry')
ax.text(15,100,f'W clear {west:.2f} um',rotation=90)
ax.text(193,100,f'E clear {east:.2f} um',rotation=90)
ax.text(85,102,f'centre {middle:.2f} um')
ax.set(xlim=(-5,w+5),ylim=(-5,h+5),aspect='equal',xlabel='um',ylabel='um',title='qcore same-outline candidate: split SRAMs N/S')
ax.legend(loc='upper left')
fig.savefig(out/'candidate.png',dpi=150,bbox_inches='tight')
(out/'macro_placement.tcl').write_text('foreach {inst master x y orient} {\n'+''.join(f'  {{{n}}} ot_sram_1r1w_128x256_m1_r2c2 {x} {y} R0\n' for n,x,y in macros)+'} {\n  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact\n}\n')
