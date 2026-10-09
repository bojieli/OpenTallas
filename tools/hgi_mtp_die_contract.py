"""Source-derived18-bit fullcore facade. Does not reuse historical17-bit widths."""
import hashlib
import json
from pathlib import Path
import die_top_lint as L
from hbm_mtp_native_contract import peer

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'rtl/hbm_accel/generic/ot_hgi_mtp_core18.sv'
PARAMS = {'GENERIC18': 1, 'TW': 18, 'SPECF': 0}


def model():
    ports = L.parse_module(SOURCE, 'ot_hgi_mtp_core18', PARAMS)['ports']
    groups = {}
    for name, (direction, width) in ports.items():
        destination = peer(name)
        if destination == 'clock':
            continue
        key = ('f_' if direction == 'input' else 't_') + destination
        group = groups.setdefault(key, dict(direction=direction, bits=0, fields=[]))
        group['fields'].append(dict(port=name, lsb=group['bits'], width=width))
        group['bits'] += width
    required = {'p_tok':18,'f_tok':18,'e_tok':18,'cmd_tok1':18,'cmd_toks':144,'am_idx':18,'sa_tok':18}
    for name, width in required.items():
        if ports[name][1] != width:
            raise ValueError(f'{name}: fullcore18 must carry {width} bits')
    return dict(schema='opentallas.hgi_mtp_die_contract.v1', source_commit='6de65ee0e',
                source=SOURCE, source_sha256=hashlib.sha256((ROOT / SOURCE).read_bytes()).hexdigest(),
                module='ot_hgi_mtp_core18', params=PARAMS, master='hfd_mtp_generic18',
                groups=groups, replicas=1, MACs_per_cycle=0, memory_bytes_per_cycle=0,
                signal_bits_per_cycle=sum(g['bits'] for g in groups.values()),
                total_signal_tracks_lower_bound=2*sum(g['bits'] for g in groups.values()),
                facade_added_cycles=0, core_edges_vs_bare_controller=4,
                reserved_slot_um=[466.56,200.88], measured_new_area_um2=None,
                floorplan_slot_fit=None, physical_ready=False,
                dependencies=['matching SPECF0 fullcore exact replay and mutant',
                              'actual wholecore registered boundary audit',
                              'real18-bit host/history/command/collective peer binding',
                              'current route/area and electrical qualification'])


def render(contract):
    lines=['`timescale 1ns/1ps','`default_nettype none',
           '// Opt-in source-derived TW18 facade; SPECF0 must qualify independently.',
           'module hfd_mtp_generic18 #(parameter integer ENABLE=0) (',
           ' input wire clk, input wire rst_n,']
    decl=[]
    for name, group in contract['groups'].items():
        decl.append(f" {group['direction']} wire [{group['bits']-1}:0] {name}")
    lines+= [',\n'.join(decl),');',' generate if (ENABLE==0) begin:g_off']
    for name, group in contract['groups'].items():
        if group['direction']=='output':lines.append(f" assign {name}='0;")
    lines+=[' end else begin:g_on',' ot_hgi_mtp_core18 #(.GENERIC18(1),.TW(18),.SPECF(0)) core (',
            ' .clk(clk), .rst_n(rst_n),']
    conns=[]
    for name, group in contract['groups'].items():
        for f in group['fields']:conns.append(f" .{f['port']}({name}[{f['lsb']} +: {f['width']}])")
    lines += [',\n'.join(conns),');',' end endgenerate','endmodule','`default_nettype wire']
    return '\n'.join(lines)+'\n'


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    c=model();a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'contract.json').write_text(json.dumps(c,indent=2)+'\n')
    (a.out/'hfd_mtp_generic18.sv').write_text(render(c))
    print(json.dumps({k:g['bits'] for k,g in c['groups'].items()}))
