import csv,sys,re,json
# usage: coloc.py psm_dir W H keepoff  -> co-located VDD drop + VSS bounce per load block (canonical interior by block centre)
d,W,H,ko=sys.argv[1],float(sys.argv[2]),float(sys.argv[3]),float(sys.argv[4])
ER=[float(v) for v in sys.argv[5:9]] if len(sys.argv)>8 else None  # optional eval rect (window-local), block centre inside
def rd(f,gnd):
    o={}
    for r in csv.DictReader(open(f)):
        v=float(r['Voltage']); mv=(v if gnd else 0.7-v)*1e3
        k=r['Instance']; o[k]=max(o.get(k,-1),mv)
    return o
vdd=rd(d+'/ir_VDD.csv',False); vss=rd(d+'/ir_VSS.csv',True)
# block placements from psm.tcl ot_pl lines + size from irblk.lef
pl={m[1]:(float(m[2]),float(m[3])) for m in re.finditer(r'^ot_pl (\S+) (\S+) (\S+)',open(d+'/psm.tcl').read(),re.M)}
sz=float(re.search(r'SIZE (\S+) BY',open(d+'/irblk.lef').read())[1])
pw={m[1]:float(m[2]) for m in re.finditer(r'set_pdnsim_inst_power -inst (\S+) -power (\S+)',open(d+'/psm.tcl').read())}
res=[];
for k in pl:
    if k not in vdd or k not in vss: continue
    cx,cy=pl[k][0]+sz/2,pl[k][1]+sz/2
    inter = (ER[0]<=cx<=ER[2] and ER[1]<=cy<=ER[3]) if ER else (ko<=cx<=W-ko and ko<=cy<=H-ko)
    res.append((vdd[k]+vss[k],k,cx,cy,inter,vdd[k],vss[k]))
res.sort(reverse=True)
I=[r for r in res if r[4]]
print(json.dumps(dict(loads=len(res),placed=len(pl),powered=len(pw),total_w=round(sum(pw.values()),4),
  all_worst=res[0][:4]+res[0][5:],interior_pairs=len(I),interior_worst=I[0][:4]+I[0][5:] if I else None,
  vdd_max=round(max(vdd.values()),3),vss_max=round(max(vss.values()),3),block_um=sz)))
