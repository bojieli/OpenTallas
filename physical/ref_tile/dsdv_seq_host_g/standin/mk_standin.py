# declared lk pin stand-in for the s10g / s10h outlines (NOT a view): s10f --cts stand-in LEF re-shaped to the successor
# outline. Pin faces + order = s10g/s10h kit pin plan (one --pin-region per face, same faces as s10f; the tool orders a
# face alphabetically, as s10f came out); positions scaled along each face and snapped to the 0.192 track phase; OBS scaled;
# timing models = s10f stand-in libs (same ports, same RTL behaviour; area patched).
import re,sys,os,shutil
src,dst,W2,H2,tag=sys.argv[1],sys.argv[2],float(sys.argv[3]),float(sys.argv[4]),sys.argv[5]
os.makedirs(dst,exist_ok=True)
txt=open(f'{src}/dsdv_sh_lk.lef').read()
W,H=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',txt).groups())
sx,sy=W2/W,H2/H; P=0.192
f=lambda v:f'{v:.3f}'.rstrip('0').rstrip('.') if '.' in f'{v:.3f}' else f'{v:.3f}'
def snapd(c,s): return c+round((c*s-c)/P)*P
out=[];pinname=None;inobs=False;pg=False;seen={}
for ln in txt.split('\n'):
    m=re.match(r'\s*PIN\s+(\S+)',ln)
    if m: pinname=m.group(1); pg=pinname in('VDD','VSS')
    if re.match(r'\s*END\s+'+re.escape(pinname or '#'),ln): pinname=None
    if re.match(r'\s*OBS',ln): inobs=True
    if ln.strip().startswith('SIZE'): ln=f'  SIZE {f(W2)} BY {f(H2)} ;'
    r=re.match(r'(\s*RECT\s+)([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)(.*)',ln)
    if r:
        x0,y0,x1,y1=map(float,r.groups()[1:5])
        if inobs:
            x0,x1,y0,y1=x0*sx,x1*sx,y0*sy,y1*sy
        elif pg:   # vertical M5 strap: keep width, keep edge gaps
            d=snapd((x0+x1)/2,sx)-(x0+x1)/2; x0+=d;x1+=d; y1=H2-(H-y1)
        else:
            cx,cy=(x0+x1)/2,(y0+y1)/2
            if y1>=H-1e-6:   # N
                d=snapd(cx,sx)-cx; x0+=d;x1+=d; y0,y1=H2-(H-y0),H2; key=('N',round(x0,3))
            elif y0<=1e-6:   # S
                d=snapd(cx,sx)-cx; x0+=d;x1+=d; key=('S',round(x0,3))
            elif x1>=W-1e-6: # E
                d=snapd(cy,sy)-cy; y0+=d;y1+=d; x0,x1=W2-(W-x0),W2; key=('E',round(y0,3))
            else:            # W
                d=snapd(cy,sy)-cy; y0+=d;y1+=d; key=('W',round(y0,3))
            assert key not in seen,(key,pinname,seen.get(key)); seen[key]=pinname
        ln=f'{r.group(1)}{x0:.3f} {y0:.3f} {x1:.3f} {y1:.3f}{r.group(6)}'
    out.append(ln)
open(f'{dst}/dsdv_sh_lk.lef','w').write('\n'.join(out))
for c in('tt','ff','ss'):
    t=open(f'{src}/dsdv_sh_lk_{c}.lib').read()
    t=re.sub(r'(cell \("dsdv_sh_lk"\) \{\s*area : )[\d.]+',lambda m:m.group(1)+f'{W2*H2:.3f}',t,count=1)
    open(f'{dst}/dsdv_sh_lk_{c}.lib','w').write(t)
shutil.copy(f'{src}/insertion.json',f'{dst}/insertion.json')
open(f'{dst}/STANDIN_NOT_A_VIEW','w').write(f"declared pin stand-in for dsdv_sh_lk_{tag} ({W2} x {H2}, p192 masters, claude/s81-shlk-1021 @254543064): "
  f"s10f --cts stand-in (regate 4e02f8a41, placement-estimated, NOT routed, NOT closed) re-shaped to the {tag} outline by the {tag} kit pin plan "
  f"(per-face pin regions, alphabetical face order as the tool places them, positions scaled x{sx:.4f} / y{sy:.4f} and snapped to the 0.192 track phase; "
  f"OBS scaled; s10f timing models + insertion.json, area patched); never bind -- replace by the {tag} --cts stand-in / closed view\n")
print(tag,'pins',len(seen),'sx',sx,'sy',sy)
