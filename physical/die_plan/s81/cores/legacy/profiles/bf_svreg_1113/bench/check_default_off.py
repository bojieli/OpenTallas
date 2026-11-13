from pathlib import Path
import re,json,hashlib,subprocess
P=Path(__file__).resolve().parent
W=P.parents[7]
meta=json.loads((P/"gold_source.json").read_text());s=(P/"gold_gf4_fullband.sv").read_text()
for n in sorted(meta["modules_prefixed"],key=len,reverse=True):
    s=re.sub(r"\bgold_"+re.escape(n)+r"\b",n,s)
assert hashlib.sha256(s.encode()).hexdigest()==meta["sha256"]
import sys
O=Path(sys.argv[1]) if len(sys.argv)>1 else Path("/tmp/gf5_default_off")
O.mkdir(exist_ok=True);old=O/"before.sv";old.write_text(s)
new=W/"rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l1f.sv"
V=Path.home()/".local/opentallas-tools/verilator-5.050/bin/verilator"
def norm(s):
    s=re.sub(r"(?m)^\s*"+chr(96)+r"line[^\n]*","",s)
    s=re.sub(r"/\*.*?\*/","",s,flags=re.S)
    s=re.sub(r"//[^\n]*","",s)
    return re.sub(r"\s+","",s)
rows=[]
for name,defs in [("gf2",[]),("gf3",["OT_GUNIT_BF_M1REG"]),("gf4",["OT_GUNIT_BF_M1REG","OT_GUNIT_BF_C1REG"])]:
    a=[]
    for p in (old,new):
        z=subprocess.run([str(V),"-E","-Wno-fatal"]+["-D"+d for d in defs]+[str(p)],capture_output=True,text=True,check=True)
        a.append(norm(z.stdout))
    assert a[0]==a[1],name
    rows.append({"form":name,"default_off_identical":True,"normalized_sha256":hashlib.sha256(a[0].encode()).hexdigest()})
(O/"result.json").write_text(json.dumps(rows,indent=1)+"\n")
print(json.dumps(rows))
print("GF5_DEFAULT_OFF PASS")
