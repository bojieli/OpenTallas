import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=Path(__file__).parent;d=json.load(open(P/'estimate.json'));q=d['output_window_candidate'];f,a=plt.subplots(figsize=(10,8));a.set_xlim(0,760.32);a.set_ylim(0,691.2);a.set_aspect('equal')
a.plot([.096,.096],[4.872,689.016],c='#cc5555',lw=4,label='Old output512 Wwindow (FAIL)');a.plot([.096,.096],[302.4,388.8],c='#00aa55',lw=6,label='Conditional output86.4um window');a.plot([760.224,760.224],[23.016,689.016],c='#bb5500',lw=4,label='SharedSWD2048 Ewindow (still FAIL)')
for m in q['output_macro_positions']:
 x,y=m['origin_um'];a.add_patch(Rectangle((x,y),172.824,41.064,fc='#9ac6e5',ec='#356a91',lw=.6));a.text(x+86.4,y+20,str(int(m['k'].split('g_bank[')[1].split(']')[0])),ha='center',fontsize=7)
a.add_patch(Rectangle((683.184,0),77.136,691.2,fc='#ffddb0',alpha=.4));a.text(715,345,'SWD forced\n77um strip\nCannot hold\n32banks',ha='center',va='center',fontsize=9)
a.text(495,345,'Other32banks, clockislands,\nreset and sharedstagepin repair\nUNRESOLVED — no physicalbuild',ha='center',va='center',fontsize=10)
a.set_title('OPSTORE_B source/pin bound + conditional output-only repair\nOutput16banks max399.738um; fullcore remains FAIL (ESTIMATE)');a.legend(loc='lower center',fontsize=8);a.set_xlabel('um');a.set_ylabel('um');f.tight_layout();f.savefig(P/'output_window_estimate.png',dpi=150)
