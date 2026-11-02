import pathlib,json,gzip
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
w=pathlib.Path('/srv/opentallas-scratch/claude/wt/codex-qc62-collect-1101');o=w/'results/qc_die62_1101/codex_core_coupled_geometry_prep';g=json.load(open(o/'geometry_eio2/MACRO_GEOMETRY.json'));s=json.load(gzip.open(o/'eio2_reader_source_PREP/JOINT_SITE_PROPOSAL.json.gz'));fig,ax=plt.subplots(figsize=(10,13))
for m in g['macros']:
 x,y=m['origin_um'];a,b=m['outline_um'];h=m['halo_um'];name=m['inst'];fold='fold' in str(m).lower();ax.add_patch(Rectangle((x-h,y-h),a+2*h,b+2*h,fc='#eeeeee',ec='#bbbbbb',lw=.4));ax.add_patch(Rectangle((x,y),a,b,fc='#f8d394' if fold else '#c7d9ee',ec='#463b2b' if fold else '#375b7c',lw=.8));ax.text(x+a/2,y+b/2,str(name).split('.')[-2]+'\n'+str(m.get('orient','R0')),fontsize=5,ha='center',va='center')
pts=[z['center_um']for z in s['rows']];ax.scatter([x for x,y in pts],[y for x,y in pts],s=.45,c='#2a7a55',alpha=.6,label='11,308 existing macro-adjacent FF proposals')
ax.set(xlim=(0,760.32),ylim=(0,1032.48),aspect='equal',xlabel='CORE local X (um)',ylabel='CORE local Y (um)',title='Held CORE source geometry: 21 SRAM + 8 uniform fold cuts\nJoint reader sites; new EIO view and internal R90 support UNQUALIFIED');ax.legend(loc='upper left',fontsize=7);ax.grid(alpha=.12);fig.text(.1,.025,'Conditional source PREP only. 2,849 selected FF edges <=398.628um; 16,674 predecessor edges unplaced.\nNo GEN, native placement, clock/reset/PG/START/boot closure, or source/view qualification.',fontsize=9);fig.tight_layout(rect=(0,.07,1,1));fig.savefig(o/'eio2_reader_source_PREP/CORE_JOINT_READER_PREP.png',dpi=150)
