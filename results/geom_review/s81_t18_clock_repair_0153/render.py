import json, pathlib,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
r=pathlib.Path('/srv/opentallas-scratch/claude/wt/codex-s81-die-2032/results/geom_review/s81_t18_clock_repair_0153');d=json.load(open(r/'native_census.json'));s=[s for s,a in zip(d['sinks'],d['assignment']) if a==16];old=d['taps'][16][1:];new=[197.088,294.112]
f,ax=plt.subplots(figsize=(8,7));ax.scatter([x[0] for x in s],[x[1] for x in s],s=6,c='steelblue',label='419 actual native assigned sinks')
for xy,c,label in [(old,'crimson','old151.093 >150'),(new,'darkgreen','new149.971 ≤150')]:
 x,y=xy;ax.plot([x,x+150,x,x-150,x],[y+150,y,y-150,y,y+150],color=c,alpha=.65,label=label);ax.scatter([x],[y],c=c,s=35)
ax.set_aspect('equal');ax.set_xlabel('x / µm');ax.set_ylabel('y / µm');ax.set_title('slice_station__t18 clk_t16: same bound / same sink membership');ax.legend(fontsize=8);f.tight_layout();f.savefig(r/'actual_native_tap_repair.png',dpi=150)
