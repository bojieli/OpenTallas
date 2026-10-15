#!/usr/bin/env python3
"""Preserve actual CTfx closed-view pins for the explicit reset successor."""
import argparse,hashlib,json,sys
from pathlib import Path
import v19_pins_1014 as V
ROOT=Path(__file__).resolve().parents[2]


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--rtl',type=Path,required=True);ap.add_argument('--out',type=Path,default=ROOT/'physical/s81_die_pins/v22_ctfx_reset_native');a=ap.parse_args()
    rel='physical/ref_tile/s81hc_ctfx_ref/views/ot_s81_hc_ctfx/ot_s81_hc_ctfx.lef';outline,pins=V.lef_bits(rel);w,h=outline
    assert outline==(576.72,12.96)
    sys.path.insert(0,str(ROOT/'tools'));from die_port_bind import parse_modules
    master='ot_s81_hc_ctfx_reset_native';modules={m.name:m for m in parse_modules(a.rtl.read_text(),str(a.rtl))};m=modules[master];env=m.env({'S_RD':2})
    assert {p:m.width(p,env) for p in m.ports}=={p:len(bits) for p,bits in pins.items()}
    ports={};original={}
    for p,bits in pins.items():
        assert set(bits)==set(range(len(bits)))
        ports[p]=[];original[p]=[]
        for i in range(len(bits)):
            f,l,x,y=bits[i];assert abs({'W':x,'E':w-x,'S':y,'N':h-y}[f]-.042)<1e-5,(p,i,f,x,y)
            ports[p].append([f,l,round(x if f in 'NS' else y,3),.192]);original[p].append([x,y])
    before=json.loads(json.dumps(ports));a.out.mkdir(parents=True,exist_ok=True)
    path=V.write(a.out,master,list(outline),ports,'clk','Exact current CTfx native LEF signal pin coordinates; reset synchronizer successor only.','v22_ctfx_reset_native',dict(clock_entries={'serial':['clk']},params={'S_RD':2},source='tools/s81/ctfx_reset_assigned_pins.py',source_sha256=hashlib.sha256(a.rtl.read_bytes()).hexdigest(),original_lef=dict(path=rel,sha256=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()),qualification='Bounded die-window candidate; old CTfx RESET capture fails, successor native CTS/STA required; no die alias adoption',cost={'token_data_edges':0,'initialization_edges':2},original_xy_um=original))
    after=json.loads(path.read_text());assert after['nudged_to_pitch']==0
    assert all(after['ports'][p]['per_bit']==v for p,v in before.items())
    print('CTFX_RESET_PIN_ABI_PASS',sum(map(len,ports.values())),'exact original pin coordinates')
if __name__=='__main__':main()
