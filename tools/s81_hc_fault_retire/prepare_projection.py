#!/usr/bin/env python3
"""Extract byte-exact HC wrapper register shell around actual CSEQ+CPIN.

The replacement is an explicitly declared CONTROL-ONLY boundary vehicle:
writer completion and registered CCF fault are external stimuli. No HC
arithmetic, SRAM result or whole-engine numerical qualification is claimed.
"""
from pathlib import Path
import argparse, hashlib, json
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
src=Path('rtl/dsrom_sys/s81_suhc/dsfd_sp_hc_c.sv');s=src.read_text();start=s.index('    dsfd_sp_hc #(');end=s.index('    always @(posedge ck[0] or negedge rn)',start)
body='''
    // DECLARED control-probe boundaries; no arithmetic/memory substitute is qualified.
    wire ncv, ndv, ninp, nflt, nonl, nypop; wire [83:0] ncd; wire [7:0] ndt;
    wire [1:0] nrqv,nrsv; wire [27:0] nrqr; wire [1023:0] nrsd;
    wire [3:0] nfcode;
    ot_s81_hc_cpin u_pin(.cck(ck[0]),.crs(rn),.sk(ck[0]),.srs(rn),
      .c_cmd_v(cv_q),.c_cmd_d(cd_q),.c_done_v(dv),.c_done_tag(dt),.inp(1'b1),
      .rq_v(rq_v),.rq_row(rq_row),.rs_v(rs_v),.rs_d(rs_d),.flt(flt),.online(onl),.fcode(fcode),
      .y_v(1'b0),.y_rdy(y_rdy),.y_s(2560'd0),.yacc_w(),.yacc_e(),
      .n_cmd_v(ncv),.n_cmd_d(ncd),.n_done_v(ndv),.n_done_tag(ndt),.n_inp(ninp),
      .n_rq_v(nrqv),.n_rq_row(nrqr),.n_rs_v(nrsv),.n_rs_d(nrsd),.n_flt(nflt),.n_online(nonl),.n_fcode(nfcode),
      .n_yacc(),.n_y(),.n_ypop(nypop));
    ot_s81_hc_cseq #(.NG(256),.D(5120),.PIPE(1),.DW(5)) u_seq(
      .cck(ck[0]),.crs(rn),.sk(ck[0]),.srs(rn),.n_cmd_v(ncv),.n_cmd_d(ncd),
      .n_done_v(ndv),.n_done_tag(ndt),.n_inp(ninp),.n_rq_v(nrqv),.n_rq_row(nrqr),.n_rs_v(nrsv),.n_rs_d(nrsd),
      .n_flt(nflt),.n_online(nonl),.n_fcode(nfcode),.n_yacc(1'b0),.n_ypop(nypop),
      .w_flt(1'b0),.e_flt(1'b0),.w_fv(),.e_fv(),.c_fv(),.w_fd(),.e_fd(),.c_fd(),
      .ngo(),.t_ssv(1'b0),.t_ss(32'd0),.t_flt(1'b0),.j_v(),.kind(),.base(),.f_q(),.f_y(),.j_end(),.fault(),.j_civ(),
      .x_wdone(writer_boundary),.x_pob(1'b0),.x_f1(1'b0),.x_f4(1'b0),.c_yfl(fault_boundary));
    assign wq_v=0,wq_row=0,wq_mask=0,wq_d=0;
    assign t_tf0=0,t_tf1=0,t_tf2=0;
'''
projection=s[:start]+body+s[end:];projection=projection.replace('module dsfd_sp_hc_c #(', 'module ot_hc_fault_control_projection #(',1)
projection=projection.replace('    output wire [TFW-1:0]', '    input wire fault_boundary,writer_boundary,\n    output wire [TFW-1:0]',1)
(a.out/'hc_control_projection.sv').write_text(projection)
(a.out/'projection.json').write_text(json.dumps(dict(source=str(src),sha256=hashlib.sha256(s.encode()).hexdigest(),
 replacement_start_byte=start,replacement_end_byte=end,unchanged_suffix_sha256=hashlib.sha256(s[end:].encode()).hexdigest(),
 wrapper_command_done_status_reset_shell='unchanged text except module rename and added explicit boundary input ports',
 actual_instantiated=['ot_s81_hc_cseq','ot_s81_hc_cpin','ot_s81_engine_adapter','ot_async_fifo'],
 omitted=['HC arithmetic/SRAM/write datapath; writer completion is declared input boundary','CCF fault producer; registered output boundary injected'],
 native_qualified=False,numerical_qualified=False),indent=2)+'\n')
