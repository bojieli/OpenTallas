#!/usr/bin/env python3
# H-DIE 10-16 20:30: SM_X option (b) routed check on d4b_place SW quadrant (relay_router, reach 405). usage: smx_option_b_check.py COLUMN_Y0 PAIR_CHANNEL_UM
# result 5571 60 -> SM_X 9 data + 2 pin regs = 11 (corner egress, top-of-span side windows)
import json, copy, sys, relay_router as RR, die_relay_stations as RS
M=json.load(open('/home/ubuntu/artifacts/hdie-d4/d4/d4b_place/manifest.json'))
Y0=float(sys.argv[1]); CH=float(sys.argv[2])
pl=copy.deepcopy(M['placement'])
for n in ['xl_SW_bfq0','xl_SW_bfq1','xl_SW_bfq2','xl_SW_bfq3','xl_SW_bd','sfup_SW','sfus_SW']: pl.pop(n)
sh=CH-19.8
for n in ['sm_SW1','sm_SW3','sm_SW5','sm_SW7']: pl[n]['x']+=sh
X=6560.0
def put(n,yy): pl[n]=dict(m='STORE',x=X,y=yy,w=950.4,h=600.5,o='R0')
put('st_SW23',Y0); put('st_SW01',Y0+600.5)
pl['hb_vms_SW'].update(x=6760.0,y=Y0+1201+5)
cy=Y0+1201+5+673+20
pl['xl_SW_ctl'].update(x=6600.0,y=cy); pl['xl_SW_aqlo'].update(x=6830.0,y=cy); pl['xl_SW_aqhi'].update(x=6950.0,y=cy)
put('st_SW45',9175-(Y0-5511)-600.5); put('st_SW67',pl['st_SW45']['y']-600.5)
R=405.0
r=RR.Router(pl,M['die_um'],R,G=20,carved=M.get('carved_feedthrough'))
ctl=(6600+109,cy+109)
store_c={'st_SW01':(X+940,pl['st_SW01']['y']+10),'st_SW23':(X+700,pl['st_SW23']['y']+10),
 'st_SW45':(X+700,pl['st_SW45']['y']+590),'st_SW67':(X+940,pl['st_SW67']['y']+590)}
store_in={k:(X+475,pl[k]['y']+(590 if pl[k]['y']<cy else 10)) for k in store_c}
xe=7291.2+sh
win={'SW0':(7271,3640),'SW1':(xe,3640),'SW2':(7099,5511),'SW3':(xe+172,5511),'SW4':(7099,9175),'SW5':(xe+172,9175),'SW6':(7271,11050),'SW7':(xe,11050)}
pairs={'st_SW01':['SW0','SW1'],'st_SW23':['SW2','SW3'],'st_SW45':['SW4','SW5'],'st_SW67':['SW6','SW7']}
def depth(a,bs,names):
    P,par,dist=RS.tree(a,bs)
    sl,tail,dep,viol=RR.plan_bus(r,P,par,R,624,names)
    return dep,viol
tot=[]
print('stack', {k:round(pl[k]['y']) for k in store_c}, 'ctl y',round(cy))
for s,c in store_c.items():
    d1,v1=depth(ctl,[store_in[s]],[s]); d2,v2=depth(c,[win[x] for x in pairs[s]],pairs[s])
    print(s,'ctl->store',d1,'store->win',dict(zip(pairs[s],d2)),'viol',v1+v2); tot+=[d1[0]+x for x in d2]
print('SM_X data stages',max(tot),'+2 pin regs ->',max(tot)+2)
