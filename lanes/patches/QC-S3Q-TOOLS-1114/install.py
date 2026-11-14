# usage: python3 -I install.py <src>/tools/die_plan   (QC S3Q tool bundle: TL-QCPHYSD phy/full-area/pg_free either-end + local_reset_pins + CORE-LAT/R-CLOCK-7 schema keys)
# whole files: bind.py check.py face_guard.py schema.py (+3 tests) from tree2 sha-equal base (bind 371b69605122, check 5cdb5b073cfa, face_guard 99e438c81bbd, schema 06919364ac43); gen_phys.py: PATCH (applies on 09c5d4b38994 with offsets).
import sys,os,shutil,hashlib,subprocess
H=os.path.dirname(os.path.abspath(__file__)); d=sys.argv[1]
base=dict(zip(["bind.py","check.py","face_guard.py","schema.py"],["371b69605122","5cdb5b073cfa","99e438c81bbd","06919364ac43"]))
new=dict(zip(["bind.py","check.py","face_guard.py","schema.py"],["b5b9a2293f15","01bf91665cf0","8373d5d5d1a3","db39c9474912"]))
sh=lambda p:hashlib.sha256(open(p,"rb").read()).hexdigest()[:12]
for f in base:
    cur=sh(d+"/"+f)
    if cur==new[f]: print("ALREADY",f); continue
    if cur!=base[f]: print("REFUSE",f,"sha",cur,"is neither base nor new"); sys.exit(2)
for f in base:
    p=d+"/"+f
    if sh(p)==new[f]: continue
    if not os.path.exists(p+".bak-qcs3q-1114"): shutil.copy2(p,p+".bak-qcs3q-1114")
    shutil.copyfile(H+"/"+f,p+".new"); shutil.copystat(p,p+".new"); os.replace(p+".new",p); print("COPIED",f,sh(p))
for f in ["test_full_area_hard_ip.py","test_pg_free_either_end.py","test_pg_free_full_area.py"]: shutil.copyfile(H+"/"+f,d+"/"+f)
g=d+"/gen_phys.py"; s=open(g).read()
if "full_area_hard_ip" in s: print("ALREADY gen_phys")
else:
    if not os.path.exists(g+".bak-qcs3q-1114"): shutil.copy2(g,g+".bak-qcs3q-1114")
    root=os.path.dirname(os.path.dirname(d))
    r=subprocess.run(["patch","-p1","-d",root,"-i",H+"/QC-PHY-gen_phys-1114.patch"],capture_output=True,text=True); print(r.stdout.strip()[-300:],r.stderr.strip()[-200:])
    if r.returncode: sys.exit(3)
    compile(open(g).read(),g,"exec"); print("PATCHED gen_phys",sh(g))
for f in ["bind.py","check.py","face_guard.py","schema.py","gen_phys.py"]: compile(open(d+"/"+f).read(),f,"exec")
print("DONE compile ok")
