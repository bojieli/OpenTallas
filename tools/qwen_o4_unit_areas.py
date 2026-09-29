#!/usr/bin/env python3
"""Pre-layout ASAP7 cell area of the Qwen O4 datapath units the die RTL repeats.

Each unit is synthesised alone with the pinned yosys 0.68 and ABC (-D at the
adopted 910 ps period) onto the ASAP7 RVT TT libraries, the same mapping the
physical driver's synth stage uses. These are cell areas before placement,
repair and routing; the floorplan applies a utilisation from routed records.
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
OUT = ROOT / 'results/floorplan/qwen_o4_unit_areas.json'
YOSYS = os.environ.get('OT_YOSYS', '/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys')
LIB = Path(os.environ.get('OT_ASAP7_NLDM', '/home/ubuntu/.local/opentallas-pdk-asap7/lib/NLDM'))
LIBS = ['asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib', 'asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib',
        'asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib', 'asap7sc7p5t_AO_RVT_TT_nldm_211120.lib',
        'asap7sc7p5t_OA_RVT_TT_nldm_211120.lib']
SOURCES = ['rtl/hdc/ot_hdc_delay.sv', 'rtl/hdc/ot_hdc_fp32_mul_pipe.sv', 'rtl/hdc/ot_hdc_fpu.sv',
           'rtl/proto/ot_fp32_add_rne_pipe.sv', 'rtl/hdc/ot_hdc_sfu.sv', 'rtl/hdc/ot_hdc_fastfp.sv']
UNITS = ['ot_hdc_bmul', 'ot_hdc_fadd', 'ot_hdc_qadd', 'ot_hdc_fmul']
PERIOD_PS = 910


def synth(top):
    with tempfile.TemporaryDirectory() as d:
        log = Path(d) / 'y.log'
        seq = LIB / LIBS[0]
        comb = ' '.join(f'-liberty {LIB / l}' for l in LIBS[1:])
        allk = ' '.join(f'-liberty {LIB / l}' for l in LIBS)
        cmd = (f"read_verilog -sv {' '.join(SOURCES)}; hierarchy -top {top}; synth -flatten -top {top}; "
               f"dfflibmap -liberty {seq}; abc -D {PERIOD_PS} {comb}; opt_clean; stat {allk}")
        subprocess.run([YOSYS, '-q', '-l', str(log), '-p', cmd], cwd=ROOT, check=True,
                       stdout=subprocess.DEVNULL)
        text = log.read_text()
    area = float(re.findall(r"Chip area for module '\\\S+': ([\d.]+)", text)[-1])
    cells = int(re.findall(r'Number of cells:\s+(\d+)', text)[-1]) if re.findall(r'Number of cells:\s+(\d+)', text) else None
    return dict(module=top, area_um2=area, cells=cells)


def dff_area():
    text = (LIB / LIBS[0]).read_text()
    m = re.search(r'cell \(DFFHQNx1_ASAP7_75t_R\)\s*\{\s*area : ([\d.]+);', text)
    return float(m.group(1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--output', type=Path, default=OUT)
    args = ap.parse_args()
    with ThreadPoolExecutor(len(UNITS)) as ex:
        units = list(ex.map(synth, UNITS))
    rec = dict(schema='opentallas.qwen-o4-unit-areas.v1', tool='tools/qwen_o4_unit_areas.py',
               tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               source_sha256={s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in SOURCES},
               yosys=YOSYS, abc_delay_ps=PERIOD_PS, corner='ASAP7 RVT TT 0.7 V (NLDM)',
               units=units, dff_bit_um2=dff_area(), dff_cell='DFFHQNx1_ASAP7_75t_R',
               claim_boundary='pre-layout cell area; no placement, repair, clock tree or routing')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(rec['units']))


if __name__ == '__main__':
    main()
