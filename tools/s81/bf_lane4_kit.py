#!/usr/bin/env python3
"""Produce the prototype production TRW7 leaf kit (no parent adoption claim)."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    out=ROOT/'physical/ref_tile_specs/s81_bf_native_1015/lane4';out.mkdir(parents=True,exist_ok=True)
    ins=['ze_d','v_s']+[f'{n}[{i}]' for n,w in [('w_s',64),('x_s',64),('t_p',13)] for i in range(w)]
    outs=[f'{n}[{i}]' for n,w in [('cv',4),('cf',4),('cfault',4),('cs_p',128),('ct_p',32)] for i in range(w)]
    assert (len(ins),len(outs))==(143,172)
    pins={};t=['# Production TRW7 lane4 ABI; prototype only.']
    for face,names in [('W',ins),('E',outs)]:
        for j,n in enumerate(names):
            y=round(round((2.16+(j+.5)*90.72/len(names)-.036)/.048)*.048+.036,6)
            x=0 if face=='W' else 95.04;pins[n]=dict(face=face,layer='M4',x=x,y=y)
            t.append(f'place_pin -pin_name {{{n}}} -layer M4 -location {{{x} {y}}} -pin_size {{.192 .024}} -force_to_die_boundary')
    for n,x in [('fclk',47.532),('rst_pin',45.372)]:
        pins[n]=dict(face='S',layer='M5',x=x,y=0)
        t.append(f'place_pin -pin_name {{{n}}} -layer M5 -location {{{x} 0}} -pin_size {{.024 .192}} -force_to_die_boundary')
    (out/'pins.tcl').write_text('\n'.join(t)+'\n')
    (out/'pin_request.json').write_text(json.dumps(dict(status='PROTOTYPE_LEAF_NOT_PARENT_ADOPTION',outline_um=[95.04,95.04],pins=pins,data_input_bits=143,data_output_bits=172,clock_reset_bits=2),indent=2)+'\n')
    base=json.loads((ROOT/'physical/ref_tile/dsfd_bf_front_static_ref/spec.json').read_text())
    s={k:base[k] for k in ['kind','sources','layer_cap','recipe','route','io_flop_at_pins','inhold','outhold','keep_pin_regs','pin_reg_split','hold_pad']}
    s.update(name='s81_bf_lane4_roots_ref',top='ot_v41_bf_lane4',params=dict(NCHB=8,TRW=7,CUT=379,RC=1,GRADUAL_RNE=1,GROUP=0),clock='cts',clock_port='fclk',reset_ports=['rst_pin'],outline=dict(w=95.04,h=95.04,exact=True),pins=dict(W=['ze_d','v_s','w_s','x_s','t_p'],E=['cv','cf','cfault','cs_p','ct_p'],S=['fclk','rst_pin']),io_tcl=str(out.relative_to(ROOT)/'pins.tcl'),macros=[],children=[],inter=[],structural_change='Real source-hierarchy four-lane master x4, dedicated fclk; reviewed arithmetic and original registered boundaries preserved, zero added cycles. Other column leaves open.',pin_regs=dict(enable=False,reason='Real existing lane/chain input registers and arithmetic pipeline outputs retain the compiled timeline; native launch/capture/comb gates remain binding.'),reroute_reason=dict(kind='rtl_change',why='Historical column one-root53493sinks/R535ps fails native',fix='real repeated4lane local source leaf; no unchanged full-column route'),job=dict(owner='Codex:S81-BF-recovery0253',purpose='Prototype localleaf, no pair/die adoption',benches=[],extra_paths=['tools/s81','rtl/s81','rtl/v41rom','results/rtl/s81_bf_clock_1015/c10/recovery_0253','physical/ref_tile_specs/s81_bf_native_1015/lane4'],views_to='physical/s81_die_views/bf_roots_1016/lane4',record_to='results/physical/s81_bf_roots_1016/lane4'))
    s['sources']+=['rtl/v41rom/ot_v41_bf_lane4.sv'];s['route']['peak_ram_gb']=16;s['route']['threads']=8
    (out/'spec.json').write_text(json.dumps(s,indent=2)+'\n')
if __name__=='__main__':main()
