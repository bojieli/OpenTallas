#!/usr/bin/env python3
"""Checkpoint full-shape ME gate with pipe2 and input-registered shared SRAM."""
import argparse
import json
from pathlib import Path

import rtl_hdc_v41x_fullshape_woa_exact as base

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'rtl/hdc/v41x/ot_hdc_v41x_fp32_bf16_preload64.sv'
PIPE=ROOT/'rtl/hdc/v41x/ot_hdc_v41x_fp32_bf16_preload64_pipe2.sv'
ALIAS=ROOT/'rtl/test/ot_hdc_v41x_fp32_bf16_preload64_pipe2_alias.sv'
base.RTL=[p for p in base.RTL if p != OLD]
base.RTL[0:0]=[PIPE,ALIAS]

def main():
    ap=argparse.ArgumentParser()
    for name in ('acc','za','image','golden-manifest','layout-manifest'):
        ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--rows',type=int,default=16)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    d=base.run(a.acc,a.za,a.image,a.golden_manifest,a.layout_manifest,
               a.rows,a.output,banked=False,macro=False,rl=4,shared=True,preloaded=True,input_registered=True)
    d['converter_pipeline_cycles']=2
    d['sram_input_register_cycles']=1
    d['claim_scope']=d['claim_scope'].replace('No full-layer or chip-throughput claim.',
        'Uses bank-major 64-wide two-stage converter and input-registered eight-macro MP1 SRAM; no VM controller, full-layer or chip-throughput claim.')
    d['source_sha256'][str(Path(__file__).relative_to(ROOT))]=base.sha(Path(__file__))
    a.output.write_text(json.dumps(d,indent=2)+'\n')
    print(json.dumps({k:d[k] for k in ('status','exact_rows','simulation_cycles','preload_issue_cycles','converter_pipeline_cycles','sram_input_register_cycles')}))

if __name__=='__main__':main()
