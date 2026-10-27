import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
w,h=241.92,293.76;mw,mh=172.824,41.064
ys=[4.32,49.68,95.04,166.32,211.68]
r={'outline_um':[w,h],'macro_um':[mw,mh],'macro_origins_um':[[34.56,y]for y in ys],
   'macro_count':5,'macro_area_um2':5*mw*mh,'macro_fill':5*mw*mh/(w*h),
   'clock_entry_um':[120.984,146.88],'side_channels_after_4p32halo_um':[30.24,w-34.56-mw-4.32],
   'centre_channel_um':ys[3]-(ys[2]+mh),'key_bits_in':1099,'key_bits_out':1099,
   'pins_per_um_keyface':1099/w,'data_cycle_delta':0,
   'old_macro_count':34,'new_macro_count':40,'old_lot_area_um2':324**2,
   'old_macro_area_um2':34*mw*mh,'new_macro_area_um2':40*mw*mh,
   'eight_slice_lot_area_um2':8*w*h,'extra_lot_area_per_keybuf_um2':8*w*h-324**2,
   'status':'ANALYTIC LOT ONLY; not a placement, native binding and hub repack pending'}
p=Path(__file__).parent;p.joinpath('lot_model.json').write_text(json.dumps(r,indent=2)+'\n')
f,a=plt.subplots(figsize=(7,8));a.add_patch(Rectangle((0,0),w,h,fill=False,lw=2))
for i,y in enumerate(ys):
 a.add_patch(Rectangle((34.56,y),mw,mh,facecolor='#8ebad6',edgecolor='#274c64'))
 a.text(34.56+mw/2,y+mh/2,f'SRAM{i} 256x256',ha='center',va='center',fontsize=9)
a.axvline(30.24,color='#bbb',ls=':');a.axvline(w-30.24,color='#bbb',ls=':')
a.scatter([120.984],[146.88],marker='*',s=170,color='darkorange',zorder=5,label='M5 clock entry')
a.plot([8.64,w-8.64],[h,h],color='green',lw=4,label='1099-bit key input, M5')
a.plot([8.64,w-8.64],[0,0],color='purple',lw=4,label='1099-bit key output, M5')
a.set(xlim=(-8,w+8),ylim=(-8,h+8),aspect='equal',xlabel='um',ylabel='um',title='Key-line slice: five real SRAMs, 50% macro fill\nAnalytic lot; 8 identical slices replace one impossible 324² lot')
a.legend(loc='upper right',fontsize=8);f.tight_layout();f.savefig(p/'lot_model.png',dpi=160)
print(json.dumps(r))
