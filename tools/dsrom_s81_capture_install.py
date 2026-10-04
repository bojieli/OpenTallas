"""Added-only native spine installer; enclosing top owns real VM accept wiring.

No changes to original source or return tree. Returned ports MUST be threaded
by the selected Arch enclosing top; no automatic tied ready/ACK/fence.
"""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
LEAF='rtl/dsrom_sys/rd64_capture/ot_dsrom_rd64_vm_capture.sv'

def replace_once(s,old,new):
    if s.count(old)!=1:raise ValueError('native source anchor not unique: '+old[:70])
    return s.replace(old,new,1)

def install(spine_source,out):
    source=Path(spine_source);original=source.read_text();s=original
    s=replace_once(s,'parameter integer R = 2,','parameter integer CAPTURE_ENABLE = 0,\n    parameter integer CAPTURE_CAPACITY = 1,\n    parameter integer CAPTURE_VM_ALWAYS_ACCEPT = 0,\n    parameter integer R = 2,')
    s=replace_once(s,'input  wire              go,','''// Source-owned immutable per-root phase output manifest, counts include positions.
    input wire [R*19-1:0] capture_root_rows,
    input wire [46:0] capture_identity,
    input wire capture_reset_request,
    input wire [R-1:0] capture_vm_accept,
    output wire capture_live, capture_drained, capture_fault,
    input  wire              go,''')
    for name in ('w_we','w_addr','w_data'):
        # Native OFF register path retains exactly its original declaration.
        import re
        pattern=r'(output )reg(\s+\[[^\n]+\]\s+'+name+r',)'
        s,n=re.subn(pattern,r'\1wire\2',s);assert n==1,name
    s=replace_once(s,'assign ready = st == S_IDLE;','assign ready = st == S_IDLE && (!CAPTURE_ENABLE || cap_ready);')
    s=replace_once(s,'assign idle = st == S_IDLE;','assign idle = st == S_IDLE && (!CAPTURE_ENABLE || cap_idle);')
    s=replace_once(s,'S_IDLE: if (go) begin','S_IDLE: if (go && ready) begin')
    s=replace_once(s,"else rows_left <= rows_left - 19'($countones(r_v));","else rows_left <= rows_left - 19'($countones(CAPTURE_ENABLE ? (cap_we & capture_vm_accept) : r_v));")
    s=replace_once(s,"S_RUN: if (rows_left == 19'd0 && !sm_run && !ld_run) begin","S_RUN: if (rows_left == 19'd0 && !sm_run && !ld_run && (!CAPTURE_ENABLE || capture_drained)) begin")
    # Move original row register body to distinct legacy block; no double capture.
    start=s.index('            // rows\n');end=s.index('\n        end\n    end\n    // buffers',start)
    rows=s[start:end].replace('w_we','legacy_we').replace('w_addr','legacy_addr').replace('w_data','legacy_data')
    rows=rows.replace("if (r_e[kr]) fault <= 1'b1;",'')
    s=s[:start]+"            if (CAPTURE_ENABLE ? capture_fault : (|(r_e & r_v))) fault <= 1'b1;"+s[end:]
    s=s.replace("w_we <= {R{1'b0}};", "") # legacy reset now in its own block
    insert='''
    wire cap_ready,cap_idle;
    wire [R-1:0] cap_we;
    wire [R*30-1:0] cap_addr;
    wire [R*32-1:0] cap_data;
    reg [R-1:0] legacy_we;
    reg [R*VAW-1:0] legacy_addr;
    reg [R*32-1:0] legacy_data;
    assign w_we=CAPTURE_ENABLE ? cap_we : legacy_we;
    assign w_data=CAPTURE_ENABLE ? cap_data : legacy_data;
    genvar cg;generate for(cg=0;cg<R;cg=cg+1)begin:capture_address
      assign w_addr[cg*VAW +:VAW]=CAPTURE_ENABLE ? cap_addr[cg*30 +:VAW] : legacy_addr[cg*VAW +:VAW];
    end endgenerate
    ot_dsrom_rd64_vm_capture #(.ENABLE(CAPTURE_ENABLE),.ROOTS(R),
      .CAPACITY(CAPTURE_CAPACITY),.VM_AW(VAW),.VM_ALWAYS_ACCEPT(CAPTURE_VM_ALWAYS_ACCEPT)) u_capture (
      .clk(clk),.rst_n(rst_n),.reset_request(capture_reset_request),
      .phase_valid(go && st==S_IDLE),.phase_ready(cap_ready),
      .phase_identity(capture_identity),.phase_id(10'(i_ph)),.phase_root_rows(capture_root_rows),
      .phase_obase(30'(i_obase)),.phase_ops(30'(i_ops)),.phase_np(i_np),.phase_fmt(i_fmt),
      .phase_rsplit(phrom[{i_ph,1'b1}][15:0]),
      .phase_fp32_low(phrom[{i_ph,1'b0}][62]),.phase_fp32_high(phrom[{i_ph,1'b0}][63]),
      .r_valid(r_v),.r_error(r_e),.r_row(r_row),.r_pos(r_pos),.r_fp32(r_fp32),.r_bf16(r_bf16),
      .vm_valid(cap_we),.vm_accept(capture_vm_accept),.vm_addr(cap_addr),.vm_data(cap_data),
      .vm_row(),.vm_pos(),.held_identity(),.held_phase(),.phase_live(capture_live),
      .phase_idle(cap_idle),.phase_drained(capture_drained),.fault(capture_fault));
    always @(posedge clk or negedge rst_n)begin
      if(!rst_n)legacy_we<={R{1'b0}};
      else if(!CAPTURE_ENABLE)begin
LEGACY_ROWS
      end
    end
'''.replace('LEGACY_ROWS',rows)
    s=replace_once(s,'    // buffers\n',insert+'    // buffers\n')
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    dest=out/source.name;dest.write_text(s)
    receipt=dict(original=str(source),original_sha256=hashlib.sha256(original.encode()).hexdigest(),
      generated=str(dest),generated_sha256=hashlib.sha256(s.encode()).hexdigest(),
      sources=[str(ROOT/LEAF),str(dest)],top_ports=['capture_root_rows','capture_identity','capture_reset_request',
      'capture_vm_accept','capture_live','capture_drained','capture_fault'],
      required_parent_wiring='Actual VM commit same edge; immutable emitted per-root count manifest; coordinated cold reset only.',
      enclosing_top_installed=False,functional_gate=False,physical_gate=False)
    (out/'source_join.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--spine',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();print(json.dumps(install(a.spine,a.out),indent=2))
