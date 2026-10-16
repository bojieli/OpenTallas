from PIL import Image, ImageDraw, ImageFont
import os,sys
T='/tmp/claude-1000/visaudit/tiles'
items=[
 ('xl2_ctl_cl2d','H-SM  ot_hgi_sm_xload_cl2_ctl cl2d  NEEDS_RTL TT -92.5 DRC 4','345.6^2 um, fill 12%, 10,786 pins on 100% of all faces (W 9.6/um); logic at W-mid, worst path diagonal to SE corner'),
 ('xl2_bdring_cl2d','H-SM  ot_hgi_sm_xload_cl2_bdring cl2d  routed TT +13.7 (native L392.9/C511.7 at cl2c)','clock pin W-centre, all logic + 2,080 pins on E face: clock crosses 173 um of empty W half'),
 ('strap_q2_s4h','H-SM  hfd_vms_bank_strap_q0..q3 strap4  TT -111 (q3) / -149.9 (q0 strap2)','3 SRAM stack centred -> logic in a 30-46 um ring; 4,518 pins on 98% of all faces; clock N-centre, paths go around the stack'),
 ('vm_cal_u','H-NETLIST/HARDEN  hfd_hgi_vm_calendar (compact)  CLOSED, native FAIL L222/C206/spread 92.8','SRAM centred, logic split W|E clusters; clock W-low must wrap the macro to reach E cluster'),
 ('hcoll_vmwrite_spread','H-NETLIST(COLL)  ot_hgi_coll_static_vmwrite spread  routed','103.7 x 388.8 strip, 5,123 pins, fill 21%; clock N end -> 389 um to S capture; worst path N-E -> S-W'),
 ('smh_tile_rp3','H-SM  ot_hbm_accel_smh_tile_eg rp3 (floorplan stage)','W and E: 3,705 pins each inside 203 um (18.2 pins/um, 366 per 20 um) = 17% of a 1,192 um face; rest of faces empty'),
 ('smh_bdc_d62','H-SM  ot_hbm_accel_smh_bdc d62  route crashed x2','1,094 of 1,158 pins on S face (10.5 pins/um); clock at N-W corner, opposite the IO face'),
 ('pcctrl','H-DIE  hdie_pc_ctrl_cfg gate (128 instances)  placement setup -208 ps','2 SRAMs centre-right: logic forms a C around W; E strip empty; clock pin W-low, pins N/S'),
 ('su_bank6_r11','H-SU  ot_hbm_su_static_bank6_clock_physical r11  CLOSED native PASS','391 x 151, 6 SRAMs, std cells 684 um2: fill 41%, 95% of free bins < 0.1 density -> outline 20-25% too big (SU over budget 3.7 mm2)'),
 ('su_reduce_r4','H-SU  ot_hbm_su_reduce_static r4  CLOSED','216 x 151, fill 27%; pins W/E packed in 5-6% of face (14 pins/um); macro margins wasted'),
 ('xl2_bfq_cl2b','H-SM  ot_hgi_sm_xload_cl2_bfq cl2b CLOSED / cl2c crashed','345.6 x 298, 8 SRAMs, std 2.6k um2, fill 33%; 1,024 pins on N half-face; clock W'),
 ('dbk_ctl_rm1','H-NETLIST/HARDEN  ot_hgi_dma_back_static_vp4_controller rm1  CLOSED TT +71','69 x 69, density mean 0.59, 27% bins > 0.8, max 1.41 -> over-full tile (watch DRC/hold on re-kit)'),
]
def load(p,w):
    try: i=Image.open(p).convert('RGB')
    except Exception: return None
    return i.resize((w,max(1,int(i.height*w/i.width))))
CW=330; rows=[]
font=ImageFont.load_default()
for s,t1,t2 in items:
    ims=[load(f'{T}/{s}/{n}',CW) for n in ('img/floorplan.png','img/density.png','rep/final_worst_path.png')]
    ims=[i for i in ims if i]
    h=min(420,max(i.height for i in ims))
    cell=Image.new('RGB',(CW*3+10,h+38),'white'); d=ImageDraw.Draw(cell)
    d.rectangle([0,0,CW*3+10,36],fill=(235,235,245)); d.text((4,3),t1,fill=(0,0,0),font=font); d.text((4,19),t2,fill=(150,0,0),font=font)
    for k,i in enumerate(ims): cell.paste(i.crop((0,0,CW,min(h,i.height))),(k*(CW+5),38))
    rows.append(cell)
cols=2; W=rows[0].width
out=Image.new('RGB',(W*cols+10,0),'white')
grid=[rows[i:i+cols] for i in range(0,len(rows),cols)]
H=sum(max(c.height for c in g)+8 for g in grid)+40
out=Image.new('RGB',(W*cols+10,H),'white'); d=ImageDraw.Draw(out)
d.text((6,8),'HBM 660 v5 VISUAL AUDIT 2026-10-16 - worst 12 tiles (floorplan | post-place density | ORFS worst path).  Images re-rendered from the routed/placed odb (tools/ref_tile/layout_dump.tcl + layout_png.py).',fill=(0,0,0),font=font)
y=30
for g in grid:
    for k,c in enumerate(g): out.paste(c,(k*(W+10),y))
    y+=max(c.height for c in g)+8
out.save(sys.argv[1]); print(out.size)
