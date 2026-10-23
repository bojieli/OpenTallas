#!/usr/bin/env python3
"""Emit the minimum actual cap30 reset/gate cone and real landing-ring probe.

Regional roots use the existing token-bench common phase; this does not test
physical skew. No frame datapath, ROM, arithmetic or full slice is instantiated.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from frame_chain_reset_v2 import inspect


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--original', required=True)
    ap.add_argument('--corrected', required=True)
    ap.add_argument('--source-root', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=False)
    old = Path(a.original).read_text(); new = Path(a.corrected).read_text()
    _, changed, _, _ = inspect(old, 4)
    frames, _, relays, aliases = inspect(new, 4)
    nets, ext = set(), set()
    def take(n):
        if n in nets: return
        nets.add(n)
        if n in relays:
            take(relays[n]['rs']); take(relays[n]['inp'])
        elif n in aliases: take(aliases[n])
        else: ext.add(n)
    for inst, c in changed.items():
        take(c['reset']); take(frames[inst]['rst'])
        for l in frames[inst]['lanes']:
            take(l['gate']['ena'])
        for u in c['upstream']:
            for l in frames[u]['lanes']: take(l['gate']['ena'])
    assert len(ext) == 1 and ext <= {'rst_sync1', 'rst_n'}, ('unknown reset roots', ext)
    root_reset = next(iter(ext))
    lines = ['`timescale 1ns/1ps', 'module tb_frame_calendar;',
        f'reg ck=0, {root_reset}=0; always #0.5 ck=~ck;',
        f'integer mut=0, cycles=0; initial begin void\'($value$plusargs("MUT=%d",mut)); #2.2 {root_reset}=1; end',
        'always @(posedge ck) cycles <= cycles+1;']
    for n in sorted(nets - ext):
        lines.append('wire ' + n + ';')
        if n in relays:
            r = relays[n]; lines.append(re.sub(r'\.ck\([^)]*\)', '.ck(ck)', r['line']))
        else: lines.append('assign ' + n + ' = ' + aliases[n] + ';')
    faults, counters = [], []
    for j, (inst, c) in enumerate(changed.items()):
        frame = frames[inst]
        lines += [f'wire fr{j} = mut ? {c["reset"]} : {frame["rst"]};',
            f'reg [3:0] qr{j}=0; always @(posedge ck or negedge fr{j}) if(!fr{j}) qr{j}<=0; else qr{j} <= {{qr{j}[2:0],1\'b1}};',
            f'integer first_read{j}=-1; always @(posedge ck) if(qr{j}[3] && first_read{j}<0) first_read{j}<=cycles;']
        for k, lane in enumerate(frame['lanes']):
            g = lane['gate']; m = re.match(r'(u_f_\w+?)_xok\[(\d+)\]', g['ck'])
            assert m, (inst, g)
            u, ix = m[1], int(m[2]); source = frames[u]['lanes'][3-ix]
            tag = f'p{j}_{k}'; ug = source['gate']
            lines += [f'wire {tag}_g0, {tag}_up, {tag}_g1, {tag}_wf;',
                f'ICGx4_ASAP7_75t_R {tag}_a (.CLK(ck),.ENA({ug["ena"]}),.SE(1\'b0),.GCLK({tag}_g0));',
                f'assign {tag}_up = {tag}_g0 ^ 1\'b{source["stages"]%2};',
                f'ICGx4_ASAP7_75t_R {tag}_b (.CLK({tag}_up),.ENA({g["ena"]}),.SE(1\'b0),.GCLK({tag}_g1));',
                f'assign {tag}_wf = {tag}_g1 ^ 1\'b{lane["stages"]%2};',
                f'wire {tag}_o, {tag}_fault;',
                f'ot_s81_land #(.W(1),.D(4)) {tag}_land (.k(3\'d2),.ck_f({tag}_wf),.i(cycles[0]),.ck(ck),.rs(qr{j}[3]),.o({tag}_o),.fault({tag}_fault));',
                f'integer {tag}_writes=0; always @(posedge {tag}_wf) if($time>0) {tag}_writes <= {tag}_writes+1;']
            faults.append(tag + '_fault'); counters.append(tag + '_writes')
    ncy = max(f['read_epoch'] for f in frames.values()) + 64
    lines += [f'initial begin repeat({ncy}) @(negedge ck);', ' $display("FRAME_CAL histories cycles=%0d mut=%0d",cycles,mut);']
    for j, (inst, c) in enumerate(changed.items()):
        lines.append(f' $display("FRAME_CAL {inst} read_first=%0d delay={c["delay"]}",first_read{j});')
    lines += [' if (' + ' | '.join(faults) + ') $fatal(1,"FRAME_CAL FAIL real landing epoch fault");',
        ' if (' + ' || '.join(n + '<32' for n in counters) + ') $fatal(1,"FRAME_CAL FAIL unexercised lane");',
        f' $display("FRAME_CAL PASS frames={len(changed)} lanes={len(faults)} unchanged_ret_lane_gates=1"); $finish; end', 'endmodule']
    # Use the actual reset relay and landing bodies selected in the executed
    # source snapshot. The W=1 relay wrapper is the exact native generator body.
    root = Path(a.source_root)
    copies = ['rtl/dsrom_sys/s81_glue/ot_s81_rly.sv', 'rtl/dsrom_sys/s81_dv/land/ot_s81_land.sv']
    hashes = {}
    for p in copies:
        body = (root / p).read_bytes(); (out / Path(p).name).write_bytes(body)
        hashes[p] = hashlib.sha256(body).hexdigest()
    masters = sorted({relays[n]['master'] for n in nets if n in relays})
    cell = '\n'.join(f'module {m}(input ck,rs,i,output o); ot_s81_rly #(.W(1)) u(.ck(ck),.rs(rs),.i(i),.o(o)); endmodule' for m in masters)
    cell += '\nmodule ICGx4_ASAP7_75t_R(input CLK,ENA,SE,output GCLK); reg en_l; /* verilator lint_off COMBDLY */ always_latch if(!CLK) en_l=ENA|SE; /* verilator lint_on COMBDLY */ assign GCLK=CLK&en_l; endmodule\n'
    (out / 'cells.sv').write_text(cell); (out / 'tb_frame_calendar.sv').write_text('\n'.join(lines)+'\n')
    (out / 'source.json').write_text(json.dumps(dict(actual_source_sha256=hashes, reset_stations=len([n for n in nets if n in relays]),
        frames=changed, scope='actual reset release and lane clock parity cone with real W1 landing epochs; common phase regional roots, no datapath or physical skew claim'),indent=1)+'\n')


if __name__ == '__main__': main()
