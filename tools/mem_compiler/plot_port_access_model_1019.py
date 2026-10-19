#!/usr/bin/env python3
"""Plot the analytical access rectangles, not a placement or routed view.

Fleet CLI: pass a JSON subset containing outline, original box, paths and PG.
Returns base64 PNGs for transport; caller saves them without model output logs.
"""
import base64
import io
import json
import sys
import zlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

data=json.loads(zlib.decompress(base64.b64decode(sys.argv[1])))
colors={'M4':'#2176ae','M5':'#e07b21'}


def draw(name,limits,size):
    fig,ax=plt.subplots(figsize=size)
    offset=data['core_offset_nm'][0]/1000
    old_w,old_h=[v/1000 for v in data['old_outline_nm']]
    w,h=[v/1000 for v in data['outline_nm']]
    ax.add_patch(Rectangle((offset,0),old_w,old_h,facecolor='#eeeeee',edgecolor='#555555',linewidth=.8))
    for p in data['pg_rectangles']:
        x0,y0,x1,y1=[v/1000 for v in p['rect_nm']]
        ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor='#aaaaaa',edgecolor='none',alpha=.6))
    for p in data['paths']:
        for s in p['shapes']:
            x0,y0,x1,y1=[v/1000 for v in s['rect_nm']]
            ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,
                         facecolor='#9b2a99' if p['kind']=='clock' else colors[s['layer']],edgecolor='none'))
        for v in p['vias']:
            x0,y0,x1,y1=[v/1000 for v in v['cut_rect_nm']]
            ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor='#222222',edgecolor='none'))
    ax.add_patch(Rectangle((0,0),w,h,fill=False,edgecolor='#bb2222',linewidth=1))
    ax.set_xlim(limits[0],limits[1]);ax.set_ylim(limits[2],limits[3])
    ax.set_aspect('equal');ax.set_xlabel('um');ax.set_ylabel('um')
    ax.set_title('Analytical access model — native DRC / parent access pending\n'+name,fontsize=11)
    ax.text(.01,-.30 if name!='full outline' else -.42,
            'M4: blue   M5: orange   VIA45 cut: black   clock: purple   inherited box/PG: gray',
            transform=ax.transAxes,fontsize=8)
    fig.tight_layout()
    stream=io.BytesIO();fig.savefig(stream,format='png',dpi=220,bbox_inches='tight');plt.close(fig)
    return base64.b64encode(stream.getvalue()).decode()

w,h=[v/1000 for v in data['outline_nm']]
print(json.dumps(dict(full=draw('full outline',[-1,w+1,-1,h+1],(12,3.9)),
                     corner=draw('W lower corner: reversed columns and real enclosures',[-.04,1.3,.65,2.55],(7.8,8.5)))))
