#!/usr/bin/env python3
"""Audit local parent FFs plus exact ports of the already-qualified ingress macro."""
import argparse,json,re,shutil,subprocess,tempfile
from pathlib import Path
from check_embedding_metadata_cells import storage


def bits(m,name):
    nets=m['netnames']
    if name in nets:return nets[name]['bits']
    rows=sorted((int(x.group(1)),n['bits']) for k,n in nets.items() if (x:=re.fullmatch(re.escape(name)+r'\[(\d+)\]',k)))
    if not rows or [i for i,_ in rows]!=list(range(len(rows))) or any(len(b)!=1 for _,b in rows):raise ValueError('missing vector '+name)
    return [b[0] for _,b in rows]


def check(m,kind):
    width=12 if kind=='code' else 18;prefix='ia' if kind=='code' else 'row';macro='qfd_embed_ingress_'+kind
    cells=[(name,c) for name,c in m['cells'].items() if c['type']==macro]
    if len(cells)!=1 or cells[0][0]!='u_ingress':raise ValueError('exactly one real u_ingress hard macro required')
    if any('embedding_ingress_' in c['type'] for c in m['cells'].values()):raise ValueError('flattenable ingress implementation forbidden')
    conn=cells[0][1]['connections'];expected={'address_q':prefix+'_q','address_n':prefix+'_n','valid_q':'iv_q','valid_n':'iv_n','credit_q':'cr_q','credit_n':'cr_n'}
    for pin,net in expected.items():
        actual=bits(m,net)
        if conn.get(pin)!=actual or len(actual)!=(width if pin.startswith('address') else 1):raise ValueError('wrong macro binding '+pin)
    for pin,port in {'clk':'clk','rst_n':'rst_n','address':'i_addr' if kind=='code' else 'i_row','valid':'i_v','credit':'o_cr'}.items():
        if conn.get(pin)!=m['ports'][port]['bits']:
            raise ValueError('wrong macro input binding '+pin)
    pairs=[('fault','fault_n',1),('wp','wp_n',2),('rp','rp_n',2),('credits','credits_n',4),('phase','phase_n',1),('valid_pipe','valid_n',4),('addr_q','addr_n',12),('ce_q','ce_n',1)]
    pairs += [(f'fifo[{i}]',f'fifo_n[{i}]',width) for i in range(2)]
    if kind=='scale':pairs += [(f'lane_pipe[{i}]',f'lane_n[{i}]',4) for i in range(4)]
    counts={}
    for a,b,w in pairs:
        left,right=storage(m,a),storage(m,b)
        if len(left)!=w or len(right)!=w or left&right:raise ValueError('local storage not independent/full width: '+a)
        counts[a+'/'+b]=[len(left),len(right)]
    for name,w in [('capture_data' if kind=='code' else 'capture',512 if kind=='code' else 256),('capture_en_q',16 if kind=='code' else 8)]:
        cells=storage(m,name)
        if len(cells)!=w:raise ValueError('capture width: '+name)
        counts[name]=len(cells)
    return dict(verdict='PASS',hard_macro=macro,local_storage=counts,component_qualification_required=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--kind',choices=['code','scale'],required=True);p.add_argument('--netlist',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    y=Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys';y=str(y) if y.exists() else shutil.which('yosys')
    with tempfile.TemporaryDirectory(prefix='embedding-parent-storage-') as d:
        dest=Path(d)/'mapped.json';subprocess.run([y,'-Q','-T','-p',f'read_verilog "{a.netlist.resolve()}"; write_json "{dest}"'],check=True,stdout=subprocess.DEVNULL)
        m=json.loads(dest.read_text())['modules'][f'ot_qwen_embed_{a.kind}_bank_parent'];result=check(m,a.kind)
    a.out.write_text(json.dumps(result,indent=2)+'\n');print('PASS qualified-macro binding and local parent storage')
if __name__=='__main__':main()
