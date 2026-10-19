#!/usr/bin/env python3
"""Produce explicit lane clock/reset ports before safe lpc reset partitioning.

This is a source construction, not native entry/crossing signoff. The current
top-only physical graph cannot qualify its nested stream paths yet.
"""
import json
from pathlib import Path
import re
import gen_slice2_lpf as east
import gen_slice2_w_lpf as west
import gen_su8_landed as su
import reset_partition

ROOT=Path(__file__).resolve().parents[2]


def generate():
    out=su.generate()
    # Explicit region reset inputs only affect lane-local transport and the
    # lane's original reset register. SU control/reducer stay on core reset.
    s=out['rtl/qwen_dv/qfd_dv_su8_landed.sv']
    anchor='    input  wire [SW-1:0] ck_lane,'
    # Preserve maintained source whitespace while checking the actual port.
    m=re.search(r'(\s*input\s+wire\s+\[SW-1:0\]\s+ck_lane\s*,)',s)
    if not m:raise ValueError('SU8 lane clock interface changed')
    s=s[:m.end()]+'\n    input wire [SW-1:0] rst_lane,'+s[m.end():]
    s=s.replace('always @(posedge ck_lane[l] or negedge rst_n) if (!rst_n) rl',
                'always @(posedge ck_lane[l] or negedge rst_lane[l]) if (!rst_lane[l]) rl')
    if s.count('.rsi(rst_n)') != 4:
        raise ValueError('review all four lane transport reset bindings')
    s=s.replace('.rsi(rst_n)', '.rsi(rst_lane[l])')
    out['rtl/qwen_dv/qfd_dv_su8_regional.sv']=s.replace('module qfd_dv_su8_landed','module qfd_dv_su8_regional')
    # Use unpartitioned maintained lpc, change structure, then apply reset
    # partition. Do not patch an already-generated reset tree by hand.
    c=east.core().replace('module qfd_dv_slice2_lpc #(', 'module qfd_dv_slice2_lpc_regional #(')
    c=east.sub1(c,'    input  wire           ck,',
                  '    input  wire           ck,\n    input wire [7:0] ck_lane, rst_lane,')
    c=east.sub1(c,'    wire [7:0]    ck8 = {8{ck}};', '    wire [7:0] ck8 = ck_lane;')
    c=east.sub1(c,'qfd_dv_su8_entries #(', 'qfd_dv_su8_regional #(')
    # Two pin sync + two reset-tree edges is the core's actual release age.
    # Match it independently at every lane root (four loads per raw reset bit).
    at=c.index('    wire [7:0] ck8 = ck_lane;')
    c=c[:at]+'''    wire [7:0] lane_reset;
    genvar lr;
    generate for(lr=0;lr<8;lr=lr+1) begin:g_lane_reset
        (* keep *) reg [3:0] release_pipe;
        always @(posedge ck_lane[lr] or negedge rst_lane[lr])
            if(!rst_lane[lr]) release_pipe <= 0;
            else release_pipe <= {release_pipe[2:0],1'b1};
        assign lane_reset[lr]=release_pipe[3];
    end endgenerate
'''+c[at:]
    a=c.index('qfd_dv_su8_regional #(');b=c.index(');',a)
    body=c[a:b]
    body=east.sub1(body,'.ck_head(ck8)', '.rst_lane(lane_reset), .ck_head(ck8)')
    c=c[:a]+body+c[b:]
    c,record=reset_partition.partition(c,'qfd_dv_slice2_lpc_regional')
    if record['leaf_count'] != 320 or not re.search(r'u_amax\s*\([^;]*\.rst\(sr_reset\[\d+\]\)', c):
        raise ValueError('review core reset census including dedicated MU child leaf')
    out['rtl/qwen_dv/qfd_dv_slice2_regional_parts.sv']=c+east.PARTS_TAIL+east.thru_modules()
    for face,base in [('e',east.top()),('w',west.top())]:
        name=f'qfd_dv_slice2_{face}_regional'
        t=base.replace(f'qfd_dv_slice2_{face}_lpf',name)
        t=east.sub1(t,'qfd_dv_slice2_lpc #(', 'qfd_dv_slice2_lpc_regional #(')
        t=east.sub1(t,'u_c (.ck(ck), .rst_n(rst_n),',
            'u_c (.ck(ck), .ck_lane({8{ck}}), .rst_lane({8{rst_n}}), .rst_n(rst_n),')
        out[f'rtl/qwen_dv/{name}.sv']=t
        spec=west.landed_spec() if face=='w' else json.loads((ROOT/'tools/landed_parent/specs/qfd_dv_slice2_e_lpf.json').read_text())
        spec.update(top=name,sources=[f'rtl/qwen_dv/{name}.sv'],landing_chunk_bits=24,landing_direct_timing=True,
                    record_dir=f'results/arch/safe_qw_slice_w_1019/{face}_regional')
        spec['child_sources']=[p for p in spec['child_sources'] if p!='rtl/qwen_dv/qfd_dv_slice2_lpf_parts.sv']
        replacements={'rtl/qwen_dv/qfd_dv_su8_entries.sv':'rtl/qwen_dv/qfd_dv_su8_regional.sv',
                      'rtl/qwen_dv/qfd_dv_su_lane.sv':'rtl/qwen_dv/qfd_dv_su_lane_landed.sv',
                      'rtl/qwen_dv/mu/qfd_dv_amax_mu.sv':'rtl/qwen_dv/mu/qfd_dv_amax_mu_rsafe.sv',
                      'rtl/qwen_dv/qfd_dv_scalar2.sv':'rtl/qwen_dv/qfd_dv_scalar2_csafe.sv',
                      'rtl/qwen_dv/qfd_dv_redstn2.sv':'rtl/qwen_dv/qfd_dv_redstn2_rsafe.sv'}
        spec['child_sources']=[replacements.get(p,p) for p in spec['child_sources']]
        spec['child_sources'].append('rtl/qwen_dv/qfd_dv_slice2_regional_parts.sv')
        spec['child_sources']+=['rtl/qwen_dv/qfd_dv_reset_tree.sv',
                                'rtl/qwen_dv/qfd_dv_reset_bank.sv',
                                'rtl/qwen_dv/qfd_dv_ring_delay.sv',
                                'rtl/common/landed_parent/ot_pl_stream_land.sv',
                                'physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v']
        spec['defines']=sorted(set((spec.get('defines') or [])+['OT_QFD_DV_SAFE_STORAGE']))
        spec['clock_pins']=sorted(set(spec['clock_pins']+['ck_lane']))
        spec['reset_pins']=sorted(set(spec['reset_pins']+['rst_lane']))
        # Centres are provisional; native-area bands/reach receipts still owed.
        for l in range(8):
            spec['regions'].append(dict(name=f'su{l}',insts=[],centre=[540+432*(l%4),172.8+604.8*(l//4)]))
        roots=[f'su{l}' for l in range(8)]
        spec['regional_child_clocks']=[dict(inst='u_c',pin='ck_lane',regions=roots)]
        spec['regional_child_resets']=[dict(inst='u_c',pin='rst_lane',regions=roots)]
        spec['why']='EXPERIMENTAL explicit eight lane roots/resets, width-aware42 native storage banks, scalar CFG+2 setup edges, new ML5 head and landed read loops. Stream/station reset fixes, exact composed production, native nested crossing audit and physical qualification still required.'
        out[f'tools/landed_parent/specs/{name}.json']=json.dumps(spec,indent=1)+'\n'
    out['results/arch/safe_qw_slice_w_1019/lpc_regional_reset.json']=json.dumps(record,indent=2)+'\n'
    return out


def main():
    for name,text in generate().items():
        target=ROOT/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text);print(name)


if __name__=='__main__':main()
