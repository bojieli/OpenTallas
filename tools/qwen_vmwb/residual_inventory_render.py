#!/usr/bin/env python3
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R=Path(__file__).resolve().parents[2]/'results/arch/qwen_vm_residual_1015/physical_inventory'
x=json.loads((R/'inventory.json').read_text())
colors={'qvm_bank_banked_native':'#7896ab','qvm_su_bank_native':'#d6ab72','qfd_vm_qcommit':'#ba6276'}
for key,v in x['alternatives'].items():
 W,H=v['outline_um'];fig,ax=plt.subplots(figsize=(12,max(7,12*H/W)))
 for b in v['rectangles']:
  ax.add_patch(Rectangle((b['x'],b['y']),b['w'],b['h'],facecolor=colors.get(b['class'],'#8aaf8c'),edgecolor='white',linewidth=.35))
  if b['class'] in colors and b['w']>100:ax.text(b['x']+b['w']/2,b['y']+b['h']/2,f"R{b['region']} {b['class'].replace('qvm_','').replace('_native','')}",fontsize=4,ha='center',va='center')
 ax.set(xlim=(0,W),ylim=(0,H),xlabel='um',ylabel='um',title=f'{key}: 487 actual LEF rectangles, 20 um channels\n{W:.1f} x {H:.1f} um; residual FFs/clock/PG/repeaters and incident cuts OPEN')
 ax.set_aspect('equal');fig.tight_layout();fig.savefig(R/(key+'.png'),dpi=130);fig.savefig(R/(key+'.svg'));plt.close(fig)
