#!/bin/bash
# KV-KVSCTL-3 10-27: hub_C parent bind check with the landed qkd_kvs_ctl cut (repo root; ORFS image)
#   yosys elaborates kv3_hub_C_part_bound (kit_rtl.f) with hierarchy -check (every instantiated port exists, every module
#   defined), then checks the u_kvs_ctl cell: each port connected, widths = core ports, no undriven core input bit.
set -e
D=results/kv_cores_r2/kvsctl3/kit_rtl/kv3_hub_C; O=$1; mkdir -p $O
Y=${YOSYS:-/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys}
F=$(grep -v "^$" $D/kit_rtl.f | tr "\n" " ")
INC=$(for f in $F; do echo -n "-I$(dirname $f) "; done)
cat > $O/bind.ys <<YS
read_verilog -defer -sv -DSYNTHESIS $INC $F
hierarchy -check -top kv3_hub_C_part_bound
select -module kv3_hub_C_part_bound
write_json -selected $O/hub_C_top.json
YS
set +e; $Y -q -l $O/bind.log $O/bind.ys >/dev/null 2>&1; echo "hierarchy rc=$?" > $O/rc.txt; set -e
python3 - $O/hub_C_top.json results/kv_cores_r2/kvsctl3/rtl/qkd_kvs_ctl.sv $O/bind_check.json <<'PY'
import json,re,sys
J=json.load(open(sys.argv[1])); M=J["modules"]["kv3_hub_C_part_bound"]
c=M["cells"]["u_kvs_ctl"]; core=open(sys.argv[2]).read()
cm=re.search(r"module qkd_kvs_ctl \((.*?)\);",core,re.S).group(1)
cp={n:(d,int(w)+1 if w else 1) for d,w,n in re.findall(r"(input|output)\s+wire\s+(?:\[(\d+):0\]\s+)?(\w+)",cm)}
drv=set()
for cn,cc in M["cells"].items():
    for p,b in cc["connections"].items():
        if cc.get("port_directions",{}).get(p)=="output": drv|=set(x for x in b if isinstance(x,int))
for pn,pp in M["ports"].items():
    if pp["direction"]=="input": drv|=set(x for x in pp["bits"] if isinstance(x,int))
err=[]; nin=0
for n,(d,w) in cp.items():
    b=c["connections"].get(n)
    if b is None: err.append("unconnected "+n); continue
    if len(b)!=w: err.append(f"{n} width {len(b)}!={w}")
    if d=="input":
        for i,x in enumerate(b):
            nin+=1
            if isinstance(x,str): err.append(f"{n}[{i}] const {x}")
            elif x not in drv: err.append(f"{n}[{i}] undriven")
for n in c["connections"]:
    if n not in cp: err.append("extra "+n)
r={"cell":"u_kvs_ctl","type":c["type"],"core_ports":len(cp),"input_bits":nin,"errors":err[:50],"n_errors":len(err),"verdict":"PASS" if not err else "FAIL"}
json.dump(r,open(sys.argv[3],"w"),indent=1); print(r["verdict"],r["core_ports"],nin,len(err),err[:5])
PY
cat $O/rc.txt; grep -i "error" $O/bind.log | head -5 || true
