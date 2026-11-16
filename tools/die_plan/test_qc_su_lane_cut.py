from pathlib import Path
import shutil
import subprocess
import sys
import pytest
import re
sys.path.insert(0, str(Path(__file__).resolve().parent))
from qc_su_lane_cut import cut


def fixture():
    text = 'module original(input wire clk, input wire rst_n, input wire [7:0] x, output wire [7:0] y);\n    wire [7:0] x_q;\n    assign x_q=x;\n'
    names = ['exp', 'rsq', 'head', 'rcp', 'lrly']
    for k in names:
        text += f'    wire [7:0] w_u_{k}0_y;\n'
    for i, k in enumerate(names):
        src = 'x_q' if i == 0 else f'w_u_{names[i-1]}0_y'
        text += f'    // as-built root.u_{k}0\n    leaf u_u_{k}0 (\n        .clk(clk),\n        .rst_n(rst_n),\n        .x({src}),\n        .y(w_u_{k}0_y)\n    );\n'
    return text + '    assign y=w_u_lrly0_y;\nendmodule\n'


def test_exact_group_lockstep_and_mutant(tmp_path):
    if not shutil.which('iverilog'):
        pytest.skip('iverilog unavailable')
    source = fixture()
    rtl, frame, report = cut(source, 0)
    assert (report['input_bits'], report['output_bits'], report['added_cycles']) == (8, 8, 0)
    leaf = '''module leaf(input clk,rst_n,input [7:0] x,output reg [7:0] y);
    always @(posedge clk) if(!rst_n) y<=0; else y<={x[6:0],x[7]}^8'h49;
    endmodule
    '''
    tb = '''module tb;
    reg clk=0,rst_n=0; reg[7:0] x=0; wire[7:0] a,b;
    original ref0(clk,rst_n,x,a); grouped dut(clk,rst_n,x,b);
    always #5 clk=~clk;
    integer i;
    initial begin
      repeat(3) @(negedge clk); rst_n=1;
      for(i=0;i<256;i=i+1) begin x=i; @(negedge clk); if(a!==b) $fatal(1,"cut differs at %0d",i); end
      $display("LOCKSTEP PASS256"); $finish;
    end endmodule
    '''
    def run(core, name):
        p=tmp_path/(name+'.sv')
        p.write_text(leaf+source+frame.replace('module original(', 'module grouped(')+core+tb)
        exe=tmp_path/name
        subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),str(p)],check=True,capture_output=True,text=True)
        return subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
    good=run(rtl,'good')
    assert good.returncode == 0 and 'LOCKSTEP PASS256' in good.stdout
    bad=run(rtl.replace('assign x_q[0] = c_i[0];','assign x_q[0] = c_i[1];'),'mutant')
    assert bad.returncode != 0 and 'cut differs' in bad.stdout


def test_missing_leaf_rejected():
    with pytest.raises(ValueError,match='exactly five'):
        cut(fixture().replace('u_u_rcp0','u_u_other0'),0)


def test_bound_head_alignment_contract():
    source=fixture().replace('leaf u_u_head0 (', 'leaf #(.MEMORY_ALIGNMENT(3)) u_u_head0 (')
    _,_,r=cut(source,0,memory_alignment=3)
    assert r['memory_alignment']==3
    with pytest.raises(ValueError,match='regenerate the canonical bind'):
        cut(source.replace('MEMORY_ALIGNMENT(3)','MEMORY_ALIGNMENT(0)'),0,memory_alignment=3)
    with pytest.raises(ValueError,match='regenerate the canonical bind'):
        cut(fixture(),0,memory_alignment=3)


def test_kv_wr_pipe_binds_head_once():
    source=fixture().replace("leaf u_u_head0 (", "qfd_dv_lane_h_safe2 #(.MEMORY_ALIGNMENT(3), .MEMORY_READ_EXTRA(0)) u_u_head0 (")
    rtl, _, report = cut(source, 0, memory_alignment=3, kv_wr_pipe=1)
    assert rtl.count(".KV_WR_PIPE(1)") == 1 and report["kv_wr_pipe"] == 1 and report["added_cycles"] == 0
    assert ".KV_WR_PIPE(" not in cut(source, 0)[0]
    with pytest.raises(ValueError, match="different KV_WR_PIPE"):
        cut(source.replace(".MEMORY_READ_EXTRA(0))", ".MEMORY_READ_EXTRA(0), .KV_WR_PIPE(0))"), 0, kv_wr_pipe=1)


def test_memory_read_extra_binds_mem9_head():
    source=fixture().replace("leaf u_u_head0 (", "qfd_dv_lane_h_safe2 #(.MEMORY_ALIGNMENT(3), .MEMORY_READ_EXTRA(0)) u_u_head0 (")  # QC-MEM9: EXTRA9 selects the successor head
    rtl, _, report = cut(source, 0, memory_alignment=3, kv_wr_pipe=1, memory_read_extra=9)
    assert rtl.count("qfd_dv_lane_h_su_mem9") == 1 and "qfd_dv_lane_h_safe2 " not in rtl and ".MEMORY_READ_EXTRA(9)" in rtl
    assert report["memory_read_extra"] == 9
    rtl0, _, report0 = cut(source, 0, memory_alignment=3, kv_wr_pipe=1)
    assert "qfd_dv_lane_h_safe2" in rtl0 and report0["memory_read_extra"] == 0


def test_one_bit_vector_keeps_its_range():
    """QC-VERIFY-GAPS (QC s26 verify lint, 29-30 errors per lane module): a bound [0:0] wire selected as n[0] by a leaf
    body was declared 'wire n;' in the cut (Illegal bit select).  The cut keeps the declared range on every one-bit
    vector, its c_i/c_o wiring and the frame concatenation; scalar wires stay scalar."""
    source = fixture().replace('    wire [7:0] x_q;\n', '    wire [7:0] x_q;\n    wire [0:0] p_v;\n    wire s_q;\n    assign s_q=x[0];\n')
    source = source.replace('        .x(w_u_exp0_y),\n', '        .x(w_u_exp0_y),\n        .v(p_v[0]),\n')
    source = source.replace('        .x(x_q),\n', '        .x(x_q),\n        .s(s_q),\n')
    source = source.replace('    assign y=w_u_lrly0_y;', '    assign y=w_u_lrly0_y;\n    assign p_v[0]=x[1];')
    rtl, frame, report = cut(source, 0)
    assert '    wire [0:0] p_v;' in rtl and '    wire p_v;' not in rtl
    assert '    wire s_q;' in rtl and 'assign s_q = c_i[' in rtl
    assert re.search(r'assign p_v\[0\] = c_i\[\d+\];', rtl) and re.search(r'\.c_i\(\{[^}]*\bp_v\[0\]', frame)
    assert report['added_cycles'] == 0
    v = shutil.which('verilator')
    if v:
        p = Path(__file__).parent / '.lane_cut_lint_tmp.sv'
        try:
            p.write_text('module leaf(input clk,rst_n,input [7:0] x,input v,input s,output [7:0] y);\n'
                         '  assign y=x^{7\'d0,v^s};\nendmodule\n' + rtl)
            r = subprocess.run([v, '--lint-only', '-Wno-fatal',
                                '--top-module', report['module'], str(p)], capture_output=True, text=True)
            assert '%Error' not in r.stderr, r.stderr
        finally:
            p.unlink(missing_ok=True)


def abi_vehicle():
    import hashlib
    source=fixture()
    reference,_,_=cut(source,0)
    # The new receiver is an explicit bitwise alias. Its physical age is outside
    # this grouping test; only the exact cut/interface mechanism is exercised.
    changed=source.replace('    wire [7:0] x_q;', '    wire [7:0] x_q;\n    wire [7:0] pad_q;\n    assign pad_q=x_q;')
    changed=changed.replace('.x(x_q)', '.x({pad_q[7:4],pad_q[3:0]})')
    digest=hashlib.sha256(reference.encode()).hexdigest()
    group=dict(module='qfd_qc_su_lane_w_l0',reference_sha256=digest,
               sink_leaf='u_exp0',sink_port='x',r8_member_id='exact-member-0',
               bits=[dict(abi_bit=i,sink_bit=i,original_local=dict(name='x_q',bit=i),
                          original_frame_expr=f'x_q[{i}]',replacement_frame_expr=f'pad_q[{i}]') for i in range(8)])
    return changed,dict(reference_rtl=reference,reference_sha256=digest,aliases=[group])


def test_explicit_input_abi_preserves_reference_and_only_rewires_frame():
    source,abi=abi_vehicle()
    rtl,frame,r=cut(source,0,input_abi=abi)
    assert rtl==abi['reference_rtl']
    assert r['input_abi_changed_bits']==8 and r['input_abi_all_leaf_ports_verified']
    assert '.c_i({pad_q[7], pad_q[6], pad_q[5], pad_q[4], pad_q[3], pad_q[2], pad_q[1], pad_q[0]})' in frame
    assert 'wire [7:0] pad_q;' not in rtl and '.x(x_q)' in rtl


@pytest.mark.parametrize('mutant', ['hash','duplicate','missing','wrong_bit','wrong_sink','module','undeclared','output','internal','reset'])
def test_explicit_input_abi_rejects_drift(mutant):
    from copy import deepcopy
    source,abi=abi_vehicle();abi=deepcopy(abi)
    if mutant=='hash':abi['reference_sha256']='0'*64
    if mutant=='duplicate':abi['aliases'][0]['bits'].append(deepcopy(abi['aliases'][0]['bits'][0]))
    if mutant=='missing':abi['aliases'][0]['bits'].pop()
    if mutant=='wrong_bit':abi['aliases'][0]['bits'][0]['replacement_frame_expr']='pad_q[1]'
    if mutant=='wrong_sink':abi['aliases'][0]['sink_leaf']='u_rcp0'
    if mutant=='module':source=source.replace('leaf u_u_rcp0', 'other u_u_rcp0')
    if mutant=='undeclared':abi['aliases'][0]['bits'][0]['replacement_frame_expr']='nonexistent[0]'
    if mutant=='output':source=source.replace('assign y=w_u_lrly0_y;', 'assign y=w_u_rcp0_y;')
    if mutant=='internal':source=source.replace('.x(w_u_rsq0_y)', '.x(w_u_exp0_y)')
    if mutant=='reset':source=source.replace('.rst_n(rst_n)', '.rst_n(rst_n_t10)',1)
    with pytest.raises(ValueError):cut(source,0,input_abi=abi)


def test_segmented_delay_is_explicit_and_default_off():
    source=fixture().replace('leaf u_u_head0 (','qfd_dv_lane_h_safe2 #(.MEMORY_ALIGNMENT(3), .MEMORY_READ_EXTRA(0)) u_u_head0 (')
    normal=cut(source,0,memory_read_extra=9)[0]
    assert '.SEGMENTED_MEMORY_DELAY(' not in normal
    rtl,_,r=cut(source,0,memory_read_extra=44,segmented_memory_delay=1)
    assert '.MEMORY_READ_EXTRA(44)' in rtl and '.SEGMENTED_MEMORY_DELAY(1)' in rtl
    assert r['segmented_memory_delay']==1
    with pytest.raises(ValueError,match='explicit MEMORY_READ_EXTRA'):
        cut(source,0,segmented_memory_delay=1)
    with pytest.raises(ValueError,match='explicit 0 or 1'):
        cut(source,0,memory_read_extra=44,segmented_memory_delay=2)


def test_reference_module_rename_requires_explicit_retarget():
    source,abi=abi_vehicle()
    with pytest.raises(ValueError,match='module differs'):
        cut(source,0,module='new_group',input_abi=abi)
    abi['reference_module']='qfd_qc_su_lane_w_l0'
    with pytest.raises(ValueError,match='retarget must be explicit'):
        cut(source,0,module='new_group',input_abi=abi)
    abi['retarget_module']='new_group'
    rtl,_,_=cut(source,0,module='new_group',input_abi=abi)
    assert rtl==abi['reference_rtl'].replace('module qfd_qc_su_lane_w_l0 (','module new_group (')


def test_input_abi_rejects_mixed_partitions_even_when_bit_aliases_are_disjoint():
    from copy import deepcopy
    source,abi=abi_vehicle()
    group=abi['aliases'][0]
    group.update(type='t',partition='p0')
    other=deepcopy(group);other['partition']='p1'
    group['bits']=group['bits'][:4];other['bits']=other['bits'][4:]
    abi['aliases'].append(other)
    with pytest.raises(ValueError,match='mixed type/partition'):
        cut(source,0,input_abi=abi)


def test_segmented_existing_enable_cannot_be_silently_selected_by_default():
    source=fixture().replace('leaf u_u_head0 (','qfd_dv_lane_h_su_mem9 #(.MEMORY_ALIGNMENT(3), .MEMORY_READ_EXTRA(44), .SEGMENTED_MEMORY_DELAY(1)) u_u_head0 (')
    with pytest.raises(ValueError,match='different SEGMENTED_MEMORY_DELAY'):
        cut(source,0)
    with pytest.raises(ValueError,match='different SEGMENTED_MEMORY_DELAY'):
        cut(source,0,memory_read_extra=44)
