import sys, subprocess
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import dsrom_s81_capture_parent as C
import dsrom_s81_system_sources as S
import dsrom_s81_capture_parent_model as M


def test_full_selected_ports_and_real_retirement(tmp_path):
    paths=[ROOT/S.CORE,ROOT/S.TILE,ROOT/'rtl/dsrom_sys/c8/ot_chip_v41x_die_owner_safe_c8.sv',
           ROOT/'rtl/dsrom_sys/c8/ot_v41_rt_die_l20_c8.sv',ROOT/C.SPINE,ROOT/C.ADAPTER]
    before={p:p.read_bytes() for p in paths}
    b=SimpleNamespace(stages=81,pairs=2417,inventory={'TP':4},contract={'return_contract':{'RD':64}},native_sources=lambda _:paths)
    r=S.install(b,'unused',tmp_path/'selected',capture=True,accepted_pop=True)
    roles={p.name:p.read_text() for p in r['sources']}
    for name in [p.name for p in paths[:4]]:
        s=roles[name]
        for port in ['capture_root_rows','capture_identity','capture_reset_request','capture_vm_accept','capture_live','capture_drained','capture_fault']:
            assert port in s
        assert 'parameter integer S81_CAPTURE=0' in s
    assert '.VM_AW(19)' in roles['ot_v41_spine_w17w10.sv']
    assert 'CAPTURE_S81_PROFILE(S81_CAPTURE)' in roles['ot_hdc_core_v41x.sv']
    adapter=roles['ot_v41_rom_adapt.sv']
    assert 'S81_CAPTURE ? capture_command_ready : s_ready' in adapter
    assert 'S_GO: if (s_ready)' in adapter # Never substitute idle for phase GO.
    die=roles['ot_chip_v41x_die_owner_safe_c8.sv']
    assert '!capture_live && capture_drained && !capture_fault' in die
    assert 'assign c8_write_quiet=capture_visibility_quiet' in die
    assert 'S81_VM_COMMIT' in roles['ot_v41_rt_die_l20_c8.sv']
    assert r['capture_added_idle_edges_per_executed_phase']==2
    assert r['parameters']['S81_CAPTURE']==1 and not r['physical_admission']
    assert all(p.read_bytes()==v for p,v in before.items())


def test_model_prices_all_last_writer_checks():
    m=M.model()
    assert m['last_write_wins']['total_19bit_equality_comparators_upper_bound']==73792
    assert m['all_rank_raw_state_bits']==16527*324
    assert m['quota_ROM_added_bits']==0 and m['physical']['area_credit']==0


def test_actual_assignment_accept_and_warm_debt(tmp_path):
    # Executable actual visibility cone, copied verbatim from the parent source
    # generator, connected to unchanged full-R128 capture RTL. No return tree,
    # arithmetic substitute, system/token/timing claim, or physical SRAM claim.
    die=C.hook('die',(ROOT/'rtl/dsrom_sys/c8/ot_chip_v41x_die_owner_safe_c8.sv').read_text().replace('    parameter integer C8_PUBLICATION=0,','    parameter integer IDX_DRAIN_LOOKAHEAD=0,\n    parameter integer C8_PUBLICATION=0,'))
    predicate=die[die.index('wire capture_visibility_quiet='):die.index('assign c8_write_quiet=capture_visibility_quiet')]
    predicate=predicate.replace('negedge rn','negedge rst_n').replace('if(!rn)','if(!rst_n)')
    source=BENCH.replace('ACTUAL_ACCEPT_LOGIC',C.VM_ACCEPT).replace('ACTUAL_RETIREMENT_PREDICATE',predicate)
    sv=tmp_path/'bench.sv';sv.write_text(source)
    obj=tmp_path/'test.vvp'
    cmd=['iverilog','-g2012','-s','tb','-o',str(obj),str(sv),str(ROOT/'rtl/dsrom_sys/rd64_capture/ot_dsrom_rd64_vm_capture.sv')]
    build=subprocess.run(cmd,text=True,capture_output=True)
    (tmp_path/'compile.log').write_text(build.stdout+build.stderr)
    assert build.returncode==0,build.stderr
    run=subprocess.run(['vvp',str(obj)],text=True,capture_output=True)
    (tmp_path/'run.log').write_text(run.stdout+run.stderr)
    assert run.returncode==0 and 'PASS S81 actual VM accept/reset 5 cases' in run.stdout,run.stdout+run.stderr


BENCH=r'''
module tb;
localparam AW=30,VM_AW=19,ROM_R=128,G=4,W=16,SW=8,SUN=256;
localparam S81_CAPTURE=1,X_ROM=1;
reg clk=0,rst_n=0,capture_reset_request=0,phase_valid=0;
always #5 clk=~clk;
reg [127:0] rv=0,re=0;reg [2047:0] row=0,bf=0;reg [383:0] pos=0;
reg [4095:0] fp=0;reg [2431:0] quota=0;
wire [127:0] rom_we,capture_vm_accept;wire [3839:0] rom_waddr;wire [4095:0] rom_wdata;
wire ready,live,drained,fault;wire [46:0] identity;
wire capture_live=live,capture_drained=drained,capture_fault=fault;
ACTUAL_RETIREMENT_PREDICATE
reg [127:0] rom_duplicate=0;
reg [G-1:0] vw_me_we=0;reg [G*W-1:0] vw_me_mask=0;reg [G*AW-1:0] vw_me_addr=0;
reg [SW-1:0] vw_su_we=0,vw_rd_we=0;reg [SW*AW-1:0] vw_su_addr=0,vw_rd_addr=0;
reg [SUN-1:0] xs_vm_we=0;reg [SUN*AW-1:0] xs_vm_waddr=0;
reg [SUN/8-1:0] xs_res_we=0;reg [SUN/8*AW-1:0] xs_res_addr=0;
reg vw_xe_we=0,ww_q_we=0,ww_x_we=0,xa_we=0;
reg [AW-1:0] vw_xe_addr=0,ww_q_addr=0,ww_x_addr=0;
reg [31:0] ww_q_mask=0,ww_x_mask=0;
reg [VM_AW-5:0] xa_waddr=0;reg [3:0] xb_we4=0;reg [4*(VM_AW-4)-1:0] xb_waddr4=0;
reg [31:0] vm[0:(1<<VM_AW)-1];
ACTUAL_ACCEPT_LOGIC
// Literal original ROM then XU assignment precedence (the tested competitor).
always @(posedge clk)begin
 for(integer q=0;q<ROM_R;q=q+1)if(rom_we[q]&&capture_vm_accept[q])vm[rom_waddr[q*AW+:VM_AW]]<=rom_wdata[q*32+:32];
 if(vw_xe_we)vm[vw_xe_addr[VM_AW-1:0]]<=32'h12345678;
end
ot_dsrom_rd64_vm_capture #(.ENABLE(1),.ROOTS(128),.CAPACITY(1),.VM_AW(19),.VM_ALWAYS_ACCEPT(1)) dut (
 .clk(clk),.rst_n(rst_n),.reset_request(capture_reset_request),.phase_valid(phase_valid),.phase_ready(ready),
 .phase_identity(47'h123456789),.phase_id(10'd9),.phase_root_rows(quota),.phase_obase(30'd16),.phase_ops(30'd256),.phase_np(3'd0),.phase_fmt(2'd1),.phase_rsplit(16'd0),.phase_fp32_low(1'b1),.phase_fp32_high(1'b1),
 .r_valid(rv),.r_error(re),.r_row(row),.r_pos(pos),.r_fp32(fp),.r_bf16(bf),
 .vm_valid(rom_we),.vm_accept(capture_vm_accept),.vm_addr(rom_waddr),.vm_data(rom_wdata),.vm_row(),.vm_pos(),
 .held_identity(identity),.held_phase(),.phase_live(live),.phase_idle(),.phase_drained(drained),.fault(fault));
task tick;begin @(posedge clk);#1;end endtask
task cold_new_diagnostic;begin
 @(negedge clk);rst_n=0;rv=0;phase_valid=0;capture_reset_request=0;vw_xe_we=0;tick;
 @(negedge clk);rst_n=1;quota=0;quota[0+:19]=1;tick;
 @(negedge clk);if(!ready)$fatal(1,"initial admission blocked");if(!capture_visibility_quiet)$fatal(1,"SU-only zero-debt retirement blocked");phase_valid=1;tick;
 @(negedge clk);phase_valid=0;end endtask
initial begin
 cold_new_diagnostic;
 rv[0]=1;row[0+:16]=0;fp[0+:32]=32'h80000000;tick;
 @(negedge clk);rv=0;if(!capture_vm_accept[0])$fatal(1,"real VM write refused");tick;
 if(vm[16]!==32'h80000000||identity!==47'h123456789||drained)$fatal(1,"raw/identity/earlydrain");
 tick;if(!drained||live||fault)$fatal(1,"actual commit not drained");
 // Later XU writer overwrites this address: no ROM credit, sticky fault.
 cold_new_diagnostic;rv[0]=1;fp[0+:32]=32'hffffffff;tick;
 @(negedge clk);rv=0;vw_xe_we=1;vw_xe_addr=16;#1;
 if(capture_vm_accept[0]||!fault)$fatal(1,"overwritten assignment credited");tick;
 if(drained||vm[16]!==32'h12345678)$fatal(1,"overwrite order/drain changed");
 // Warm reset after accepted but undelivered work cannot erase its owner/debt.
 cold_new_diagnostic;rv[0]=1;fp[0+:32]=32'h7f800000;tick;
 @(negedge clk);rv=0;capture_reset_request=1;tick;
 if(dut.count[0]!==1||dut.received[0]!==1||dut.committed[0]!==0||!live||drained||!fault)$fatal(1,"warm reset erased debt");
 @(negedge clk);capture_reset_request=0;tick;
 if(capture_visibility_quiet||!fault||drained||ready||dut.count[0]!==1)$fatal(1,"warm quarantine released itself");
 // Source same-edge writers other than XU must likewise refuse positive ACK.
 cold_new_diagnostic;rv[0]=1;tick;
 @(negedge clk);rv=0;xs_vm_we[0]=1;xs_vm_waddr[0+:AW]=16;#1;
 if(capture_vm_accept[0])$fatal(1,"SU overwrite credited");xs_vm_we=0;
 xb_we4[0]=1;xb_waddr4[0+:VM_AW-4]=1;#1;
 if(capture_vm_accept[0])$fatal(1,"collective overwrite credited");xb_we4=0;
 $display("PASS S81 actual VM accept/reset 5 cases");$finish;
end
endmodule
'''
