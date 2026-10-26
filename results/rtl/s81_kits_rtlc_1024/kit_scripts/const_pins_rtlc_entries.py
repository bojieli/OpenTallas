import json, collections
F="physical/die_plan/s81/inputs/const_pins_dropped.json"
d=json.load(open(F), object_pairs_hook=collections.OrderedDict)
def pk(name, keep, width, packed):
    keep=sorted(keep); ks=set(keep); gone=[f"{name}[{i}]" for i in range(width) if i not in ks]
    ren={f"{name}[{o}]":f"{name}[{n}]" for n,o in enumerate(keep) if o!=n} if packed else {}
    return gone, ren
CTLK=[0]+list(range(9,13))+list(range(21,38))+[39]+list(range(42,189))
DLK=list(range(1,4))+list(range(40,50))+list(range(52,276))
CWK=list(range(0,6))+[8,9]
def ent(specs, why):
    g=[]; r={}
    for name,keep,w in specs:
        a,b=pk(name,keep,w,isinstance(keep,list)); g+=a; r.update(b)
    e=collections.OrderedDict(pins=g, why=why)
    if r: e["rename"]=r
    return e
CTLW="CTL row packed (S81-KITS-RTLC 10-24): ctl() bits 1..8, 13..20, 38, 40, 41, 189..275 are constant 0 on every producer (L5 / L3 / L1 rows); the seam carries {w[188:42], w[39], w[37:21], w[12:9], w[0]} (170, rename: kept bits keep their closed-view positions); L2 unpacks before the vstop inject"
new=collections.OrderedDict()
new["dsdv_gunit_l3"]=ent([("w_b",CTLK,276),("rw_x",range(192),512)], CTLW+"; rw_x[511:192] were 0 at L1 (only [191:0] written): input narrowed to rw_x[191:0]")
new["dsdv_gunit_l1"]=ent([("w_b",CTLK,276),("ct_b",CTLK,276),("rw_x",range(192),512),("dl_a",DLK,276),("dl_b",DLK,276),("cw_a",CWK,10)],
  CTLW+"; rw_x[511:192] constant 0 (narrowed); dl_a / dl_b bits 0, 4..39, 50, 51 not read (packed {dl[275:52], dl[49:40], dl[3:1]}, 237); cw_a[7:6] not read (packed {a[9:8], a[5:0]})")
new["dsdv_gunit_l1c"]=ent([(n,[0],4) for n in ("f_v","f_f","f_l","f_g")]+[("f_d",[246*q+k for q in range(4) for k in range(246) if k!=205],984)],
  "S81-KITS-RTLC 10-24: L1c reads f_v / f_f / f_l / f_g of front 0 only (fronts 1..3 are the same L1f master: their outputs stay, open) and o_d[205] of no front: L1f o_d packed {d[245:206], d[204:0]} (245 per front, rename)")
new["dsdv_gunit_l2"]=ent([("hct_b",CTLK,276),("rct_b",CTLK,276),("hp_a",range(40,244),276),("hp_b",range(40,244),276),("dl_a",DLK,276),("dl_b",DLK,276),("cws_a",CWK,10),("cwn_a",CWK,10),("cw_a",CWK,10)],
  CTLW+"; hp_a / hp_b: L0 reads [243:40] only (port narrowed, names kept); dl_a / dl_b and cws_a packed as L1 reads them; cw_a (unit pins) / cwn_a packed {a[9:8], a[5:0]}: no gunit leaf reads a[7:6] (L0 / L4 / L1 / L5 decode a[9:8], a[5:0] only)")
new["dsdv_gunit_l0"]=ent([("hct4_b",CTLK,276),("hct_b",CTLK,276),("hp_a",range(40,244),276),("hp_b",range(40,244),276),("cw_a",CWK,10),("cwo_a",CWK,10)],
  CTLW+" (L0 relays L5/L4 rows); hp_a / hp_b [0..39], [244..275] not read: port [243:40]; cw_a / cwo_a packed {a[9:8], a[5:0]} (a[7:6] read by no gunit leaf)")
new["dsdv_gunit_l4"]=ent([("hct5_b",CTLK,276),("hct_b",CTLK,276),("cwo_a",CWK,10),("cw_a",CWK,10)], CTLW+" (L4 relays L5 rows); cw_a / cwo_a packed {a[9:8], a[5:0]} (no gunit leaf reads a[7:6])")
new["dsdv_gunit_l5"]=ent([("ct_b",CTLK,276),("cw_a",CWK,10)], CTLW+"; cw_a[7:6] not read (packed {a[9:8], a[5:0]})")
XW="S81-KITS-RTLC 10-24: ring bits read by nothing / constant: dl_e / dl_w [0] and [1076..1103] (ring valid is dl_*v; the top 28 ring bits are never set), dl_vb[0], ci_b[1076..1103] (TIELO), x_si[7] (max index 59); ports narrowed, names kept"
new["ot_s81sl_xrt1"]=ent([("dl_e",range(1,1076),1104),("dl_w",range(1,1076),1104),("dl_vb",range(1,276),276),("ci_b",range(1076),1104),("x_si",range(7),8)], XW)
new["ot_s81sl_xrt3"]=ent([("dl_e",range(1,1076),1104),("dl_w",range(1,1076),1104),("dl_vb",range(1,276),276),("ci_b",range(1076),1104),("x_si",range(7),8),("bi",list(range(7))+list(range(37,1076)),1104)],
  XW+"; band input bi packed {B[1075:37], B[6:0]} (B[7..36] ring header fields and B[1076..] are not read; rename)")
m=d["modules"]; d["modules"]=collections.OrderedDict(list(new.items())+[(k,v) for k,v in m.items() if k not in new])
json.dump(d, open(F,"w"), indent=1)
for k,v in new.items(): print(k, len(v["pins"]), len(v.get("rename",{})))
