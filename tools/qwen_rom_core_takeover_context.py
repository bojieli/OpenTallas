#!/usr/bin/env python3
"""Re-use the retained core screen's actual parameter cut; emit unmapped control RTL."""
import argparse,hashlib,json,re
from pathlib import Path
import qwen_rom_core_dec_emit_w12 as E
p=argparse.ArgumentParser();p.add_argument('--retained',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--bounded',action='store_true');p.add_argument('--chaseq',action='store_true');p.add_argument('--counter-la',action='store_true');a=p.parse_args();a.out.mkdir(exist_ok=False)
root=Path(__file__).resolve().parents[1]
s=E.emit(E.V.E.CORE.read_text())
if a.bounded or a.chaseq or a.counter_la:
    from qwen_rom_core_dec_bound_emit_w12 import apply
    s=apply(s)
if a.chaseq or a.counter_la:
    from qwen_rom_core_dec_chaseq_emit_w12 import apply
    s=apply(s)
if a.counter_la:
    from qwen_rom_core_dec_counter_emit_w12 import apply
    s=apply(s)
# Same Yosys0.68 unpacked-port workaround as retained Claude context.
s=s.replace('    generate if (VPOS != 0) begin : g_vpos_tiles\n        genvar vpt;\n','    genvar vpt;\n    generate if (VPOS != 0) begin : g_vpos_tiles\n')
for old,new in [('    wire [NW-1:0] dynp_tiles_zero [0:7];\n','    wire [8*NW-1:0] dynp_tiles_zero_f;\n'),('.rounds(dynp_tiles_zero[vpt])','.rounds(dynp_tiles_zero_f[vpt*NW +: NW])'),('<= dynp_tiles_zero[vpo];','<= dynp_tiles_zero_f[vpo*NW +: NW];')]:
    assert s.count(old)==1,old;s=s.replace(old,new)
(a.out/'core.sv').write_text(s)
oldroot='/srv/opentallas-scratch/claude/qwen-core-decode/src/'
old=(root/'results/rtl/qwen_rom_core_takeover_20261005/retained_screen/synth.ys').read_text()
lines=[]
for line in old.splitlines():
    if line.startswith(('dfflibmap','abc ','setundef','splitnets','tee ','write_verilog')):continue
    if line.startswith('read_verilog '):
        f=line.split()[-1].removeprefix(oldroot)
        selected=a.out/'core.sv' if f.startswith('gen/ot_qwen_rom_core_scr_') else (root/f if (root/f).is_file() else a.retained/f)
        if not selected.is_file():raise FileNotFoundError(selected)
        lines.append(f'read_verilog -sv -I{root}/rtl/hdc {selected}')
    elif line.startswith('synth '):lines.append(line+' -noabc')
    elif line.startswith('hierarchy ') and (a.bounded or a.chaseq or a.counter_la):
        lines.append(line+' -chparam DEC_LA_BOUND 1'+(' -chparam DEC_LA_CHASE_Q 1' if a.chaseq or a.counter_la else '')+(' -chparam DEC_LA_COUNT_LA 1' if a.counter_la else ''))
    else:lines.append(line)
lines.append(f'write_verilog -noattr {a.out}/control_context.v')
(a.out/'prepare.ys').write_text('\n'.join(lines)+'\n')
(a.out/'inputs.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(s.encode()).hexdigest(),
    parameter_source='retained AR core_d1v0g; DEC_LA1 VPOS0; no timing exceptions',
    emitted_source='unmapped actual control after same expose-evert spine/stream boundaries; argmax/chase/run_val retained',
    clock_ps=833,setup_uncertainty_ps=60,hold_uncertainty_ps=25,arithmetic_engines_qualified=False),indent=2)+'\n')
