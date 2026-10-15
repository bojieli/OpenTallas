#!/usr/bin/env python3
"""Generate full 4x(N128/M32) static arithmetic from the native lane ABI.

The copied lane changes only fetch-tag stages. Arithmetic remains native RTL.
Run before builds; model is written before engine sources.
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'rtl/hbm_accel/generic/adapters/static_su/arithmetic'
RESULT = ROOT / 'results/arch/hbm_su_f2_static_1014/arithmetic'
SOURCE = ROOT / 'rtl/hdc/v41x/ot_hdc_v41x_vec_lane.sv'

# Exact 1742-bit raw controller ABI, msb first. cx_srcs is the lane's unused ABI input.
FIELDS = [('ld',1),('ld_bank',1),('ld_c',1200),('emit',1),('bank',1),
          ('o_v',24),('i_v',24),('no',24),('ni',24),('ls',4),('lvw',4),
          ('vb',120),('krow',24),('obase',24),('aibase',24),('aind',2),
          ('gsh',5),('cpair',1),('dst',2),('srcs',8),('cx_arnd',1),
          ('cx_arelu',1),('cx_amin',1),('cx_cclip',1),('cx_imm3',32),
          ('cp_m1',3),('cp_imm1',32),('cm_m1',3),('cm_m2',2),('cm_qm',3),
          ('cm_imm1',32),('ca_ad',3),('ca_imm2',32),('ci_sfu',3),('cs_sfu',3),
          ('cs_e1',3),('cs_imm2',32),('ce_e2',2),('ce_imm1',32),('co_rnd',1),('co_dst',2)]


def main():
    OUT.mkdir(parents=True,exist_ok=True); RESULT.mkdir(parents=True,exist_ok=True)
    assert sum(w for _,w in FIELDS)==1742
    model = dict(schema='hbm.su.static.arithmetic.v1', qualified=False,
        shape=dict(quarters=4,lanes_per_quarter=128,sfu_per_quarter=32,
                   full_lanes=1,sfu_only_lanes=127,light_lanes=384),
        replica_policy='KIND2 only global lane0; local lane0 in quarters1..3 is KIND1',
        clock_roots=dict(lane_stage_entries=4096,insertion_entries=2048,broadcast=64,scalar_side_external=True,scalar_side_native_roots_candidate=6,
                         broadcast_registered_bits_per_root=13936,
                         insertion_max_flops_per_root=5808,lane_sink_census='stage roots split; actual synthesized count and CTS remain unverified'),
        memory=dict(read_ports=2048,index_read_ports=512,word_bits=32,
                    read_bytes_per_cycle=8192,index_bytes_per_cycle=2048,
                    write_bytes_per_cycle=2048,response_offsets=[0,1,2],
                    backing_sram_macros=3072,backing_sram_bound=False),
        communication=dict(control_per_quarter_bits=1742,broadcast_edges=1,
                           operand_boundary_bits_per_cycle=65536,
                           output_boundary_bits_per_cycle=16384,
                           routing_tracks='requires actual pin/geometry allocation'),
        arithmetic=dict(fp32_multiplier_pipelines=2560,fp32_adder_pipelines=1024,
                        divider_lanes=128,exp_lanes=128,
                        max_vector_result_words_per_cycle=512),
        latency=dict(normal_extra_fetch_edges=2,gather_extra_fetch_edges=4,
                     nominal_light_emit_to_write_edges=23,
                     note='broadcast1 + native20 + fetch2; actual bench required'),
        area='unmeasured full native datapath; no physical fit claimed',
        model_status='sizing candidate; not throughput/physical qualification',
        native_lane_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest())
    (RESULT/'model.json').write_text(json.dumps(model,indent=2)+'\n')
    native=SOURCE.read_text().replace('module ot_hdc_v41x_vec_lane #(',
                                    'module ot_hbm_su_static_lane #(')
    native=native.replace('/* verilator no_inline_module */','/* verilator hier_block */')
    native=native.replace('parameter integer AW = 24,',
                          'parameter integer FETCH_EXTRA_EDGES = 2, // response edge offset: 0 raw macro, 2 pinned bank\n    parameter integer AW = 24,',1)
    # Delay F0 gather metadata before G1 for the actual sampled response offset.
    marker='    // ---- G1, G2:'
    pos=native.index(marker)
    text='''    // Pinned SRAM adds two index metadata edges before G1, not an address reinterpretation.
    wire fg_v, fg_g, fg_par, fg_cpair;
    wire [AW-1:0] fg_a, fg_b, fg_c, fg_d, fg_o;
    wire [7:0] fg_src;
    wire [4:0] fg_sh;
    reg [4:0] f_sh;
    always @(posedge clk) f_sh <= gsh_e;
    generate if (FETCH_EXTRA_EDGES > 0) begin:g_index_edge
        reg [FETCH_EXTRA_EDGES-1:0] valid;
        reg [5*AW+15:0] payload[0:FETCH_EXTRA_EDGES-1];
        integer ix;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) valid <= 0; else valid <= (valid << 1) | f_v;
        always @(posedge clk) begin
            payload[0] <= {f_g,f_par,f_cpair,f_a,f_b,f_c,f_d,f_o,f_src,f_sh};
            for(ix=1;ix<FETCH_EXTRA_EDGES;ix=ix+1)payload[ix]<=payload[ix-1];
        end
        assign fg_v=valid[FETCH_EXTRA_EDGES-1];
        assign {fg_g,fg_par,fg_cpair,fg_a,fg_b,fg_c,fg_d,fg_o,fg_src,fg_sh}=payload[FETCH_EXTRA_EDGES-1];
    end else begin:g_index_direct
        assign {fg_v,fg_g,fg_par,fg_cpair,fg_a,fg_b,fg_c,fg_d,fg_o,fg_src,fg_sh}=
               {f_v,f_g,f_par,f_cpair,f_a,f_b,f_c,f_d,f_o,f_src,f_sh};
    end endgenerate
'''
    native=native[:pos]+text+native[pos:]
    a=native.index(marker); b=native.index('    // ---- memory reads:',a)
    section=native[a:b]
    section=section.replace('    reg [4:0] f_sh;\n    always @(posedge clk) f_sh <= gsh_e;\n','')
    section=re.sub(r'\bf_(v|g|par|cpair|a|b|c|d|o|src|sh)\b',r'fg_\1',section)
    native=native[:a]+section+native[b:]
    a=native.index('    // tags of the read,'); b=native.index('    // ---- X:',a)
    native=native[:a]+'''    // Exact read-tag extension: x_a..d capture the actual external SRAM q.
    reg m_v, x_v;
    reg [AW-1:0] m_o, x_o;
    reg m_par, x_par;
    wire mf_v, mf_par;
    wire [AW-1:0] mf_o;
    generate if (FETCH_EXTRA_EDGES > 0) begin:g_fetch_edge
        reg [FETCH_EXTRA_EDGES-1:0] v;
        reg [AW:0] tag[0:FETCH_EXTRA_EDGES-1];
        integer fx;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) v <= 0; else v <= (v << 1) | mr_v;
        always @(posedge clk) begin
            tag[0] <= {g2_v ? g2_o : f_o, g2_v ? g2_par : f_par};
            for(fx=1;fx<FETCH_EXTRA_EDGES;fx=fx+1)tag[fx]<=tag[fx-1];
        end
        assign mf_v=v[FETCH_EXTRA_EDGES-1]; assign {mf_o,mf_par}=tag[FETCH_EXTRA_EDGES-1];
    end else begin:g_fetch_direct
        assign mf_v=mr_v;
        assign mf_o=g2_v ? g2_o : f_o;
        assign mf_par=g2_v ? g2_par : f_par;
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin m_v<=0; x_v<=0; end
        else begin m_v<=mf_v; x_v<=m_v; end
    end
    always @(posedge clk) begin
        m_o<=mf_o; m_par<=mf_par; x_o<=m_o; x_par<=m_par;
    end
    generate if (FETCH_EXTRA_EDGES < 0 || FETCH_EXTRA_EDGES > 2) begin:g_bad_fetch
        ot_su_response_offset_must_be_0_1_or_2 u_trap();
    end endgenerate
'''+native[b:]
    # Eight stage-clock pins and four insertion-line clock pins. All roots are
    # compiler-related 1:1 with phase0; no synchronizer or runtime scheduling.
    native=native.replace('input  wire              clk,',
                          'input wire [7:0] clk_stage,\n    input wire [3:0] clk_insert,',1)
    boundaries=[native.index('    // ---- M1 '),native.index('    // ---- M2 '),
                native.index('    // ---- AD '),native.index('    // ---- S '),
                native.index('    // ---- E1 '),native.index('    // ---- E2 '),
                native.index('    // ---- OUT')]
    segments=[];start=0
    for stage,end in enumerate(boundaries+[len(native)]):
        part=re.sub(r'\bclk\b',f'clk_stage[{stage}]',native[start:end])
        # Preserve named port identifiers .clk while changing their signals.
        part=part.replace(f'.clk_stage[{stage}](','.clk(')
        if stage==4:
            part=part.replace('ot_hdc_v41x_ins #(', 'ot_hbm_su_static_ins #(')
            # Only the insertion line changes clock vector; real arithmetic
            # uses the S arithmetic root, each metadata segment has its own.
            part=re.sub(r'(ot_hbm_su_static_ins[\s\S]*?u_l4\s*\(\s*)\.clk\(clk_stage\[4\]\)',
                        r'\1.clk(clk_insert)',part)
        segments.append(part);start=end
    native=''.join(segments)
    sfus=(ROOT/'rtl/hdc/v41x/ot_hdc_v41x_sfu.sv').read_text()
    ins=sfus[sfus.index('module ot_hdc_v41x_ins #('):]
    ins=ins[:ins.index('endmodule')+len('endmodule')]
    ins=ins.replace('module ot_hdc_v41x_ins #(', 'module ot_hbm_su_static_ins #(')
    ins=ins.replace('input  wire         clk,','input wire [3:0] clk,')
    ins=ins.replace('posedge clk','posedge clk[(p-1)/48]')
    (OUT/'ot_hbm_su_static_ins.sv').write_text('`timescale 1ns/1ps\n'+ins+'\n')
    (OUT/'ot_hbm_su_static_lane.sv').write_text('// Generated by tools/hbm_static/su_arith_generate.py; native arithmetic unchanged.\n'+native)
    ports='''input wire [4095:0] clk_lane, input wire [2047:0] clk_insert,\n input wire [511:0] rst_lane_n,
 input wire [63:0] clk_bcast, rst_bcast_n,
 input wire [6967:0] control,
 input wire [16383:0] vi_q,
 input wire [65535:0] rd_q,
 input wire [31:0] side_y,
 output wire side_v, output wire [31:0] side_x,\n output wire [2:0] side_fn, side_fn_out,
 output wire [511:0] vi_re, vm_we, kv_we, ro_v, fault, coll,
 output wire [12287:0] vi_addr, vm_waddr, kv_waddr,
 output wire [49151:0] rd_addr,
 output wire [2047:0] rd_re,
 output wire [4095:0] rd_src,
 output wire [16383:0] vm_wdata, kv_wdata, ro_x'''
    grid='''`timescale 1ns/1ps
`default_nettype none
// Full-shape wires-only cluster: all 512 native lane identities remain live.
// Each quarter control is compiler-rebased explicitly; no hidden address translation.
// All clock entries are independent physical roots with a common scheduled phase.
// Scalar native side pipe is external and belongs only to global lane0.
module ot_hbm_su_static_arithmetic #(parameter integer FETCH_EXTRA_EDGES=2, MLAT=3, ALAT=3, LEAF=0)(
 '''+ports+'''
);
 for(genvar b=0;b<64;b=b+1)begin:g_bcast
  // Eight actual replicas per root = 8*1742=13936 sinks, below 15000.
  reg [1741:0] ctl [0:7];
  for(genvar k=0;k<8;k=k+1)begin:g_replica
   always @(posedge clk_bcast[b] or negedge rst_bcast_n[b])
    if(!rst_bcast_n[b])ctl[k]<=0; else ctl[k]<=control[(b/16)*1742+:1742];
  end
 end
 for(genvar l=0;l<512;l=l+1)begin:g_lane
  localparam integer LOCAL=l%128;
  localparam integer KIND=(l==0)?2:(LOCAL<32)?1:0;
'''
    for name,w in FIELDS: grid+=f'  wire [{w-1}:0] c_{name};\n'
    grid+='  assign {'+','.join('c_'+n for n,_ in FIELDS)+'}=g_bcast[l/8].ctl[l%8];\n'
    # Keep low7 terms for 128 true local lanes. Other ABI terms have no identity bit.
    grid+='  wire [839:0] terms;\n  for(genvar s=0;s<5;s=s+1)begin:g_terms\n   assign terms[s*168+:168]=c_ld_c[s*240+:168];\n  end\n'
    grid+='  wire sv; wire [31:0] sx;\n  if(l==0)begin:g_side\n   assign side_v=sv; assign side_x=sx; assign side_fn=c_ci_sfu; assign side_fn_out=c_cs_sfu;\n  end\n'
    grid+='  ot_hbm_su_static_lane #(.LN(7),.KIND(KIND),.MLAT(MLAT),.ALAT(ALAT),.LEAF(LEAF),.FETCH_EXTRA_EDGES(FETCH_EXTRA_EDGES)) u_lane(\n'
    conns=['.clk_stage(clk_lane[l*8+:8])','.clk_insert(clk_insert[l*4+:4])','.rst_n(rst_lane_n[l])',".lane_id(11'(LOCAL))",'.cx_srcs(c_srcs)']
    conns += [f'.{n}(terms)' if n=='ld_c' else f'.{n}(c_{n})' for n,_ in FIELDS]
    for n,w in [('vi_q',32),('rd_q',128),('vi_re',1),('vm_we',1),('kv_we',1),('ro_v',1),('fault',1),('coll',1),('vi_addr',24),('vm_waddr',24),('kv_waddr',24),('rd_addr',96),('rd_re',4),('rd_src',8),('vm_wdata',32),('kv_wdata',32),('ro_x',32)]:
        conns.append(f'.{n}({n}[l*{w}+:{w}])')
    conns += ['.side_v(sv)','.side_x(sx)','.side_y(side_y)']
    grid+='   '+',\n   '.join(conns)+');\n end\nendmodule\n`default_nettype wire\n'
    (OUT/'ot_hbm_su_static_arithmetic.sv').write_text(grid)
    # A prior native-lane census remains valid only for byte-identical lane,
    # insertion and native arithmetic dependencies. The wires-only parent is
    # not instantiated in that per-KIND census.
    census_path=RESULT/'clock_census.json'
    if census_path.exists():
        census=json.loads(census_path.read_text())
        sources=census.get('source_sha256',{})
        relevant={p:h for p,h in sources.items()if not p.endswith('ot_hbm_su_static_arithmetic.sv')}
        if relevant and all((ROOT/p).exists() and hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
                            for p,h in relevant.items()):
            maximum=max(r['max_sink']for r in census['records'])
            model['clock_roots']['active_arithmetic_and_broadcast_roots']=64+sum(
                n*sum(v>0 for v in r['clock_sink_upper_bound'].values())
                for n,r in zip((384,127,1),census['records']))
            model['clock_roots']['max_native_register_sinks_per_root']=maximum
            model['clock_roots']['lane_sink_census']='Actual byte-matched Yosys per-KIND register census; no CTS'
            model['arithmetic']['register_bits_actual_census']=sum(
                n*sum(r['clock_sink_upper_bound'].values())for n,r in zip((384,127,1),census['records']))
            (RESULT/'model.json').write_text(json.dumps(model,indent=2)+'\n')


if __name__=='__main__': main()
