#!/usr/bin/env python3
"""Re-use the retained core screen's actual parameter cut; emit unmapped control RTL."""
import argparse,hashlib,json,re
from pathlib import Path
import qwen_rom_core_dec_emit_w12 as E
p=argparse.ArgumentParser();p.add_argument('--retained',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--bounded',action='store_true');p.add_argument('--chaseq',action='store_true');p.add_argument('--counter-la',action='store_true');p.add_argument('--am-commit',action='store_true');p.add_argument('--retain-receivers',action='store_true');a=p.parse_args();a.out.mkdir(exist_ok=False)
root=Path(__file__).resolve().parents[1]
s=E.emit(E.V.E.CORE.read_text())
if a.bounded or a.chaseq or a.counter_la or a.am_commit:
    from qwen_rom_core_dec_bound_emit_w12 import apply
    s=apply(s)
if a.chaseq or a.counter_la or a.am_commit:
    from qwen_rom_core_dec_chaseq_emit_w12 import apply
    s=apply(s)
if a.counter_la or a.am_commit:
    from qwen_rom_core_dec_counter_emit_w12 import apply
    s=apply(s)
if a.am_commit:
    from qwen_rom_core_dec_commit_emit_w12 import apply
    s=apply(s)
# Same Yosys0.68 unpacked-port workaround as retained Claude context.
s=s.replace('    generate if (VPOS != 0) begin : g_vpos_tiles\n        genvar vpt;\n','    genvar vpt;\n    generate if (VPOS != 0) begin : g_vpos_tiles\n')
for old,new in [('    wire [NW-1:0] dynp_tiles_zero [0:7];\n','    wire [8*NW-1:0] dynp_tiles_zero_f;\n'),('.rounds(dynp_tiles_zero[vpt])','.rounds(dynp_tiles_zero_f[vpt*NW +: NW])'),('<= dynp_tiles_zero[vpo];','<= dynp_tiles_zero_f[vpo*NW +: NW];')]:
    assert s.count(old)==1,old;s=s.replace(old,new)
(a.out/'core.sv').write_text(s)
oldroot='/srv/opentallas-scratch/claude/qwen-core-decode/src/'
old=(root/'results/rtl/qwen_rom_core_takeover_20261005/retained_screen/synth.ys').read_text()
lines=[]
# Physical receiver context retains the selected original ROM engine RTL, not
# a donor controller or invented input flops. Same core/clock/parameters.
if a.retain_receivers:
    # The selected original runtime source closure, without importing its
    # numerical/native-build driver into a physical preparation checkout.
    receiver_rtl=[root/'rtl/hdc'/f'{name}.sv' for name in (
        'ot_hdc_delay','ot_hdc_fp32_mul_pipe','ot_hdc_fpu','ot_hdc_fastfp',
        'ot_hdc_sfu','ot_hdc_sfu_q','ot_hdc_reduce','ot_hdc_reduce_q',
        'ot_hdc_matvec','ot_hdc_stream','ot_hdc_vstream_lane','ot_hdc_vreduce',
        'ot_hdc_vstream','ot_hdc_dyn_ttiles','ot_hdc_qwen_int8_arith',
        'ot_hdc_qwen_int8_embed_decode','ot_hdc_cg','ot_qwen_me_array_w12',
        'ot_hdc_fp32_add_lat','ot_hdc_prefix','ot_qwen_w12_matvec','ot_qwen_w12_arith')]
    receiver_rtl += [root/'rtl/proto'/f'{name}.sv' for name in
                     ('ot_fp32_add_rne_pipe','ot_fp32_mul_rne_pipe')]
    already={Path(line.split()[-1]).name for line in old.splitlines() if line.startswith('read_verilog ')}
    seen=set(already)
    for source in receiver_rtl:
        if source.name in seen or source.suffix != '.sv':
            continue
        if not source.is_file():
            raise FileNotFoundError(source)
        seen.add(source.name)
        lines.append(f'read_verilog -sv -I{root}/rtl/hdc {source}')
for line in old.splitlines():
    if a.retain_receivers and line.startswith(('blackbox ', 'expose ')):
        # These operations removed the genuine ME/SU capture endpoints.
        # Do not recreate them as an externally timed/ideal port.
        continue
    if line.startswith(('dfflibmap','abc ','setundef','splitnets','tee ','write_verilog')):continue
    if line.startswith('read_verilog '):
        f=line.split()[-1].removeprefix(oldroot)
        selected=a.out/'core.sv' if f.startswith('gen/ot_qwen_rom_core_scr_') else (root/f if (root/f).is_file() else a.retained/f)
        if not selected.is_file():raise FileNotFoundError(selected)
        lines.append(f'read_verilog -sv -I{root}/rtl/hdc {selected}')
    elif line.startswith('synth '):lines.append(line+' -noabc')
    elif line.startswith('hierarchy ') and (a.bounded or a.chaseq or a.counter_la or a.am_commit):
        lines.append(line+' -chparam DEC_LA_BOUND 1'+(' -chparam DEC_LA_CHASE_Q 1' if a.chaseq or a.counter_la or a.am_commit else '')+(' -chparam DEC_LA_COUNT_LA 1' if a.counter_la or a.am_commit else '')+(' -chparam DEC_LA_AM_COMMIT 1' if a.am_commit else ''))
    else:lines.append(line)
lines.append(f'write_verilog -noattr {a.out}/control_context.v')
(a.out/'prepare.ys').write_text('\n'.join(lines)+'\n')
(a.out/'inputs.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(s.encode()).hexdigest(),
    parameter_source='retained AR core_d1v0g; DEC_LA1 VPOS0; no timing exceptions',
    emitted_source=('original ROM core plus real ME/SU receiver RTL; capture and feedback retained' if a.retain_receivers else 'unmapped actual control after same expose-evert spine/stream boundaries; argmax/chase/run_val retained'),
    clock_ps=833,setup_uncertainty_ps=60,hold_uncertainty_ps=25,arithmetic_engines_qualified=False,
    actual_receivers_retained=a.retain_receivers,
    receiver_source='original ROM u_me.u_top and g_vsu.u_su; no native696a5 arithmetic substitution',
    receiver_clocks='actual me_clk ICG + coreclk SU, no timing exceptions',
    physical_scope='full actual receiver/control RTL' if a.retain_receivers else 'legacy exposed controller cut'),indent=2)+'\n')
