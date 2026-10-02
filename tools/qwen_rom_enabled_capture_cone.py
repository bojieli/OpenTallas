#!/usr/bin/env python3
"""Extract full current enabled-ROM capture cone and unified model for review."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TILE='rtl/hdc/ot_qwen_rom_tile_w12.sv'


def extract(raw):
    text=raw.decode();start=text.index('    reg  [CODE_BANKS-1:0] code_sel_q;')
    end=text.index('    // -- KV slice',start);logic=text[start:end]
    top=text.index('module ot_qwen_rom_tile_w12 #(')
    begin=text.index('    generate\n        for (p = 0; p < 2;',top)
    finish=text.index('    reg        kvw_ce_q;',begin);macros=text[begin:finish]
    if 'if (code_sel_q[b] && code_rd_q) cap <= rd;' not in logic:
        raise ValueError('Re-review changed enabled capture')
    header='''module qwen_current_enabled_capture #(
 parameter integer W=16,AW=24,TG=4,CODE_BANKS=5,MEM_EXTRA=1
)(input wire clk,rst_n,wrom_re,input wire [AW-1:0] wrom_addr,
 output wire [2*W*8*TG/2-1:0] wrom_q);
 wire [CODE_BANKS-1:0] rom_ce;
 wire [11:0] rom_addr;
 wire [2*CODE_BANKS*266-1:0] rom_rd;
'''
    return (header+logic+macros+'endmodule\n').encode(),logic.encode(),macros.encode()


def generate(output):
    if output.exists():raise ValueError('Refusing to overwrite preparation')
    import uarch_model as U
    if Path(U.__file__).resolve()!=(ROOT/'tools/uarch_model.py').resolve():raise ValueError('Wrong model root')
    raw=(ROOT/TILE).read_bytes();cone,logic,macros=extract(raw)
    model=U.qwen_rom_enabled_capture_contract(enabled=True)
    if model['capture_register_bits']!=2560 or model['ROM_macros']!=10:raise ValueError('Model geometry changed')
    output.mkdir(parents=True);(output/'exact_cone.v').write_bytes(cone)
    record=dict(schema='opentallas.qwen-rom-enabled-capture-preparation.v1',status='READY_CONE_MODEL_REVIEW_NOT_PNR',
        source_ref=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [TILE,'tools/uarch_model.py','tools/qwen_rom_enabled_capture_cone.py']},
        cone_sha256=hashlib.sha256(cone).hexdigest(),verbatim_logic_sha256=hashlib.sha256(logic).hexdigest(),
        verbatim_macro_instantiation_sha256=hashlib.sha256(macros).hexdigest(),model=model,
        mapped_gate_ready=True,PnR_ready=False,engine_RTL_modified=False,
        exact_scope='Full10-ROM/2560-bit enabled capture+selectors+bank mask/OR; no scalar representative downscale. Same source body and macro instantiation as current tile. Matrix arithmetic, KV and tree remain outside this cone.',
        physical_review_required=['Archimedes: place all10 real ROM views and2560 capture bits at actual output pins; carry macro LEF OBS/PG and10 unused output pins per ROM.',
          'Price512 capture-enable loads per bank and512 bank-mask loads per delayed selector, with buffering/replication/route tracks; do not fan out scalar control for free.',
          'Use current SS/FF mapped cells; include real macro slew, feedback mux/capture input pin loads, clock tree skew and uncertainty60/25 at833.333ps.',
          'Maxwell: retain MEM_EXTRA1 once, +55 separately. No new latency has been implemented; any added stage needs same-program cycle price and consumer/tag/control alignment before adoption.'],
        pin_OBS_PG_closed=False,actual_skew_ps=None,actual_pin_wire_cap_fF=None,adoption=False,
        second_position_queued=False,heavy_jobs_launched=0)
    (output/'preparation.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    return record


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    r=generate(a.output);print(json.dumps({'status':r['status'],'model':r['model']},indent=2))
    return 0


if __name__=='__main__':raise SystemExit(main())
