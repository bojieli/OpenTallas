import json,sys,shutil,os
sys.path.insert(0,sys.argv[1]); import kit_contract as K
spec=json.load(open(sys.argv[2])); kits=sys.argv[3]; out=sys.argv[4]; plan=sys.argv[5]
for kd0 in sys.argv[6:]:
    name=os.path.basename(kd0); top=[c for c in spec if name.startswith(c+"_")][0]
    kd=os.path.join(out,name)
    if os.path.exists(kd): shutil.rmtree(kd)
    shutil.copytree(os.path.join(kits,kd0),kd,symlinks=True)
    lines=["foreach {inst master x y orient} {"]
    for m in spec[top]["macros"]:
        inst=m["name"].replace("[","\\[").replace("]","\\]")
        lines.append(f"  {{{inst}}} {m['master']} {m['origin_um'][0]} {m['origin_um'][1]} {m['orient']}")
    lines.append("} { place_macro -macro_name $inst -location [list $x $y] -orientation $orient }")
    open(os.path.join(kd,"macro_placement.tcl"),"w").write("\n".join(lines)+"\n")
    cfg=open(os.path.join(kd,"config.mk")).read()+"\nexport MACRO_PLACEMENT_TCL = /work/macro_placement.tcl\n"
    open(os.path.join(kd,"config.mk"),"w").write(cfg)
    for fn in ("macro_channels","clock_entry_clear","macro_pin_grid"):
        e,i=getattr(K,fn)(kd,plan); print(top,fn,"FAIL" if e else "PASS",e[:3],{k:v for k,v in i.items() if k!="min_channel_note"})
    e,i=K.island_macro_clear(kd); print(top,"island_macro_clear","FAIL" if e else "PASS",e[:2],i)
