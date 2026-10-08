#!/usr/bin/env python3
"""Emit an isolated actual r21 link subsystem with directional clock ownership.
No native endpoint, physical closure, or warm-reset adoption is implied.
"""
import argparse
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'results/uarch/qwen_link_forwarded_graph_20261007'

def emit(graph, connections):
    edges={e['id']:e for e in graph['edges']}
    pairs=connections['pairs']
    path_index={(p['hub_face'],p['hub_lane']):i for i,p in enumerate(connections['paths'])}
    strip_index={p['endpoint']:i for i,p in enumerate(connections['paths'])}
    lines=['`timescale 1ns/1ps',
      '// Actual r21 transport graph only. Cold POR; no warm reset or endpoint credit/protection claim.',
      'module ot_qwen_link_graph_r22 #(parameter integer ENABLE=0) (',
      ' input wire link_por_n,',
      ' input wire [3:0] hub_tx_clk, strip_tx_clk,',
      ' input wire [2111:0] hub_tx_data, strip_tx_data,',
      ' output wire [3:0] hub_rx_clk, strip_rx_clk,',
      ' output wire [2111:0] hub_rx_data, strip_rx_data',
      ');']
    names={name:f'e{i}' for i,name in enumerate(edges)}
    drivers={};readers={};bindings=[]
    def own(edge,lane,direction,owner):
        key=(edge,lane,direction)
        if key in drivers:raise AssertionError(('duplicate driver',key))
        drivers[key]=owner
    def read(edge,lane,direction,owner):
        key=(edge,lane,direction)
        if key in readers:raise AssertionError(('duplicate reader',key))
        readers[key]=owner
    for e in edges.values():
        nl=e['bits']//1056;assert nl*1056==e['bits']
        en=names[e['id']]
        lines += [f' wire [{nl*528-1}:0] {en}_down, {en}_up;',f' wire [{nl-1}:0] {en}_dclk, {en}_uclk;']
        a,b=e['endpoints']
        if a[0]=='hub_el':
            for lane in range(nl):
                ix=path_index[(a[1],lane)];off=lane*528;ex=ix*528
                lines += [f' assign {en}_down[{off}+:528]=hub_tx_data[{ex}+:528];',
                          f' assign {en}_dclk[{lane}]=hub_tx_clk[{ix}];',
                          f' assign hub_rx_data[{ex}+:528]={en}_up[{off}+:528];',
                          f' assign hub_rx_clk[{ix}]={en}_uclk[{lane}];']
                own(e['id'],lane,'down','hub');read(e['id'],lane,'up','hub')
        if b[0] in strip_index:
            assert nl==1
            ix=strip_index[b[0]];ex=ix*528
            lines += [f' assign {en}_up=strip_tx_data[{ex}+:528];',f' assign {en}_uclk=strip_tx_clk[{ix}];',
                      f' assign strip_rx_data[{ex}+:528]={en}_down;',f' assign strip_rx_clk[{ix}]={en}_dclk;']
            own(e['id'],0,'up',b[0]);read(e['id'],0,'down',b[0])
    for i,p in enumerate(pairs):
        a,b=names[p['in_edge']],names[p['out_edge']];al,bl=p['in_lane'],p['out_lane'];ao,bo=al*528,bl*528
        lines += [f' // {p["node"]}: {p["in_edge"]}[{al}] <-> {p["out_edge"]}[{bl}]',
          f' ot_qwen_die_link_fwd_full #(.NL(1),.ENABLE(ENABLE)) u_stage_{i} (',
          '  .rst_n(link_por_n),',
          f'  .fclk_ab_i({a}_dclk[{al}]), .fclk_ab_o({b}_dclk[{bl}]),',
          f'  .fclk_ba_i({b}_uclk[{bl}]), .fclk_ba_o({a}_uclk[{al}]),',
          f'  .a_i({a}_down[{ao}+:528]), .a_o({a}_up[{ao}+:528]),',
          f'  .b_i({b}_up[{bo}+:528]), .b_o({b}_down[{bo}+:528]) );']
        own(p['out_edge'],bl,'down',i);own(p['in_edge'],al,'up',i)
        read(p['in_edge'],al,'down',i);read(p['out_edge'],bl,'up',i)
        bindings.append(dict(instance=f'u_stage_{i}',node=p['node'],NL=1,reset='link_por_n',
          ab_clock_input=f'{a}_dclk[{al}]',ab_clock_output=f'{b}_dclk[{bl}]',
          ba_clock_input=f'{b}_uclk[{bl}]',ba_clock_output=f'{a}_uclk[{al}]'))
    expected={(e['id'],i,d) for e in edges.values() for i in range(e['bits']//1056) for d in ['up','down']}
    assert set(drivers)==set(readers)==expected
    lines+=['endmodule','']
    return '\n'.join(lines),dict(primitives=len(pairs),directional_stream_segments=len(expected),
      every_stream_has_one_driver_and_reader=True,bindings=bindings,endpoint_order=connections['paths'],
      default_off=True,adopted=False,physical_closed=False)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    graph=json.loads((DATA/'graph.json').read_text());con=json.loads((DATA/'connections.json').read_text())
    rtl,record=emit(graph,con);a.out.mkdir(parents=True,exist_ok=False)
    (a.out/'ot_qwen_link_graph_r22.sv').write_text(rtl)
    record['rtl_sha256']=hashlib.sha256(rtl.encode()).hexdigest()
    record['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),DATA/'graph.json',DATA/'connections.json']}
    (a.out/'bindings.json').write_text(json.dumps(record,indent=2)+'\n')
    print(f'PASS directional graph: {record["primitives"]} primitives, {record["directional_stream_segments"]} owned streams')
if __name__=='__main__':main()
