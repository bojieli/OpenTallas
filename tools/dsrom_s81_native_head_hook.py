"""Emit one additive selected core/adapter hookup; originals stay untouched."""
from pathlib import Path
import argparse,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
CORE=ROOT/'rtl/dsrom_sys/s81_capture_parent/ot_hdc_core_v41x.sv'
ADAPT=ROOT/'rtl/dsrom_sys/s81_capture_parent/ot_v41_rom_adapt.sv'

def emit(out):
    out.mkdir(parents=True,exist_ok=False)
    a=ADAPT.read_text();c=CORE.read_text()
    a=a.replace('parameter integer S81_CAPTURE=0,','parameter integer S81_CAPTURE=0,\n    parameter integer OPT_NATIVE_HEAD=0,')
    a=a.replace('m_round && !m_amax && !m_mmode;',"!m_mmode && ((m_round && !m_amax) || (OPT_NATIVE_HEAD && m_amax && !m_round && m_k==NW'(5120) && m_split==0));")
    a=a.replace("if (!m_ok) fault <= 1'b1;\n                        st <= S_LOOK;","if (!m_ok) fault <= 1'b1;\n                        st <= (OPT_NATIVE_HEAD && !m_ok) ? S_IDLE : S_LOOK;")
    a=a.replace("s_ph <= hit_p; st <= S_GO;","s_ph <= hit_p; st <= (OPT_NATIVE_HEAD && (!hit || fault)) ? S_IDLE : S_GO;")
    c=c.replace('parameter integer S81_CAPTURE=0,','parameter integer S81_CAPTURE=0,\n    parameter integer OPT_NATIVE_HEAD=0,')
    c=c.replace('input wire capture_command_ready,','input wire capture_command_ready,') # header remains source-owned
    anchor='    input wire [ROM_R*19-1:0] capture_root_rows,'
    assert anchor in c
    ports='''    input wire head_up_valid, head_up_last,
    output wire head_up_ready,
    input wire [511:0] head_up_data,
    input wire [46:0] head_up_identity,
    output wire head_dn_valid, head_dn_last,
    input wire head_dn_ready,
    input wire head_final_valid,
    output wire head_final_ready,
    input wire [511:0] head_final_data,
    input wire [46:0] head_final_identity,
    output wire [511:0] head_dn_data,
    output wire [46:0] head_dn_identity,
'''
    c=c.replace(anchor,ports+anchor)
    c=c.replace('localparam integer EAM = (X_ME != 0) ? 1 : 0;','localparam integer EAM = ((X_ROM != 0 && OPT_NATIVE_HEAD) || X_ME != 0) ? 1 : 0;')
    c=c.replace('    wire rom_m_go = e_go[1];','''    wire rom_m_go = e_go[1];
    wire head_busy,head_seen,head_fault;
    wire [NW-1:0] head_idx;
    wire [31:0] head_val;
    wire head_any;
    generate if(X_ROM && OPT_NATIVE_HEAD) begin:g_native_head
        initial if(MP!=1 || NSLOT!=1 || !S81_CAPTURE) $fatal(1,"minimum native head requires selected MP1/NSLOT1 capture path");
        ot_dsrom_s81_head_amax #(.R(ROM_R),.AW(AW),.NW(NW),.RANK(RANK)) u_head (
            .clk(clk),.rst_n(rst_n),.start(rom_m_go && me_amax),
            .identity(capture_identity),.nout(me_nout),.obase(me_obase*AW'(W)),
            .write_valid(rom_we),.write_accept(capture_vm_accept),.write_address(rom_waddr),.write_bits(rom_wdata),
            .upstream_valid(head_up_valid),.upstream_ready(head_up_ready),.upstream_data(head_up_data),
            .upstream_last(head_up_last),.upstream_identity(head_up_identity),
            .downstream_valid(head_dn_valid),.downstream_ready(head_dn_ready),.downstream_data(head_dn_data),
            .downstream_last(head_dn_last),.downstream_identity(head_dn_identity),
            .final_valid(head_final_valid),.final_ready(head_final_ready),.final_data(head_final_data),.final_identity(head_final_identity),
            .busy(head_busy),.result_seen(head_seen),.am_idx(head_idx),.am_val(head_val),.am_any(head_any),.fault(head_fault));
    end else begin:g_no_native_head
        assign head_busy=0;assign head_seen=0;assign head_fault=0;assign head_idx=0;assign head_val=0;assign head_any=0;
        assign head_final_ready=0;assign head_up_ready=0;assign head_dn_valid=0;assign head_dn_last=0;assign head_dn_data=0;assign head_dn_identity=0;
    end endgenerate''')
    c=c.replace('assign e_ready[1] = rom_ready_w;', 'assign e_ready[1] = rom_ready_w && !head_busy;')
    c=c.replace('assign e_idle[1] = rom_idle_w; assign e_fault[1] = 1\'b0;',"assign e_idle[1] = rom_idle_w && !head_busy; assign e_fault[1] = head_fault;")
    c=c.replace('assign e_am_idx[1*MP*NW +: MP*NW] = 0;',"assign e_am_idx[1*MP*NW +: MP*NW] = OPT_NATIVE_HEAD ? head_idx : 0;",1)
    c=c.replace('assign e_am_val[1*MP*32 +: MP*32] = 0; assign e_am_any[1*MP +: MP] = 0;',"assign e_am_val[1*MP*32 +: MP*32] = OPT_NATIVE_HEAD ? head_val : 0; assign e_am_any[1*MP +: MP] = OPT_NATIVE_HEAD ? head_any : 0;",1)
    c=c.replace('.S81_CAPTURE(S81_CAPTURE),.AW(AW)', '.OPT_NATIVE_HEAD(OPT_NATIVE_HEAD),.S81_CAPTURE(S81_CAPTURE),.AW(AW)',1)
    (out/CORE.name).write_text(c);(out/ADAPT.name).write_text(a)
    (out/'source_diff_receipt.json').write_text(json.dumps({'original_source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [CORE,ADAPT]},'selected_source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.sv')},'opt_in_default':False,'ME_head_output_format':'existing s_fmt1 FP32 unchanged','no_new_dot':True},indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);emit(p.parse_args().out)
