#!/usr/bin/env python3
"""Pre-layout ASAP7 area of the Qwen O4 representative clusters.

Synthesises the ROM/MAC neighbourhood (rtl/physical/ot_qwen_o4_g4_rommac.sv) as
a result-port neighbourhood (SCALE_BANKS = 1) and as an ordinary one
(SCALE_BANKS = 0), and the 8-skew-bank VM cut (rtl/physical/ot_qwen_o4_g4_vm_cut.sv)
with pinned yosys 0.68 + ABC (-D 910) on ASAP7 RVT TT. Macros are black boxes;
their area comes from the LEF views. The floorplan sizes its neighbourhood
logic channels from these cell areas until routed records replace them.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/floorplan/qwen_o4_cluster_synth.json'
YOSYS = os.environ.get('OT_YOSYS', '/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys')
LIB = Path(os.environ.get('OT_ASAP7_NLDM', '/home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM'))
LIBS = ['asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib', 'asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib',
        'asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib', 'asap7sc7p5t_AO_RVT_TT_nldm_211120.lib',
        'asap7sc7p5t_OA_RVT_TT_nldm_211120.lib']
M = 'physical/asap7_memory_macros'
FP = ['rtl/hdc/ot_hdc_delay.sv', 'rtl/hdc/ot_hdc_fp32_mul_pipe.sv', 'rtl/hdc/ot_hdc_fpu.sv',
      'rtl/proto/ot_fp32_add_rne_pipe.sv', 'rtl/hdc/ot_hdc_sfu.sv', 'rtl/hdc/ot_hdc_fastfp.sv',
      'rtl/hdc/ot_hdc_matvec.sv']
CASES = {
    'rommac_port': dict(top='ot_qwen_o4_g4_rommac', params={'SCALE_BANKS': 1},
                        sources=FP + [f'{M}/ot_rom_4096x266_m8/ot_rom_4096x266_m8_bb.v',
                                      'rtl/physical/ot_qwen_o4_g4_rommac.sv'],
                        macros={'ot_rom_4096x266_m8': 26}),
    'rommac_plain': dict(top='ot_qwen_o4_g4_rommac', params={'SCALE_BANKS': 0},
                         sources=FP + [f'{M}/ot_rom_4096x266_m8/ot_rom_4096x266_m8_bb.v',
                                       'rtl/physical/ot_qwen_o4_g4_rommac.sv'],
                         macros={'ot_rom_4096x266_m8': 22}),
    'vm_cut': dict(top='ot_qwen_o4_g4_vm_cut', params={},
                   sources=[f'{M}/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2_bb.v',
                            'rtl/physical/ot_qwen_g4_vm_skew_candidate.sv', 'rtl/physical/ot_qwen_o4_g4_vm_cut.sv'],
                   macros={'ot_sram_1r1w_512x128_m4_r2c2': 32}),
}


def synth(name):
    c = CASES[name]
    with tempfile.TemporaryDirectory() as d:
        log = Path(d) / 'y.log'
        chp = ' '.join(f'-chparam {k} {v}' for k, v in c['params'].items())
        comb = ' '.join(f'-liberty {LIB / l}' for l in LIBS[1:])
        allk = ' '.join(f'-liberty {LIB / l}' for l in LIBS)
        cmd = (f"read_verilog -sv {' '.join(c['sources'])}; hierarchy -top {c['top']} {chp}; "
               f"synth -flatten -top {c['top']}; dfflibmap -liberty {LIB / LIBS[0]}; abc -D 910 {comb}; "
               f"opt_clean; stat {allk}")
        subprocess.run([YOSYS, '-q', '-l', str(log), '-p', cmd], cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
        text = log.read_text()
    area = float(re.findall(r"Chip area for module '\\\S+': ([\d.]+)", text)[-1])
    seq = 0.0
    for m in re.finditer(r'^\s+(\d+)\s+([\d.]+)\s+(DFF\S+|ASYNC\S+)$', text, re.M):
        seq += float(m.group(2))
    cells = re.findall(r'^\s+(\d+)\s+[\d.]+\s+cells$', text, re.M) or re.findall(r'Number of cells:\s+(\d+)', text)
    return name, dict(top=c['top'], params=c['params'], cell_area_um2=area,
                      sequential_area_um2=round(seq, 3), cells=int(cells[-1]) if cells else None,
                      macros=c['macros'],
                      source_sha256={s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in c['sources']})


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--output', type=Path, default=OUT)
    args = ap.parse_args()
    with ThreadPoolExecutor(len(CASES)) as ex:
        res = dict(ex.map(synth, CASES))
    rec = dict(schema='opentallas.qwen-o4-cluster-synth.v1', tool='tools/qwen_o4_cluster_synth.py',
               tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), yosys=YOSYS,
               abc_delay_ps=910, corner='ASAP7 RVT TT 0.7 V', clusters=res,
               claim_boundary='pre-layout standard-cell area; macros black-boxed')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps({k: (v['cell_area_um2'], v['cells']) for k, v in res.items()}))


if __name__ == '__main__':
    main()
