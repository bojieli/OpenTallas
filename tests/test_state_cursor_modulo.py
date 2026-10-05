"""Exercise transactional ring cursor reduction against Python integer arithmetic."""
from pathlib import Path
import random
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]

@pytest.mark.skipif(shutil.which('iverilog') is None, reason='iverilog unavailable')
@pytest.mark.parametrize('simulator', ['iverilog', 'verilator'])
def test_ring_cursor_commit_and_cancel(tmp_path, simulator):
    rng = random.Random(831)
    cases = [(c, c-1 if c else 0, s) for c in
             [0, 1, 2, 3, 7, 32, 513, 1024, 65535, 0x80000000, 0xffffffff]
             for s in [1, 2, 31, 0x80000000, 0xffffffff]]
    cases += [(rng.randrange(1, 2**32), rng.randrange(2**32), rng.randrange(1, 2**32))
              for _ in range(200)]
    calls = []
    for cap, cur, span in cases:
        expected = (cur+span) % cap if cap else cur
        rows = min(cap, span)
        steps = 35 if cap and cap & (cap-1) else 1
        calls.append(f"run_case(32'd{cap},32'd{cur},32'd{span},32'd{expected},32'd{rows},{steps});")
    bench = r'''module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,clear=0,op_valid=0,commit_all=0,discard_all=0;
reg [7:0] op_sub=0;reg [31:0] op_descriptor_id=1,op_rows=0;
reg [511:0] op_payload=0;reg op_rows_bound=1;
wire op_done,op_ok,apply_busy,apply_done,apply_overflow;
wire [15:0] op_trap_class;
wire [31:0] count_prepares,count_commits,count_discards,count_reads;
wire [31:0] count_generation_advances,count_commits_applied,count_rows_committed;
wire [63:0] count_bytes_written;
wire [31:0] session_state_count=1;
ot_a3_state_controller dut(.*);
task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
task reset_tx;begin clear=1;tick();clear=0;end endtask
task op(input [7:0] sub);begin
 op_sub=sub;op_valid=1;tick();op_valid=0;
 if(!op_done || !op_ok)$fatal(1,"operation refused %0d",op_trap_class);
end endtask
task stage(input [31:0] cap,cur,span);begin
 op_payload=0;op_payload[8+:8]=ot_a3_pkg::A3_COMMIT_POLICY_SATURATING;
 op_payload[128+:32]=7;op_payload[192+:32]=cap;op_payload[256+:32]=cur;op_rows=span;
 op(ot_a3_pkg::A3_STATE_PREPARE);op(ot_a3_pkg::A3_STATE_COMMIT);
end endtask
task run_case(input [31:0] cap,cur,span,expected,rows,input integer cycles);
integer waited;
begin
 reset_tx();stage(cap,cur,span);
 if(dut.slot_cursor[0]!==cur || count_commits_applied!=0)$fatal(1,"early publication");
 commit_all=1;tick();commit_all=0;waited=0;
 while(!apply_done)begin tick();waited=waited+1;if(waited>40)$fatal(1,"apply timeout");end
 if(waited!=cycles || apply_busy || dut.slot_cursor[0]!==expected ||
    dut.slot_generation[0]!=1 || count_commits_applied!=1 ||
    count_rows_committed!=rows || count_bytes_written!=64'(rows)*7 || apply_overflow)
  $fatal(1,"ring mismatch cap=%0d cur=%0d span=%0d got=%0d want=%0d cycles=%0d/%0d",cap,cur,span,dut.slot_cursor[0],expected,waited,cycles);
end endtask
integer j;
initial begin
 tick();rst_n=1;
CALLS
 // Cancel at every iterative position; no cursor/generation/counter update
 // may escape, and the same slot must accept a new prepare after discard.
 for(j=0;j<34;j=j+1)begin
  reset_tx();stage(513,512,32'hffffffff);
  commit_all=1;tick();commit_all=0;repeat(j)tick();
  discard_all=1;tick();discard_all=0;
  if(apply_busy || !apply_done || dut.slot_cursor[0]!=512 ||
     dut.slot_generation[0]!=0 || count_commits_applied!=0)$fatal(1,"cancel leaked update");
  stage(513,512,1);commit_all=1;tick();commit_all=0;
  wait(apply_done);@(negedge clk);
  if(dut.slot_cursor[0]!=0 || count_commits_applied!=1)$fatal(1,"restart failed");
 end
 // Non-ring policies keep the single-cycle apply path and accounting.
 reset_tx();op_payload=0;op_payload[128+:32]=7;op_payload[192+:32]=100;
 op_payload[256+:32]=9;op_rows=5;
 op(ot_a3_pkg::A3_STATE_PREPARE);op(ot_a3_pkg::A3_STATE_COMMIT);
 commit_all=1;tick();commit_all=0;tick();
 if(!apply_done || dut.slot_cursor[0]!=14 || count_rows_committed!=5 ||
    count_bytes_written!=35)$fatal(1,"request-span changed");
 reset_tx();op_payload[8+:8]=ot_a3_pkg::A3_COMMIT_POLICY_UNSTAGED;op_rows=0;
 op(ot_a3_pkg::A3_STATE_PREPARE);op(ot_a3_pkg::A3_STATE_COMMIT);
 commit_all=1;tick();commit_all=0;tick();
 if(!apply_done || dut.slot_cursor[0]!=9 || count_rows_committed!=0 ||
    count_bytes_written!=0 || dut.slot_generation[0]!=1)$fatal(1,"unstaged changed");
 // Clear an in-flight divide and reuse the controller.
 reset_tx();stage(513,512,1000);commit_all=1;tick();commit_all=0;
 repeat(12)tick();reset_tx();repeat(40)tick();
 if(apply_busy || count_commits_applied!=0 || dut.slot_used!=0)$fatal(1,"clear leaked update");
 // Rejected payload may be captured, but cannot become a pending entry.
 reset_tx();stage(7,6,5);op_rows=0;op_valid=1;op_sub=ot_a3_pkg::A3_STATE_COMMIT;
 tick();op_valid=0;
 if(op_ok || dut.pending_count!=1 || count_commits!=1)$fatal(1,"rejected entry published");
 op_rows=2;op(ot_a3_pkg::A3_STATE_COMMIT);commit_all=1;tick();commit_all=0;
 wait(apply_done);@(negedge clk);
 if(dut.slot_cursor[0]!=6 || count_rows_committed!=7 || count_commits_applied!=2)$fatal(1,"rejected entry not overwritten");
 // A full queue must not overwrite its oldest valid entry on refusal.
 reset_tx();stage(7,6,1);repeat(15)op(ot_a3_pkg::A3_STATE_COMMIT);
 op_rows=5;op_valid=1;op_sub=ot_a3_pkg::A3_STATE_COMMIT;tick();op_valid=0;
 if(op_ok || dut.pending_count!=16)$fatal(1,"full queue accepted commit");
 commit_all=1;tick();commit_all=0;wait(apply_done);@(negedge clk);
 if(dut.slot_cursor[0]!=1 || count_rows_committed!=16 || count_commits_applied!=16)$fatal(1,"full queue payload corrupted");
 // Multiple staged commits to the same resource consume the updated cursor.
 reset_tx();stage(7,6,5);op(ot_a3_pkg::A3_STATE_COMMIT);commit_all=1;tick();commit_all=0;
 wait(apply_done);@(negedge clk);
 if(dut.slot_cursor[0]!=2 || count_commits_applied!=2 || count_rows_committed!=10)$fatal(1,"staged recurrence");
 $display("PASS ring cursor cases=255 cancel_positions=34");$finish;
end
initial begin #1000000;$fatal(1,"timeout");end
endmodule
'''.replace('CALLS', '\n'.join(calls))
    (tmp_path/'tb.sv').write_text(bench)
    sources = [str(ROOT/'rtl/abi3/ot_a3_pkg.sv'),
               str(ROOT/'rtl/abi3/ot_a3_state_controller.sv'), str(tmp_path/'tb.sv')]
    if simulator == 'iverilog':
        command = ['iverilog', '-g2012', '-s', 'tb', '-o', str(tmp_path/'sim'), *sources]
        executable = ['vvp', str(tmp_path/'sim')]
    else:
        verilator = Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
        if not verilator.exists():
            pytest.skip('pinned Verilator unavailable')
        command = [str(verilator), '--binary', '--timing', '-Wno-fatal',
                   '--top-module', 'tb', '--Mdir', str(tmp_path/'obj'), *sources]
        executable = [str(tmp_path/'obj/Vtb')]
    built = subprocess.run(command, capture_output=True, text=True, timeout=120)
    assert built.returncode == 0, built.stderr
    run = subprocess.run(executable, capture_output=True, text=True, timeout=30)
    assert run.returncode == 0, run.stdout+run.stderr
    assert 'PASS ring cursor' in run.stdout
