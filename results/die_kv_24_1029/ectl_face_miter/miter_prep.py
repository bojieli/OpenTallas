import re,sys,shutil
from pathlib import Path
R=Path("/srv/opentallas-scratch2/claude/codex-kv-1028/ectl"); M=R/"miter"; mode=sys.argv[1]
O=R/"kits/qkd_ectlk_q0__216x172.8"; F=R/"fp/kits/qkd_ectlk_q0__216x172.8"
T=M/mode; shutil.rmtree(T,ignore_errors=True); (T/"o").mkdir(parents=True); (T/"n").mkdir()
files=[Path(x).name for x in re.search(r"VERILOG_FILES = (.*)",(O/"config.mk").read_text()).group(1).split()]
names=set()
for f in files: names|=set(re.findall(r"^\s*module\s+(\w+)",(O/"rtl"/f).read_text(),re.M))
pat=re.compile(r"\b("+"|".join(sorted(names,key=len,reverse=True))+r")\b")
for f in files:
    t=(O/"rtl"/f).read_text()
    (T/"o"/f).write_text(pat.sub(lambda m:m.group(1)+"_o",t))
for p in (O/"rtl").iterdir():
    if p.suffix in (".svh",".vh"): shutil.copy(p,T/"o"/p.name); shutil.copy(p,T/"n"/p.name)
for f in files: shutil.copy(F/"rtl"/f,T/"n"/f)
if mode=="mut":
    sys.path.insert(0,"/srv/opentallas-scratch2/claude/wt/codex-kv-ectl-1028/physical/die_plan/qwen_kvsys/cores/harden")
    import ectlk_face_ports as E
    for f in ["ot_qkd_ectl_parts.sv","qkd_static_k_issuer.sv","qkd_static_ectl_st.sv"]: shutil.copy(O/"rtl"/f,T/"n"/f)
    E.apply_kit(T/"n",True)
(T/"files.f").write_text("\n".join([f"o/{f}" for f in files if not f.endswith("_bb.v")]+[f"n/{f}" for f in files if not f.endswith("_bb.v")])+"\n")
print(len(files),"files;",[f for f in files if f.endswith(".v")])
