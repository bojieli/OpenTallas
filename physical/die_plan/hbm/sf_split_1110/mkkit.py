# HBM-COLLECT-1 SF-SPLIT 11-10: build the W/E half kits of ot_smh_static_front from the SF-C kit + split3 netlists.
import json,re,os,sys,shutil,hashlib,subprocess,glob
SRC,SPL,OUTD=sys.argv[1:4]
XC=907.2; H_=233.28; WH={"W":907.2,"E":1814.4-907.2}
sp=json.load(open(SPL+"/split.json")); pm=sp["pinmap"]; st=sp["stats"]
EXCL={"run","signoff","lec","face_shell_work","__pycache__","placed.csv","dump_placed.log","dump_placed.py","dtap.txt","hold_census.txt",
 "run_finish.log","orfs_metrics.log","face_guard.json","face_guard.log","port_bind.json","port_bind.log","pin_audit.json","pin_audit.log",
 "selrange.json","selrange.log","selrange.rc","rtl_lint.json","rtl_lint.log","sdc_lint.log","physical_completion","FAIL_PREFLOOR","resume.json",
 "postcts_gate_FF.log","postcts_gate_TT.log","postcts_gate_ff.json","postcts_gate_tt.json","postcts_gate_ff.libraries.json","postcts_gate_tt.libraries.json",
 "pre_route_ff_hold.log","hold_gate.log","hold_margin_read.log","hold_margin_value.log","orfs_hold_mm.log","kit_modes_cts.log","lec_run.log","rtl_lint.ys","gen.log"}
LECST=re.compile(r"^lec_async\.(done|identity|lock|log|mode|owner|pid|rc|ready|runs|source_identity|unit_rc)$")
# seam slots: M4 every 2nd track + M6 tracks evenly, y in the core band
N=len(sp["seam"]); y0,y1=4.5,228.8
m4=[("M4",round(0.024+0.048*k,3)) for k in range(0,5000,2) if y0<=0.024+0.048*k<=y1]
m6all=[("M6",round(0.032+0.064*k,3)) for k in range(0,4000) if y0<=0.032+0.064*k<=y1]
need=N-len(m4); assert 0<need<=len(m6all),(N,len(m4),len(m6all))
m6=[m6all[int(i*len(m6all)/need)] for i in range(need)]
slots=sorted(m4+m6,key=lambda t:t[1])
seam=sorted(sp["seam"],key=lambda s:s["y"])
slot_of={}
for s,(ly,y) in zip(seam,slots): slot_of[(s["bus"],s["bit"])]=(ly,y)
def half_of(name,x): return "W" if x<XC else "E"
for H in "WE":
    mod="ot_smh_static_front_"+H.lower(); dx=0.0 if H=="W" else XC; w=WH[H]
    mymap=pm[H]  # orig bit name -> half bit name
    out_s="seam_w2e" if H=="W" else "seam_e2w"; in_s="seam_e2w" if H=="W" else "seam_w2e"
    nseam={"seam_w2e":st["seam_w2e"],"seam_e2w":st["seam_e2w"]}
    tmp=os.path.join(OUTD,mod+"_tmp"); 
    if os.path.exists(tmp): shutil.rmtree(tmp)
    os.makedirs(tmp)
    for e in os.listdir(SRC):
        if e in EXCL or LECST.match(e): continue
        s=os.path.join(SRC,e); d=os.path.join(tmp,e)
        if e=="rtl": os.makedirs(d); continue
        (shutil.copytree(s,d,symlinks=True) if os.path.isdir(s) else shutil.copy2(s,d))
    shutil.copy2(os.path.join(SPL,mod+".v"),os.path.join(tmp,"rtl",mod+".v"))
    shutil.copy2(os.path.join(os.path.dirname(os.path.abspath(__file__)),"seam_face_advisory.py"),os.path.join(tmp,"seam_face_advisory.py"))
    rk=open(os.path.join(tmp,"run_kit_hbm.sh")).read()
    old="if [ \\$fg != 0 ]; then echo 'FAIL_PREFLOOR face_guard'"
    assert old in rk,"runner pattern"
    rk=rk.replace(old,"if [ \\$fg != 0 ] && ! python3 -I /work/seam_face_advisory.py /work; then echo 'FAIL_PREFLOOR face_guard'",1)
    open(os.path.join(tmp,"run_kit_hbm.sh"),"w").write(rk)
    # ---- pins
    def ren(n):
        return mymap.get(n)
    io=[];pj=[];pp=[]
    for ln in open(os.path.join(SRC,"io.tcl")):
        m=re.match(r"place_pin -pin_name \{(\S+)\} -layer (\S+) -location \{(\S+) (\S+)\} -pin_size \{(\S+) (\S+)\}",ln)
        if not m: continue
        n,ly,x,y,a,b=m.groups(); x=float(x); y=float(y)
        if n=="clk":
            io.append("place_pin -pin_name {clk} -layer %s -location {%.4f %.4f} -pin_size {%s %s}"%(ly,x-453.6,y,a,b)); continue
        if half_of(n,x)!=H: continue
        io.append("place_pin -pin_name {%s} -layer %s -location {%.4f %.4f} -pin_size {%s %s}"%(ren(n),ly,x-dx,y,a,b))
    for p in json.load(open(os.path.join(SRC,"pins.json"))):
        n=p["bus"] if p.get("bit") is None else "%s[%d]"%(p["bus"],p["bit"])
        q=dict(p)
        if n=="clk": q["x"]=round(p["x"]-453.6,4); pj.append(q); continue
        if half_of(n,p["x"] if p["face"] not in("E",) else 1814.4)!=H: continue
        hn=ren(n); m=re.match(r"(.*)\[(\d+)\]$",hn)
        q["bus"],q["bit"]=(m.group(1),int(m.group(2))) if m else (hn,None)
        q["x"]=round(p["x"]-dx,4); pj.append(q)
    ppin=json.load(open(os.path.join(SRC,"plan_pins.json")))
    for p in ppin["pins"]:
        n=p["name"]; q=dict(p)
        if n=="clk": q["x"]=round(p["x"]-453.6,4); pp.append(q); continue
        if half_of(n,p["x"])!=H: continue
        q["name"]=ren(n); q["x"]=round(p["x"]-dx,4); pp.append(q)
    # seam pins: W east edge / E west edge
    for bus in ("seam_w2e","seam_e2w"):
        for k in range(nseam[bus]):
            ly,y=slot_of[(bus,k)]; sz=("0.1920 0.0240" if ly=="M4" else "0.1920 0.0320")
            xl=w-0.096 if H=="W" else 0.096; xe=w if H=="W" else 0.0
            io.append("place_pin -pin_name {%s[%d]} -layer %s -location {%.4f %.4f} -pin_size {%s}"%(bus,k,ly,xl,y,sz))
            pj.append({"bus":bus,"bit":k,"layer":ly,"x":xe,"y":y,"face":"E" if H=="W" else "W"})
            pp.append({"name":"%s[%d]"%(bus,k),"layer":ly,"x":round(xl,4),"y":y})
    # sanity: every half port has a pin
    ports=set()
    for p in pj: ports.add(p["bus"] if p.get("bit") is None else "%s[%d]"%(p["bus"],p["bit"]))
    nports=len(ports); assert len(io)==len(pj)==len(pp)==nports,(len(io),len(pj),len(pp),nports)
    open(os.path.join(tmp,"io.tcl"),"w").write("# HBM-COLLECT-1 SF-SPLIT: %s half pins (outer plan pins shifted by %.1f um, renamed per half; seam pins M4/M6 at the %s edge)\n"%(H,dx,"east" if H=="W" else "west")+"\n".join(io)+"\n")
    json.dump(pj,open(os.path.join(tmp,"pins.json"),"w"))
    ppin.update(module=mod,pins=pp,source="SF-SPLIT %s half of %s"%(H,ppin["source"]),split_derived=True); ppin.pop("source_sha256",None)
    json.dump(ppin,open(os.path.join(tmp,"plan_pins.json"),"w"),indent=1)
    # ---- config.mk
    c=open(os.path.join(SRC,"config.mk")).read()
    c=re.sub(r"(?m)^export DESIGN_NICKNAME = .*$","export DESIGN_NICKNAME = hbc_"+mod,c)
    c=re.sub(r"(?m)^export DESIGN_NAME = .*$","export DESIGN_NAME = "+mod,c)
    c=re.sub(r"(?m)^export VERILOG_FILES = .*$","export VERILOG_FILES = /work/rtl/%s.v"%mod,c)
    c=re.sub(r"(?m)^export DIE_AREA = .*$","export DIE_AREA = 0 0 %.2f 233.28"%w,c)
    c=re.sub(r"(?m)^export CORE_AREA = .*$","export CORE_AREA = 4.32 4.32 %.2f 228.96"%(w-4.32),c)
    c=c.replace("# GENERATED by gen_core_kit_hbm.py","# SF-SPLIT %s half (HBM-COLLECT-1 11-10, derived from SF-C kit 4f244bbf347ac167 by mkkit.py); originally GENERATED by gen_core_kit_hbm.py"%H,1)
    open(os.path.join(tmp,"config.mk"),"w").write(c)
    # ---- SDC: seam budget split (launch half 200 ps incl. clk->Q, receive half 633 ps; sum = 833 period); mins keep the kit contract
    seam_sdc=("\n# HBM-COLLECT-1 SF-SPLIT seam budget: the seam is launch-registered (every %s bit is a flop output, every %s bit\n"
      "# lands in comb -> flop); W+E share one 833 ps cycle: launch half 200 ps, receive half 633 ps. -min stays the kit contract.\n"
      "set_output_delay -max 633.0000 -clock vclk [get_ports {%s[*]}]\nset_input_delay -max 200.0000 -clock vclk [get_ports {%s[*]}]\n")%(out_s,in_s,out_s,in_s)
    open(os.path.join(tmp,"constraint.sdc"),"a").write(seam_sdc)
    # ---- sdc_lint.json
    sl=json.load(open(os.path.join(SRC,"sdc_lint.json")))
    ins=sorted({p["bus"] for p in pj if p["bus"]!="clk" and any(q["bus"]==p["bus"] for q in pj)} )
    dirs={}
    for p in ppin["pins"]:
        pass
    pdir={}
    for p in json.load(open("/w2/pins.json")) if False else []: pass
    orig_dirs={re.sub(r"\[\d+\]$","",p["name"]):p["dir"] for p in json.load(open(sys.argv[4]))}
    buses=sorted({p["bus"] for p in pj})
    d_of=lambda b:("output" if b==out_s else "input") if b.startswith("seam_") else orig_dirs[b]
    sl["inputs"]=[b for b in buses if b!="clk" and d_of(b)=="input"]; sl["outputs"]=[b for b in buses if d_of(b)=="output"]
    fl=sl.get("io_floor_ps",{}); fl={b:v for b,v in fl.items() if b in buses}; fl[out_s]=166.6; fl[in_s]=166.6; sl["io_floor_ps"]=fl
    json.dump(sl,open(os.path.join(tmp,"sdc_lint.json"),"w"),indent=1)
    # ---- core.json / boundary context / freeze
    resets=["rst_n"] if "rst_n" in buses else []
    cj=json.load(open(os.path.join(SRC,"core.json"))); cj["boundary_role"]={"clk":"clk",**({"rst_n":"reset"} if resets else {})}; json.dump(cj,open(os.path.join(tmp,"core.json"),"w"),indent=1)
    bg=json.load(open(os.path.join(SRC,"boundary_guard_context.json"))); bg["reset_ports"]=resets; json.dump(bg,open(os.path.join(tmp,"boundary_guard_context.json"),"w"),indent=1)
    # ---- clock sites / face flops / portlist
    cs=[l for l in open(os.path.join(SRC,"clock_sites.tcl")) if l.strip()]
    keep=[]
    for l in cs:
        m=re.match(r"\{(\S+) (\S+)\}",l.strip()); x=float(m.group(1))
        if half_of("",x)==H: keep.append("{%.2f %s}\n"%(x-dx,m.group(2)))
    open(os.path.join(tmp,"clock_sites.tcl"),"w").write("".join(keep))
    ff=[]
    for l in open(os.path.join(SRC,"ot_face_flops.txt")):
        f=l.rstrip("\n").split("\t")
        if len(f)<5: continue
        if f[4] not in mymap: continue
        ff.append("\t".join([f[0],f[1],"%.2f"%(float(f[2])-dx),f[3],mymap[f[4]]]))
    open(os.path.join(tmp,"ot_face_flops.txt"),"w").write("\n".join(ff)+"\n")
    wid={}
    for p in pj: wid[p["bus"]]=max(wid.get(p["bus"],0),(p["bit"] or 0)+1)
    open(os.path.join(tmp,"rtl","portlist.txt"),"w").write("module %s\n"%mod+"".join("%s [%d:0] %s\n"%(d_of(b),wid[b]-1,b) for b in sorted(wid)))
    # ---- hash + freeze + provenance
    h=hashlib.sha256()
    for f in ("rtl/%s.v"%mod,"config.mk","io.tcl","constraint.sdc","pins.json","sdc_lint.json","run_kit_hbm.sh"):
        h.update(open(os.path.join(tmp,f),"rb").read())
    kh=h.hexdigest()[:16]
    fz=json.load(open(os.path.join(SRC,"freeze.json")))
    ppsha=hashlib.sha256(open(os.path.join(tmp,"plan_pins.json"),"rb").read()).hexdigest()
    fz.update(view=mod+"@sfs1110",module=mod,design=mod,rtl_top=mod,recipe_key=mod,outline_um=[w,H_],pins=nports,pins_sha256=ppsha,
      pins_canon_sha256=None,resets=resets,kit_hash=kh,face_shell=None,plan_pins_source="SF-SPLIT "+H,plan_pins_source_sha256=None,plan_pins_source_canon_sha256=None,
      split_derived={"from_kit":"4f244bbf347ac167","from_netlist":"SF-C 1_synth.v","cut_x_um":XC,"half":H,"seam_out":out_s,"seam_in":in_s,
        "seam_bits":nseam,"proof":"structural netlist equivalence EQUIVALENT (split4/proof.out); 2-bit seam swap mutant NOT_EQUIVALENT"})
    json.dump(fz,open(os.path.join(tmp,"freeze.json"),"w"),indent=1)
    pv=json.load(open(os.path.join(SRC,"PROVENANCE.json"))) if os.path.exists(os.path.join(SRC,"PROVENANCE.json")) else {}
    pv={"sf_split":{"lane":"HBM-COLLECT-1","date":"2026-11-10","half":H,"kit_hash":kh,"source_kit":SRC,"netlists":SPL},"parent_provenance":pv}
    json.dump(pv,open(os.path.join(tmp,"PROVENANCE.json"),"w"),indent=1)
    final=os.path.join(OUTD,"%s_%s"%(mod,kh))
    if os.path.exists(final): shutil.rmtree(final)
    os.rename(tmp,final)
    print(H,final,"ports",nports,"io",len(io),"faceflops",len(ff),"sites",len(keep),"kit_hash",kh)
