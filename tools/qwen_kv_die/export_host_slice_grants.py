#!/usr/bin/env python3
"""Export exact source-sized HOST slice grants and physical-root contracts.

The two views share RTL but differ in chain pin faces.  No Liberty or route is
inherited between them.  The existing die homes retain their dimensions.
"""
import argparse
import hashlib
import json
from pathlib import Path
import kv_die as K
from die_port_bind_kv import header, evalw

def export(out):
    binding = K.slice_die_binding()
    source = (K.ROOT / binding['file']).read_text()
    params, ports = header(source, binding['module'])
    out.mkdir(parents=True, exist_ok=True)
    records = {}
    for name in ('qkd_hslice', 'qkd_hslice_dn'):
        mm = K.F.Master(name, K.SLICE_W-K.SHAVE, K.SLICE_H-K.SHAVE, 5, 'v1.4.2 HOST slice pin grant')
        for port in binding['ports']:
            mm.face(port, evalw(ports[port][1], params), 'W', 'M4', 100)
        K._slice_pins({}, mm, down=name.endswith('_dn'))
        pins = []
        lines = ['# Exact die-assigned v1.4.2 pins; keep separate physical view per orientation.']
        for pin, layer, rect in K.F.pin_rects(mm, 1, {}):
            base = pin.split('[')[0]
            if evalw(ports[base][1], params) == 1:
                pin = base
            x0,y0,x1,y1 = rect
            assert min(x0,y0)>=-1e-8 and x1<=mm.w+1e-8 and y1<=mm.h+1e-8, (pin,rect)
            face = mm.ports[base][2]
            pins.append(dict(pin=pin,layer=layer,face=face,rect_um=list(rect)))
            lines.append(f'place_pin -pin_name {{{pin}}} -layer {layer} -location {{{(x0+x1)/2:.6f} {(y0+y1)/2:.6f}}} -pin_size {{{x1-x0:.6f} {y1-y0:.6f}}}')
        # Exact rectangles must not overlap on the same face/layer.
        for face in 'WENS':
            for layer in ('M4','M5'):
                selected = [p for p in pins if p['face']==face and p['layer']==layer]
                axis = 1 if face in 'WE' else 0
                selected.sort(key=lambda p:p['rect_um'][axis])
                for a,b in zip(selected,selected[1:]):
                    assert a['rect_um'][axis+2] < b['rect_um'][axis]-1e-6, (a,b)
        old = json.loads((K.ROOT/'results/arch/qwen_split_1014/kvsys_v1_4_1/pins'/f'{name}.json').read_text())
        clocks = {c:dict(family='CORE833.334',period_ps=833.334,die_trunks=['clk_core_'+s for s in K.STACKS],
                     separate_physical_root=True,phase_rule='phi - actual routed boundary R for this root')
                  for c in ('ck_station','ck_static','ck_boot','ck_boot_test')}
        rec = dict(schema='opentallas.qwen_host_slice_grant.v1',master=name,rtl=binding['module'],rtl_file=binding['file'],
                   rtl_sha256=hashlib.sha256(source.encode()).hexdigest(),outline_um=[mm.w,mm.h],
                   instances=old['instances'],pins=pins,clock_domains=clocks,
                   timing_rule='All four roots synchronous; keep all cross-root setup/hold checks. No asynchronous clock groups.',
                   source_evidence=['tools/qwen_kv_die/kv_die.py:_host_v14_buses',
                       'results/arch/qwen_split_1014/host_bind_request_1014/die_wiring.json:ck_station/ck_static',
                       'rtl/test/qwen_split/tb_host_pc_slice_die.sv:same actual clock for all four entries'],
                   boot_clock_note='ck_boot and ck_boot_test are on the actual die core trunk, as in the source parent equivalence; HBM reset naming does not change the clock family.',
                   local_two_track_cut=dict(NS_M5=0.5,WE_M4=0.2),
                   reroute_reason='slot_change: measured 1.0 local pin cut and M8 area clock pins replaced by legal M4/M5 face grants',
                   qualification='PIN_GRANT_ONLY: no leaf closure, native boundary, or whole-die qualification inferred')
        (out/f'{name}.json').write_text(json.dumps(rec,indent=1)+'\n')
        (out/f'{name}.tcl').write_text('\n'.join(lines)+'\n')
        records[name]=dict(pins=len(pins),clock_roots=len(clocks),max_signal_layer='M5',geometry_overlap=0)
    return records

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--out',type=Path,required=True)
    print(json.dumps(export(ap.parse_args().out)))
