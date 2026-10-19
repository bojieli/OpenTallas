#!/usr/bin/env python3
"""Size candidate compaction and prove the ORIGINAL source rounding boundary.

No producer RTL is generated here. The only emitted HDL is a formal miter of
functions copied verbatim from the selected original producer source files.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess


def cell(lib, name):
    raw=lib.read_bytes()
    s=gzip.decompress(raw).decode() if lib.suffix=='.gz' else raw.decode()
    m=re.search(r'cell\s*\('+re.escape(name)+r'\)\s*\{',s)
    if not m:raise ValueError(name)
    b=s[m.start():];end=b.find('\n  cell (',1)
    if end!=-1:b=b[:end]
    a=float(re.search(r'\barea\s*:\s*([\d.]+)',b)[1])
    cap=None
    if 'DFFHQNx1' in name:
        c=b[b.index('pin (CLK)'):]
        cap=float(re.search(r'\bcapacitance\s*:\s*([\d.]+)',c)[1])
    return dict(name=name,area_um2=a,clock_cap_ff=cap,library=lib.name,
                sha256=hashlib.sha256(raw).hexdigest())


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True)
    ap.add_argument('--pdk',default=str(Path.home()/'.local/opentallas-pdk-asap7-platform/asap7/lib/NLDM'))
    a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True);pdk=Path(a.pdk)
    ff=cell(pdk/'asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib','DFFHQNx1_ASAP7_75t_R')
    nand=cell(pdk/'asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz','NAND2x1_ASAP7_75t_R')
    and2=cell(pdk/'asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz','AND2x2_ASAP7_75t_R')
    inv=cell(pdk/'asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz','INVx1_ASAP7_75t_R')
    mux=3*nand['area_um2']
    # Detailed cell network charge, not a measured mapped result or upper
    # bound on physical implementation (sizing/CTS/native overhead still open).
    counts=dict(mode_ff=64,source_data_copy_ff=4,source_enable_copy_ff=4,
                data_mux=512,upper_zero_and=512,select_inv=64,enable_mux=72)
    area=(72*ff['area_um2']+(512+72)*mux+512*and2['area_um2']+64*inv['area_um2'])
    rec=dict(schema='opentallas.s81.qf_compaction_candidates.v1',hardware_implemented=False,
        primitive_libraries=[ff,nand,and2,inv],
        uniform_static_wire=dict(preferred=True,new_ff=0,new_logic_cells=0,new_macro=0,
            added_clock_cap_ff=0,added_pipeline_edges=0,new_pin_count=0,
            payload_source_bits='bo[52+32*i+16 +:16], i0..31',
            payload_target_bits='q_data[16*i +:16]',
            header_representation='slot i is {original_header[16*i+:16],16b0}',
            header_sram_bits=3072,header_sram_rows=24,source_pairs_per_packet=4,
            source_format_proven=False,selected_data_fanout=1,
            q_words=258,word_ii=4,span_lower_bound=1029,
            old_span=258,minimum_added_edges=771,
            production_binding_changed=False,full_token_delta=None),
        receiver_partial_write=dict(new_macro_vs_qmem8_prototype=0,
            baseline_macros_per_slice=8,baseline_macro_area_per_slice_um2=4419.25632,
            baseline_physical_bits_per_slice=16384,useful_bits_per_slice=8192,
            raw_frame_header='explicit new Q format: type1 length256; old128 unchanged in legacy profile',
            payload_decode=dict(tile='f_idx[4:1]',head='{f_hdr[448],f_idx[7:5]}',phase='f_idx[0]'),
            old_payload_decode=dict(tile='f_idx[3:0]',head='{f_hdr[448],f_idx[6:4]}'),
            data='raw512 holds16 canonical BF16-in-FP32 values; upper16 selection yields256',
            bank_write='phase0 banks0..3; phase1 banks4..7; same rd_head and OLD native read',
            clock_delta=0,data_ff_delta=0,extra_control_state_ff=None,
            q_have='increment only qualified second half after matching first half',
            faults_needed=['GO with partial query','missing/mismatched first half',
                           'overlapping active read/write','unsupported format/len','wrong head identity'],
            control_area_um2=None,native_census_pending=True,
            physical_words=514,physical_word_ii=2,span_lower_bound=1027,
            minimum_added_edges=769,full_token_delta=None,
            reason_not_preferred='changes header payload count, parser indices, job stream and partial lifetime; wire profile preserves all'),
        in_xr=dict(preferred=False,enable_default=False,new_ff=72,new_macro=0,
            added_clock_cap_ff=72*ff['clock_cap_ff'],cell_network_counts=counts,
            modeled_stdcell_area_um2=area,physical_area_bound=False,
            added_pipeline_edges=0,lo_pairs_per_q_word=4,q_word_ii=4,
            combined_q_frame_words=258,diagnostic_all_compact_word_span=1029,
            mixed_raw_headers=2,mixed_compact_payload_words=256,
            mixed_source_lo_edges=1028,mixed_q_frame_span_lower_bound=1027,
            old_combined_q_frame_span=258,lower_bound_extra_edges=769,
            minimum_mode_switch_cfg_bubbles=3,
            two_entry_modeled_area_um2=2*area,all_driver_census_pending=True,
            new_select_load_bound=25,mode_validity='loaded with SEND cfg before first lo; resetdir/valid suppress all output before cfg',
            reset_added_control_ff=4,reset_native_load_proof=False,
            scope='64 group flags, 8 selected bits/group; four source copies drive16flags each',
            upper512_rule='explicit compact32BF16 format only; raw header/general B payload unchanged'),
        standalone=dict(new_data_ff=640,new_control_ff=None,minimum_ff_area_um2=640*ff['area_um2'],
            added_input_output_edges=2,q_word_ii=4,new_macro=0,
            whole_area_um2=None,reason_not_preferred='640new dataFF; header/bypass native cost not yet bounded'),
        missing=['wrong-mode/pair-count fault validation logic and exact clock-tree/physical cost',
                 'actual source row interleaving or independent coefficient-read path',
                 'header/mode control calendar and complete32word source identity',
                 'native all-driver reset/clock/depth and unchanged raw-mode equivalence',
                 'actual head-to-central gather and SRAM lifetime',
                 'production schedule admission with original deadlines'],
        qualification='MODEL_ONLY; no source hardware approval or token qualification')
    (out/'cost.json').write_text(json.dumps(rec,indent=2)+'\n')
    paths=['rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vs.sv',
           'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_rt.sv']
    texts=[Path(p).read_text() for p in paths]
    gp=Path('results/rtl/s81_qf_producer_1019/selected_source/hdc_golden.py')
    gs=gp.read_text()
    expected='rounded = (b + 0x7FFF + ((b >> 16) & 1)) >> 16'
    if expected not in gs or 'return from_bits((rounded << 16).astype(np.uint32))' not in gs:
        raise ValueError('golden conversion differs from proved bitvector specification')
    funcs=[re.search(r'function automatic \[31:0\] '+n+r'\(.*?endfunction',s,re.S)[0]
           for s,n in zip(texts,['bf16','fmt_d'])]
    mod='''module rounding_miter(input [31:0] x, input [511:0] h,
output ok, output raw_ok, output header_ok, output bad_bind_ok);
'''+ '\n'.join(funcs)+'''
wire [31:0] rounded = x + 32'h7fff + {31'd0,x[16]};
wire [31:0] golden = {rounded[31:16],16'd0};
wire [31:0] vs = bf16(x);
wire [31:0] cap = fmt_d(x,16'd0,2'd2,16'd0,1'b0,1'b0);
assign ok = vs == golden && cap == golden && vs[15:0] == 0 && cap[15:0] == 0;
assign raw_ok = x[31:16] == golden[31:16];
wire [1023:0] expanded;
wire [511:0] decoded;
genvar i;
generate for(i=0;i<32;i=i+1)begin:slot
assign expanded[32*i+:32] = {h[16*i+:16],16'd0};
assign decoded[16*i+:16] = expanded[32*i+16+:16];
end endgenerate
assign header_ok = decoded == h;
assign bad_bind_ok = expanded[511:0] == h;
endmodule
'''
    hdl=out/'rounding_miter.sv';hdl.write_text(mod)
    ledger=dict(source_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths},
        golden_source=str(gp),golden_source_sha256=hashlib.sha256(gp.read_bytes()).hexdigest(),
        proof='all32bit patterns incl NaN/Inf/subnormals/ties; original function exact arithmetic',
        compaction_precondition='actual qualified producer already wrote BF16-in-FP32; no new rounding here',
        missing_composition='actual wq_b return and QR capture/read wiring not proved by isolated function')
    (out/'rounding_source.json').write_text(json.dumps(ledger,indent=2)+'\n')
    for name,expr,verify in [('original_producer','ok',True),('raw_truncation_negative','raw_ok',False),
                           ('uniform_header_all512','header_ok',True),('old_binding_negative','bad_bind_ok',False)]:
        command=f'read_verilog -sv {hdl}; prep -top rounding_miter; flatten; sat -prove {expr} 1 -show x -show golden -show vs -show cap'
        if verify:command+=' -verify'
        p=subprocess.run(['yosys','-p',command],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (out/f'{name}.log').write_text(p.stdout)
        expected='SUCCESS!' if verify else 'model found: FAIL!'
        if p.returncode or expected not in p.stdout:raise RuntimeError(f'{name} unexpected {p.returncode}')
        print(name,expected)
    print('COMPACTION_MODEL_AREA_UM2',area,'CLOCK_CAP_FF',72*ff['clock_cap_ff'])

if __name__=='__main__':main()
