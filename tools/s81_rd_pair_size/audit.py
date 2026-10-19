"""Mapped source census, including inherited blockers; grants no SAFE waiver."""
import collections
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

root=Path.cwd()
spec=importlib.util.spec_from_file_location('abi',root/'tools/run_abi3_physical.py')
abi=importlib.util.module_from_spec(spec);spec.loader.exec_module(abi)
results=[]
for netlist in sorted(Path('price').glob('*/mapped.v')):
    top='ot_s81sl_xr1' if 'xr1' in netlist.parent.name else 'ot_s81sl_rstop'
    out=netlist.parent/'mapped.json'
    libs=abi.VIEWS['asap7']['corners']['TT']['liberty']
    script='; '.join([f'read_liberty -lib {p}' for p in libs]+[f'read_verilog {netlist}',f'hierarchy -top {top}',f'write_json {out}'])
    with (netlist.parent/'census_yosys.log').open('w') as log:
        subprocess.run([str(abi.YOSYS),'-p',script],stdout=log,stderr=subprocess.STDOUT,check=True)
    mod=json.loads(out.read_text())['modules'][top]
    loads=collections.Counter();drivers={};unknown=[]
    for name,cell in mod['cells'].items():
        for port,bits in cell['connections'].items():
            direction=cell.get('port_directions',{}).get(port)
            if direction not in ('input','output'):unknown.append((name,port))
            for bit in set(bits):
                if isinstance(bit,int):
                    if direction=='input':loads[bit]+=1
                    elif direction=='output':drivers[bit]=(name,cell['type'],port)
    aliases=collections.defaultdict(list)
    for name,net in mod['netnames'].items():
        for index,bit in enumerate(net['bits']):
            if isinstance(bit,int):aliases[bit].append(name+(f'[{index}]' if len(net['bits'])>1 else ''))
    sequential=[];all_bad=[]
    for bit,(name,typ,port) in drivers.items():
        if loads[bit]>32:
            row=dict(net=bit,cell=name,type=typ,port=port,loads=loads[bit],aliases=aliases.get(bit,[]))
            all_bad.append(row)
            if typ.startswith(('DFF','SDF')):sequential.append(row)
    ports={p:sum(loads.get(b,0) for b in v['bits'] if isinstance(b,int)) for p,v in mod['ports'].items() if v['direction']=='input'}
    result=dict(name=netlist.parent.name,top=top,unknown_port_directions=unknown,
                max_mapped_driver_loads=max(loads.get(b,0) for b in drivers),
                output_drivers_over32=sorted(all_bad,key=lambda x:-x['loads']),
                sequential_outputs_over32=sorted(sequential,key=lambda x:-x['loads']),
                raw_input_loads=ports,admitted=False)
    (netlist.parent/'fanout.json').write_text(json.dumps(result,indent=1)+'\n')
    results.append(dict(name=result['name'],max_loads=result['max_mapped_driver_loads'],
                        over32=len(all_bad),q_over32=len(sequential),raw_reset_loads=ports.get('rst_n')))
Path('price/census_summary.json').write_text(json.dumps(results,indent=1)+'\n')
print(json.dumps(results))
