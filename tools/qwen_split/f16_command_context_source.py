"""Frozen-width F16 identity transport using SU-only command bits111:90.

The accepted playhead start owns its immutable {stage,token identity}. Actual
chosen playhead ru publishes those bits in the same existing SU command output
register. Every non-SU command bit and every SU functional decode bit is retained.
"""
import argparse,hashlib,json,re
from pathlib import Path
def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"Expected one source anchor, got {text.count(old)}: {old}")
    return text.replace(old, new)


def generate(cal_path,gi_path,slice_path,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    original=Path(cal_path).read_text()
    cal=replace_once(original,'module qfd_dv_cmd_cal_mu #(', 'module qfd_dv_cmd_cal_mu_f16 #(')
    cal=replace_once(cal,'    parameter integer MUT = 0,','    parameter integer F16_CONTEXT = 0,\n    parameter integer MUT = 0,')
    cal=replace_once(cal,'    input  wire          start,','    input wire [15:0] start_epoch,\n    input  wire          start,')
    declaration="""    // Reuse the existing accepted-start pst stage bank; capture token identity
    // at the identical accepted nonempty-start edge. Payload is guarded by pst/run.
    reg [15:0] f16_epoch [0:NU-1];
    integer f16_u;
    initial if(F16_CONTEXT!=0 && (NU>4 || (NU>1 && PIDX_STRIDE!=128)))
      $error("F16 context needs <=4 users and actual PIDX128 relocation");
    always @(posedge ck)
      for(f16_u=0;f16_u<NU;f16_u=f16_u+1)
        if(go_u[f16_u]&&!start_bad&&g_cnt_nz)
          f16_epoch[f16_u]<=boot_go?16'd0:start_epoch;
"""
    cal=replace_once(cal,'    // ================================================================ sequential',declaration+'    // ================================================================ sequential')
    cal=replace_once(cal,'                    cmd <= rc;',"""                    // SU consumes PC[12:4], valid/kind[3:0], target[115:112].
                    // Bits111:90 carry stage6/token16 only for real external SU.
                    cmd <= (F16_CONTEXT!=0 && i_kind==3'd1)
                      ? {rc[115:112],pst[ru],f16_epoch[ru],rc[89:0]} : rc;""")
    # Keep frozen selector identities private to this distinct source variant.
    helpers=set(re.findall(r'module\s+(qfd_calpipe_\w+)',cal))
    for helper in helpers:cal=re.sub(r'\b'+re.escape(helper)+r'\b',helper+'_f16',cal)
    gi=Path(gi_path).read_text();gi=gi[:re.search(r'(?m)^endmodule\b',gi).end()]+'\n'
    gi=replace_once(gi,'module qfd_tt_ctlm_dv_gi_hp13 #(', 'module qfd_tt_ctlm_dv_gi_hp13_f16 #(')
    gi=replace_once(gi,'    qfd_dv_cmd_cal_mu #(', '    qfd_dv_cmd_cal_mu_f16 #(.F16_CONTEXT(F16WTN), ')
    gi=replace_once(gi,'        .start(u_start), .stage(u_stage)', '        .start_epoch(u_tokid), .start(u_start), .stage(u_stage)')
    sl=Path(slice_path).read_text()
    if sl.count('.p_re(c_su), .p_idx(cmd_q[12:4])')!=1:raise ValueError('actual PROG request differs')
    sl=replace_once(sl,'module qfd_dv_slice2 #(', 'module qfd_dv_slice2_f16cmd #(')
    sl=replace_once(sl,'    input  wire [115:0]   cmd_i,','    output wire [37:0] f16_issue_o,\n    input  wire [115:0]   cmd_i,')
    anchor="    // SU issue: the program word answers 2 edges after the command's pin register"
    sl=replace_once(sl,anchor,"""    qfd_dv_f16_issue_tap u_f16_issue (
      .ck(ck),.rst_n(rst),.program_re(c_su),.program_pidx(cmd_q[12:4]),
      .slice_id(sid_q),.command_context(cmd_q[111:90]),.observation(f16_issue_o));
"""+anchor)
    rows={}
    for name,s in [('qfd_dv_cmd_cal_mu_f16.sv',cal),('qfd_tt_ctlm_dv_gi_hp13_f16.sv',gi),('qfd_dv_slice2_f16cmd.sv',sl)]:
      (out/name).write_text(s);rows[name]=hashlib.sha256(s.encode()).hexdigest()
    return dict(sources={str(p):hashlib.sha256(Path(p).read_bytes()).hexdigest()for p in [cal_path,gi_path,slice_path]},outputs=rows,context_bank_bits=64,command_width=116,command_edges_added=0,context_field='SU-only cmd[111:90]',scope='Source candidate; full selected parent/LP/native/GEN binding remains required')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cal',required=True);p.add_argument('--gi',required=True);p.add_argument('--slice',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    print(json.dumps(generate(a.cal,a.gi,a.slice,a.out),indent=2))
