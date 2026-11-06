import argparse,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection
p=argparse.ArgumentParser();p.add_argument('json');p.add_argument('png');a=p.parse_args();d=json.load(open(a.json));fig,ax=plt.subplots(figsize=(8,13));core=d['core_box'];ax.add_patch(Rectangle((core[0],core[1]),core[2]-core[0],core[3]-core[1],fill=False,edgecolor='black'))
cells=d.get('cells',[]);placed=[c for c in cells if c['placed']]
if placed:
 ax.hist2d([c['x']+c['w']/2 for c in placed],[c['y']+c['h']/2 for c in placed],bins=(90,190),range=((core[0],core[2]),(core[1],core[3])),cmap='Blues',cmin=1)
for i,m in enumerate(d['macros']):
 x,y,z,t=m['box'];ax.add_patch(Rectangle((x-4.32,y-4.32),z-x+8.64,t-y+8.64,fill=False,edgecolor='tomato',linestyle=':',linewidth=.8));ax.add_patch(Rectangle((x,y),z-x,t-y,facecolor='#f7c36b',edgecolor='#7b5316'));name=m['name'].split('.')[-1]
 if 'g_cache' in m['name']:name='cache'+m['name'].split('g_cache')[1].split('.')[0].replace('\\','')
 ax.text((x+z)/2,(y+t)/2,name,fontsize=7,ha='center',va='center')
for p in d['clock_pins']:
 x,y,z,t=p['box'];ax.plot((x+z)/2,(y+t)/2,'m*',markersize=11);ax.annotate('stream_clk M5',((x+z)/2,(y+t)/2),xytext=(12,15),textcoords='offset points',fontsize=8,color='purple')
ax.set(xlim=(0,302.4),ylim=(0,639.36),xlabel='x (um)',ylabel='y (um)',aspect='equal');ax.set_title('SVGR_TOP private A — actual '+d['odb'].split('/')[-1]+'\nfunctional '+str(d['counts']['functional'])+'; placed '+str(len(placed))+'; halo row util '+format(d['post_halo_row_util'],'.4f'));fig.tight_layout();fig.savefig(a.png,dpi=160)
