#!/usr/bin/env python3
"""Move the residual collective controller into one explicit hard-leaf module.

Input is a source-pinned Yosys hierarchy with all real datapath/memory leaves
preserved. This changes hierarchy and wires only: every cell, parameter and bit
connection is retained. Generated controller RTL must still pass equivalence,
real functional composition, pin/clock/physical gates before use.
"""
import argparse
import copy
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


def directions(cell):
    ds=cell.get("port_directions",{})
    assert set(cell["connections"])==set(ds),"missing cell port directions"
    assert set(ds.values())<={"input","output"},"inout requires an explicit ownership rule"
    return ds


def bits_by_direction(cells):
    result={"input":set(),"output":set()}
    for cell in cells.values():
        for p,d in directions(cell).items():
            result[d].update(b for b in cell["connections"][p] if isinstance(b,int))
    return result


def extract(design,top):
    result=copy.deepcopy(design);modules=result["modules"];parent=modules[top]
    # Reset leaf FFs belong to the same small controller clock tree. There must
    # be no separate soft reset islands left in the wires-only parent.
    names={n for n,c in parent["cells"].items() if c["type"] not in modules or c["type"]=="ot_coll_rst_leaf"}
    assert names,"no residual controller found"
    owned={n:parent["cells"][n] for n in sorted(names)}
    rest={n:c for n,c in parent["cells"].items() if n not in names}
    inside=bits_by_direction(owned);outside=bits_by_direction(rest)
    for p in parent["ports"].values():
        assert p["direction"] in ("input","output")
        # External output pins consume an internal driver; external input pins
        # supply one. This reversal is only for computing the boundary.
        d="input" if p["direction"]=="output" else "output"
        outside[d].update(b for b in p["bits"] if isinstance(b,int))
    boundary={"input":inside["input"]-inside["output"],
              "output":inside["output"] & outside["input"]}
    assert not boundary["input"] & boundary["output"],"ambiguous bidirectional boundary"
    assert boundary["input"] <= outside["output"],"controller input without an external source"

    ports={};port_manifest={};remaining={d:set(bs) for d,bs in boundary.items()}
    candidates=[]
    for n,p in parent["ports"].items():candidates.append((0,n,p["bits"]))
    for n,p in parent["netnames"].items():candidates.append((1+int(p.get("hide_name",0)),n,p["bits"]))
    candidates.sort(key=lambda x:(x[0],len(x[1]),x[1]))
    used_names=set()
    for primary,name,bs in candidates:
        for d in ("input","output"):
            indices=[i for i,b in enumerate(bs) if isinstance(b,int) and b in remaining[d]]
            groups=[]
            for i in indices:
                if groups and i==groups[-1][-1]+1:groups[-1].append(i)
                else:groups.append([i])
            for group in groups:
                values=[bs[i] for i in group]
                # A duplicate alias can only claim a boundary bit once.
                if len(set(values))!=len(values):continue
                base=re.sub(r"[^A-Za-z0-9_$]","_",name.lstrip("\\"))
                pname=base if primary==0 and len(group)==len(bs) else f"p_{d}_{base}_{group[0]}_{group[-1]}"
                stem=pname;k=0
                while pname in used_names:k+=1;pname=f"{stem}_{k}"
                used_names.add(pname);ports[pname]={"direction":d,"bits":values}
                port_manifest[pname]={"direction":d,"width":len(values),"source_net":name,
                                       "source_indices":group,"yosys_bits":values}
                remaining[d].difference_update(values)
    for d,bs in remaining.items():
        assert not bs,f"unmapped {d} boundary bits: {sorted(bs)[:20]}"
    ctl="ot_coll_local_controller"
    assert ctl not in modules,"controller module already exists"
    netnames=copy.deepcopy(parent["netnames"])
    for p,v in ports.items():netnames[p]={"hide_name":0,"bits":v["bits"],"attributes":{}}
    modules[ctl]={"attributes":{"keep_hierarchy":"00000000000000000000000000000001"},
                  "ports":ports,"cells":owned,"netnames":netnames}
    parent["cells"]=dict(rest)
    parent["cells"]["u_controller"]={"hide_name":0,"type":ctl,"parameters":{},
        "attributes":{"keep_hierarchy":"00000000000000000000000000000001"},
        "port_directions":{p:v["direction"] for p,v in ports.items()},
        "connections":{p:v["bits"] for p,v in ports.items()}}
    assert all(c["type"] in modules for c in parent["cells"].values()),"primitive logic remains in parent"
    assert len(rest)+len(owned)==len(design["modules"][top]["cells"]),"cell lost or duplicated"
    for n,c in owned.items():assert c==design["modules"][top]["cells"][n],"controller cell changed"
    for n,c in rest.items():assert c==design["modules"][top]["cells"][n],"datapath cell changed"
    ff_bits=sum(len(c["connections"].get("Q",[])) for c in owned.values() if "dff" in c["type"].lower())
    manifest={"schema":"opentallas.qwen.controller_hierarchy_extraction.v1","top":top,
        "controller_module":ctl,"scope":"Exact hierarchy-only source candidate, no physical/native qualification",
        "controller_primitive_ff_bits":ff_bits,"controller_reset_leaf_instances":sum(c["type"]=="ot_coll_rst_leaf" for c in owned.values()),
        "controller_cell_types":dict(Counter(c["type"] for c in owned.values())),
        "parent_hierarchical_instances":len(parent["cells"]),"parent_primitive_cells":0,
        "port_bits":{d:sum(len(v["bits"]) for v in ports.values() if v["direction"]==d) for d in boundary},
        "ports":port_manifest,"preserved_cells":sorted(names),
        "obligations":["Formal equivalence after flattening both hierarchies, same actual child definitions",
            "Functional proof uses real SRAM compiler models and actual FP fold RTL, never blackbox outputs",
            "Controller actual pin/clock/margin gate and all incident physical cut/reach checks before routing",
            "Every hard child has source-current RTL/ports/views; no placeholder physical inheritance"]}
    return result,manifest


def main():
    p=argparse.ArgumentParser();p.add_argument("--input",type=Path,required=True)
    p.add_argument("--top",default="qfd_io_collective_local_roots")
    p.add_argument("--output",type=Path,required=True);p.add_argument("--manifest",type=Path,required=True)
    a=p.parse_args();raw=a.input.read_bytes();out,m=extract(json.loads(raw),a.top)
    m["input_sha256"]=hashlib.sha256(raw).hexdigest();encoded=(json.dumps(out,indent=2)+"\n").encode()
    m["output_sha256"]=hashlib.sha256(encoded).hexdigest()
    a.output.write_bytes(encoded);a.manifest.write_text(json.dumps(m,indent=2)+"\n")
    print(json.dumps({k:m[k] for k in ("controller_primitive_ff_bits","controller_reset_leaf_instances","parent_primitive_cells","port_bits")}))


if __name__=="__main__":main()
