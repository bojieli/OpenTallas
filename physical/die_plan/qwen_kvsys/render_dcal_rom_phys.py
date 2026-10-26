#!/usr/bin/env python3
"""Render real SYS_C3 context with plan_review.draw_base, plus actual LEF-pin closeups."""
from pathlib import Path
import argparse,json,re,sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/die_plan'));sys.path.insert(0,str(ROOT/'tools/geom_review'))
import schema as S,gen_phys as G,plan_review as PR
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.ticker import FuncFormatter


def render(plan,out):
    raw=json.loads(plan.read_text());P=S.Plan(raw,path=plan);tn='kv3_sys_c';t=P.types[tn]
    part=next(n for n,p in P.parts.items() if p['type']==tn)
    assert P.orient(part)=='R0','render is in authoritative R0 SYS_C frame'
    x0,y0,_,_=P.rect(part);out.mkdir(parents=True,exist_ok=True)
    hcs=[]
    for c in t['contents']:
        x,y=c['origin_um'];w,h=c['outline_um']
        hcs.append((part,c['inst'],c['module'],(x0+x,y0+y,x0+x+w,y0+y+h)))
    taps={n:(x0+x,y0+y) for n,x,y in G.clock_pins(P,tn)}
    rom=next(c for c in t['contents'] if c['inst']=='u_bound.u_dcal.u_profile')
    rx,ry=rom['origin_um'];rw,rh=rom['outline_um'];halo=4.32
    lef=(ROOT/rom['lef']).read_text();pins=[]
    for name,block in re.findall(r'^  PIN (.*?)\n(.*?)^  END [^\n]+$',lef,re.S|re.M):
        if name in('VDD','VSS'):continue
        m=re.search(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',block)
        if m:
            a,b,c,d=map(float,m.groups());pins.append((name,rx+(a+c)/2,ry+(b+d)/2))
    ft=[xy for slot in t.get('ft_slots',[]) for row in slot.get('bit_sites_um',[]) for xy in row]
    views=[('sys_c_context.png',[0,0,*t['outline_um']],(16,8)),
           ('rom_context_closeup.png',[260,210,350,290],(9,8)),
           ('rom_pin_closeup.png',[296,244,318,267],(9,9))]
    for filename,view,figsize in views:
        fig,ax=plt.subplots(figsize=figsize,dpi=170)
        rect=(x0+view[0],y0+view[1],x0+view[2],y0+view[3])
        PR.draw_base(ax,P,{},hcs,taps,rect=rect,lanes=False)
        for box in t['clock'].get('keepouts_um',[]):
            a,b,c,d=box;ax.add_patch(Rectangle((x0+a,y0+b),c-a,d-b,fill=False,ec='tomato',ls='--',lw=1.1))
        if filename=='sys_c_context.png' and ft:
            ax.scatter([x0+p[0] for p in ft],[y0+p[1] for p in ft],s=.35,c='navy',alpha=.55,label='Actual FT station sites')
        ax.add_patch(Rectangle((x0+rx,y0+ry),rw,rh,fc='mediumturquoise',ec='black',lw=1.0,zorder=9))
        ax.plot([x0+x for n,x,y in pins if n!='clk'],[y0+y for n,x,y in pins if n!='clk'],ls='',marker='.',ms=3,color='darkgreen',zorder=10)
        clk=next(p for p in pins if p[0]=='clk')
        ax.plot(x0+clk[1],y0+clk[2],'o',ms=5,color='crimson',zorder=11)
        ax.annotate('clk M4 (302.412,251.340)',(x0+clk[1],y0+clk[2]),xytext=(14,25),textcoords='offset points',fontsize=8,color='crimson',arrowprops={'arrowstyle':'->','color':'crimson'},zorder=12)
        if filename=='sys_c_context.png':
            ax.annotate('D-ROM profile ROM:8.856x9.192um',(x0+rx,y0+ry),xytext=(-120,-35),textcoords='offset points',fontsize=8,arrowprops={'arrowstyle':'->'},zorder=12)
            for c in t['contents'][:-1]:
                cx,cy=c['origin_um'];cw,ch=c['outline_um'];label='UCIe PHY M6 PG' if 'ucie' in c['module'] else 'SRAM'
                ax.text(x0+cx+cw/2,y0+cy+ch/2,label,ha='center',va='center',fontsize=7,zorder=12)
        else:
            ax.text(x0+rx+rw/2,y0+ry+rh/2,'64x32m2\n81.404um2',ha='center',va='center',fontsize=8,zorder=12)
            ax.text(x0+rx-halo,y0+ry+rh+halo+1,'4.32um clock keepout halo',fontsize=8,color='tomato',zorder=12)
        ax.set_xlim(rect[0],rect[2]);ax.set_ylim(rect[1],rect[3]);ax.set_aspect('equal')
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x,pos:f'{x-x0:g}'))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda y,pos:f'{y-y0:g}'))
        ax.set_xlabel('SYS_C type-frame x (um)');ax.set_ylabel('SYS_C type-frame y (um)')
        ax.set_title('SYS_C3 + D-ROM: placement-only candidate; actual b18 scalar/cache clustering still required',fontsize=10)
        ax.grid(alpha=.15);fig.tight_layout();fig.savefig(out/filename);plt.close(fig)
    print(out)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('plan',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args();render(a.plan,a.out)
