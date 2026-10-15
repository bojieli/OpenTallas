#!/usr/bin/env python3
"""Add six local clock pins to the exact retained calendar IO scene."""
import argparse,copy,hashlib,json,re,statistics,sys
from pathlib import Path
import v19_pins_1014 as V
ROOT=Path(__file__).resolve().parents[2]


def main():
    ap=argparse.ArgumentParser()
    for key in ['old-pins','census','rtl','rom-lef','out']:ap.add_argument('--'+key,type=Path,required=True)
    a=ap.parse_args();old=json.loads(a.old_pins.read_text());census=json.loads(a.census.read_text())
    assert hashlib.sha256(a.rtl.read_bytes()).hexdigest()==census['source_sha256'],'stale source census'
    assert old['outline_um']==[237.6,291.6]
    assert len(old['pins'])==568
    sys.path.insert(0,str(ROOT/'tools'));from die_port_bind import parse_modules
    modules={m.name:m for m in parse_modules(a.rtl.read_text(),str(a.rtl))};module=modules['s81_static_calendar_controller7'];env=module.env({'CYCLES':4096})
    ports={};coordinates={}
    for row in old['pins']:
        match=re.fullmatch(r'(.+?)(?:\[(\d+)\])?',row['pin']);name=match[1];bit=int(match[2] or 0)
        coordinate=row['x_um'] if row['face'] in 'NS' else row['y_um']
        coordinates.setdefault(name,{})[bit]=[row['face'],row['layer'],coordinate,.192]
    for name,bits in coordinates.items():
        assert set(bits)==set(range(len(bits))),name
        ports[name]=[bits[i] for i in range(len(bits))]
    old_ports=copy.deepcopy(ports)
    assert set(module.ports)==set(ports)|{'clk_rom','clk_outputs'}
    for name,bits in ports.items():assert module.width(name,env)==len(bits),(name,len(bits))
    assert module.width('clk_rom',env)==module.width('clk_outputs',env)==3
    clk_port=re.search(r'PIN clk\s+(.*?)END clk',a.rom_lef.read_text(),re.S)[1]
    rect=list(map(float,re.search(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',clk_port).groups()))
    assert 'LAYER M4' in clk_port
    macro_clk_y=(rect[1]+rect[3])/2
    phase=round(ports['clk'][0][2]%.096,6)
    def free(face,preferred):
        occupied=[v[2] for bs in ports.values() for v in bs if v[:2]==[face,'M4']]
        candidates=[round(phase+.096*i,3) for i in range(1,3036)]
        legal=[v for v in candidates if .2<v<291.4 and all(abs(v-x)>=.0955 for x in occupied)]
        assert legal
        return min(legal,key=lambda v:(abs(v-preferred),v))
    ports['clk_rom']=[];ports['clk_outputs']=[];placements=[]
    for bank in range(3):
        preferred=25.92+86.4*bank+macro_clk_y
        v=free('W',preferred);ports['clk_rom'].append(['W','M4',v,.192])
        placements.append(dict(pin='clk_rom[%d]'%bank,face='W',y_um=v,reason='nearest free track to actual ROM%d clock y %.3f'%(bank,preferred)))
    for group in census['output_groups']:
        pins=[p for p in old['pins'] if re.sub(r'\[\d+\]$','',p['pin']) in group['ports']]
        assert len(pins)==group['bits']
        preferred=statistics.median(p['y_um'] for p in pins)
        v=free('E',preferred);ports['clk_outputs'].append(['E','M4',v,.192])
        placements.append(dict(pin=group['clock'],face='E',y_um=v,reason='nearest free track to actual owned output-pin median %.3f'%preferred))
    a.out.mkdir(parents=True,exist_ok=True)
    master='s81_static_calendar_controller7'
    f=V.write(a.out,master,old['outline_um'],ports,'clk','Exact retained 568 signal pins; only six added related clock pins, ROM clocks on W and registered-output clocks on E.','calendar7_candidate',dict(clock_entries={'stream':['clk','clk_rom[0]','clk_rom[1]','clk_rom[2]','clk_outputs[0]','clk_outputs[1]','clk_outputs[2]']},params={'CYCLES':4096},source='tools/s81/calendar7_assigned_pins.py',qualification='CANDIDATE top-down IO assignment; exact/mutant proof and actual independent-root native CTS/STA required',clock_delivery='Each clock phase0 related PLL1:1 delivered at phi-wire-R_i; no inherited insertion defaults',added_clocks=placements,input_sha256={key:hashlib.sha256(getattr(a,key).read_bytes()).hexdigest() for key in ['old_pins','census','rtl','rom_lef']}))
    new=json.loads(f.read_text());assert all(new['ports'][p]['per_bit']==v for p,v in old_ports.items()),'existing pin moved'
    assert new['nudged_to_pitch']==0,'existing pitch changed'
    (a.out/'assignment_receipt.json').write_text(json.dumps(dict(original_odb_sha256=old['source_odb_sha256'],preserved_original_signal_pins=568,added_clock_pins=6,source_abi='PASS',existing_pin_coordinates='BYTE_EQUIVALENT',pitch_and_bounds='PASS',placements=placements),indent=1)+'\n')
    print(json.dumps(dict(master=master,preserved=568,added=6,placements=placements)))
if __name__=='__main__':main()
