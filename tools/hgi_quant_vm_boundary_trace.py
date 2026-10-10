#!/usr/bin/env python3
import importlib.util,inspect,json,pathlib,sys
s=importlib.util.spec_from_file_location('rb','tools/closure_loop/rtl_boundary.py');rb=importlib.util.module_from_spec(s);s.loader.exec_module(rb)
source=inspect.getsource(rb.analyse)
needle='    return {"in_to_out_bits"'
extra='''    b=in2reg[1]; trail=[]
    while b is not None:
        trail.append(dict(bit=b,depth=depth(b)[0]))
        if b in in_bits or b not in drivers:break
        choices=drivers[b][0]
        b=max(choices,key=lambda x:depth(x)[0]) if choices else None
    wanted={x["bit"] for x in trail}
    labels={b:[] for b in wanted}
    for name,n in mod.get("netnames",{}).items():
        for index,b in enumerate(n["bits"]):
            if b in labels:labels[b].append(name+"["+str(index)+"]")
    for row in trail:row["nets"]=labels[row["bit"]][:6]
    return {"worst_input_path":trail,"worst_input_port":in_bits.get(b),"in_to_out_bits"'''
source=source.replace(needle,extra);exec(source,rb.__dict__)
data=json.loads(pathlib.Path(sys.argv[1]).read_text());result=rb.analyse(data,'ot_hgi_quant_vm_transport');print(json.dumps(result,indent=2))
