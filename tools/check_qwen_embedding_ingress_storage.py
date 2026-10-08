#!/usr/bin/env python3
"""Require all independent ingress capture FFs in a mapped physical netlist."""
import argparse,json,subprocess,tempfile,shutil
from pathlib import Path
from check_embedding_metadata_cells import storage


def check(module,width):
    seen=set();counts={}
    for name,w in [('address_q',width),('address_n',width),('valid_q',1),('valid_n',1),('credit_q',1),('credit_n',1)]:
        cells=storage(module,name)
        assert len(cells)==w,(name,'wrong width',len(cells),w)
        assert not cells&seen,(name,'shared state',sorted(cells&seen))
        seen|=cells;counts[name]=len(cells)
    return counts


def main():
    p=argparse.ArgumentParser();p.add_argument('--netlist',required=True);p.add_argument('--width',type=int,choices=[12,18],required=True);p.add_argument('--out',required=True);a=p.parse_args()
    y=Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys';y=str(y) if y.exists() else shutil.which('yosys')
    with tempfile.TemporaryDirectory(prefix='qwen-ingress-storage-') as d:
        dest=Path(d)/'mapped.json'
        subprocess.run([y,'-Q','-T','-p',f'read_verilog "{Path(a.netlist).resolve()}"; write_json "{dest}"'],check=True,stdout=subprocess.DEVNULL)
        m=json.loads(dest.read_text())['modules']['ot_qwen_embedding_ingress_island']
        counts=check(m,a.width)
    Path(a.out).write_text(json.dumps(dict(verdict='PASS',counts=counts,width=a.width),indent=2)+'\n')
    print('PASS ingress mapped storage independent FFs='+str(sum(counts.values())))
if __name__=='__main__':main()
