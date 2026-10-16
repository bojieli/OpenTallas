#!/usr/bin/env python3
"""Generic Yosys proc/opt evidence only; not native or mapped physical qualification."""
import json
from pathlib import Path
root=Path(__file__).resolve().parent
result={}
for kind in ("golden", "candidate"):
    module=json.loads((root/(kind+"_proc.json")).read_text())["modules"][kind+"_skid"]
    reachable=set(module["ports"]["rst_n"]["bits"])
    cells=module["cells"]
    for _ in range(len(cells)):
        before=len(reachable)
        for cell in cells.values():
            if "ff" in cell["type"] or "latch" in cell["type"]: continue
            if any(set(bits)&reachable for port,bits in cell["connections"].items() if cell["port_directions"].get(port)=="input"):
                for port,bits in cell["connections"].items():
                    if cell["port_directions"].get(port)=="output": reachable.update(bits)
        if len(reachable)==before: break
    registers=[]
    for name,cell in cells.items():
        if "ff" not in cell["type"]: continue
        dependent=[port for port,bits in cell["connections"].items() if set(bits)&reachable and cell["port_directions"].get(port)=="input"]
        registers.append(dict(name=name,type=cell["type"],width=len(cell["connections"]["Q"]),reset_dependent_ports=dependent))
    result[kind]=dict(generic_cells=len(cells),registers=registers,reset_qualified_payload_bits=sum(r["width"] for r in registers if r["width"]>1 and "EN" in r["reset_dependent_ports"]))
print(json.dumps(result,indent=2))
