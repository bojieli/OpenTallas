#!/usr/bin/env python3
"""DIE-HBM-83-OPSG: macro placements + GPL guide boxes for the operand group hub forms (part 57). mk_forms.py OUT_DIR
Bank k = macro k in list order. Core 4.32..756 x 4.32..228.96. Writes place_<form>.json, boxes_<form>_<opsa|opsb>.json"""
import json,sys,os
O=sys.argv[1]; W,H=760.32,233.28; MW,MH=92.664,43.752; M="ot_sram_1r1w_2048x32_m8_r0c0_g32"; CORE=(4.32,4.32,756.0,228.96)
gy4=(H-2*8.64-4*MH)/3; R4=[8.64+r*(MH+gy4) for r in range(4)]
gy3=(H-2*12.96-3*MH)/2; R3=[12.96+r*(MH+gy3) for r in range(3)]
c22=[30.24,142.344,525.312,637.416]; c3=[21.6,125.064,228.528,439.128,542.592,646.056]
F={ '22':([(x,y) for x in c22 for y in R4],(246.,514.)),
    '332':([(x,R3[r]) for i,x in enumerate(c3) for r in ((0,2) if i in(2,3) else (0,1,2))],(332.,428.)),
    '3el':([(x,y) for x in c22[:0]+[21.6,133.704,245.808] for y in R4]+[(x,y) for x in c22[2:] for y in R4[:2]],(349.,514.)) }
for fn,(ML,hub) in F.items():
    assert len(ML)==16
    for i,a in enumerate(ML):
        assert CORE[0]<=a[0] and a[0]+MW<=CORE[2] and CORE[1]<=a[1] and a[1]+MH<=CORE[3],a
        for b in ML[i+1:]:
            assert a[0]+MW+8.64<=b[0] or b[0]+MW+8.64<=a[0] or a[1]+MH+8.64<=b[1] or b[1]+MH+8.64<=a[1],(a,b)
    json.dump(dict(schema="die-hbm-83-opsg.macro_placement.v1",form=fn,macro_placement=[dict(k=k,macro=M,origin_um=[round(x,3),round(y,3)],orient="R0") for k,(x,y) in enumerate(ML)]),open(f"{O}/place_{fn}.json","w"),indent=1)
    for t,P in (('opsa','u_fcore.u_t.u_g.'),('opsb','u_fcore.u_g.')):
        bx=[]
        for k,(x,y) in enumerate(ML):
            xg=min([9.0]+[(abs(o[0]-x)-MW)/2-.05 for o in ML if abs(o[0]-x)>=MW and not(o[1]+MH<=y or y+MH<=o[1])])
            yg=min([6.0]+[(abs(o[1]-y)-MH)/2-.05 for o in ML if abs(o[1]-y)>=MH and not(o[0]+MW<=x or x+MW<=o[0])])
            bx.append(dict(name=f"bk{k}",prefixes=[f"{P}g_bank[{k}].",f"{P}b_q[{k}]["],box_um=[round(v,3) for v in (max(CORE[0],x-xg),max(CORE[1],y-yg),min(CORE[2],x+MW+xg),min(CORE[3],y+MH+yg))]))
        bx.append(dict(name="hub",prefixes=[P+s for s in("g_s1.","g_s2.","g_hc.","g_lane[","q_out[","fq[","wcoll_q","hc[")],box_um=[hub[0],9.0,hub[1],224.0]))
        json.dump(dict(schema="die-hbm-83-opsg.reg_guide_boxes.v1",boxes=bx),open(f"{O}/boxes_{fn}_{t}.json","w"),indent=1)
    print(fn,'ok hub',hub)
