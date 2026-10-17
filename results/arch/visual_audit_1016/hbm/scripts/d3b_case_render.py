import json,re
from PIL import Image, ImageDraw
d=json.load(open('manifest.json')); W,H=d['die_um']
S=1800/W; cw,ch=int(W*S)+20,int(H*S)+60
im=Image.new('RGB',(cw,ch),'white'); g=ImageDraw.Draw(im)
X=lambda x:10+x*S; Y=lambda y:50+(H-y)*S
col={'ot_hbm3e_phy_rc_e8p5':(150,200,230),'ot_hbm_svc_pc_ctrl_leaf':(240,200,120),'ot_hbm_svc_sm_group':(180,230,180),'ot_hbm_accel_smh_static':(200,200,240),'hfd_stn_v15_cc1182':(250,150,150)}
g.rectangle([X(0),Y(H),X(W),Y(0)],outline='black',width=2)
for k,v in d['placement'].items():
    w,h=v['w'],v['h']
    if v['o'] in('R90','R270','MXR90','MYR90'): w,h=h,w
    g.rectangle([X(v['x']),Y(v['y']+h),X(v['x']+w),Y(v['y'])],fill=col[v['m']],outline=(60,60,60))
pts={'dks':[], 'dkh':[], 'rly':[]}
for l in open('place.txt'):
    m=re.search(r'-name (\S+) -location \{([\d.]+) ([\d.]+)\}',l)
    if not m: continue
    n=m.group(1); x,y=float(m.group(2)),float(m.group(3))
    for p in pts:
        if n.startswith(p): pts[p].append((x,y))
c={'dks':(0,150,0),'dkh':(200,0,200),'rly':(255,0,0)}
for p in ('dks','dkh','rly'):
    for x,y in pts[p]: g.rectangle([X(x)-1,Y(y)-1,X(x)+1,Y(y)+1],fill=c[p])
g.text((10,5),'d3b die case (E4, GRT running; OLD compact660_v5 plan 660 mm2, grants v6) -- NOT_A_DIE_RESULT diagnostic',fill='black')
g.text((10,20),'blue PHY, orange pc_ctrl, green svc_sm_group, lilac SM static, pink stn relay tiles; dots: green stream clk bufs %d, magenta hbm clk bufs %d, red relays %d'%(len(pts['dks']),len(pts['dkh']),len(pts['rly'])),fill='black')
im.save('d3b_case.png'); print(im.size,{k:len(v) for k,v in pts.items()})
