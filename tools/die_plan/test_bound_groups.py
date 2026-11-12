from copy import deepcopy
from types import SimpleNamespace as N
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bound_groups as G


def vehicle():
    items=[dict(inst='u_'+k+'0',module=k,reset_pin='rst_n') for k in ('exp','head','lrly','rcp','rsq')]
    cells=[N(module=x['module'],ports={'rst_n':[99]},dirs={'rst_n':'input'}) for x in items]
    hc=dict(inst='u_lane0',bound_group=dict(kind='exact_post_bind_group',reset_pin='rst_n',members=items))
    target=dict(pin='rst_n',tap=10)
    tree=dict(relays=[dict(q='rst_n_t3',depth=4),dict(q='rst_n_t10',depth=4)],tap_roles={3:'mission',10:'mission'})
    rel=lambda i:items[i]['inst']
    return cells,list(range(5)),rel,target,hc,tree,3


def test_explicit_group_reset_projects_every_exact_member_and_rejects_mutants():
    v=vehicle();assert G.reset_members(*v)==[(i,'rst_n') for i in range(5)]
    for mutation in ('missing','wrong_module','depth','start_role','duplicate','noninput'):
        a=list(deepcopy(v));a[2]=v[2]
        if mutation=='missing':a[1]=a[1][:-1]
        if mutation=='wrong_module':a[0][0].module='different'
        if mutation=='depth':a[5]['relays'][1]['depth']=5
        if mutation=='start_role':a[5]['tap_roles'][10]='bootstrap'
        if mutation=='duplicate':a[4]['bound_group']['members'][1]=a[4]['bound_group']['members'][0]
        if mutation=='noninput':a[0][0].dirs['rst_n']='output'
        with pytest.raises(G.BoundGroupError):G.reset_members(*a)


def test_cut_preserves_actual_scheduled_reset_and_committed_core_code():
    import qc_su_lane_cut as C
    from test_qc_su_lane_cut import fixture
    old=fixture();core,_,_=C.cut(old,0)
    source=old.replace('.rst_n(rst_n)','.rst_n(rst_n_t10)').replace('    wire [7:0] x_q;','    wire rst_n_t10;\n    wire [7:0] x_q;')
    new,frame,r=C.cut(source,0)
    assert G._code(core)==G._code(new)
    assert '.rst_n(rst_n_t10)' in frame and r['reset_source']=='rst_n_t10' and r['input_bits']==8
    bad=source.replace('.rst_n(rst_n_t10)','.rst_n(rst_n_t11)',1)
    with pytest.raises(ValueError,match='one exact delivered reset'):C.cut(bad,0)


def test_original_leaf_identity_keeps_real_group_hierarchy():
    t=dict(hard_cores=[dict(inst='u_lane0',bound_group=dict(members=[dict(inst='u_head0')]))])
    assert G.scope_for_member(t,'u_head0')=='u_lane0.'
    assert G.scope_for_member(t,'u_other')==''
    t['hard_cores'].append(dict(inst='u_othergroup',bound_group=dict(members=[dict(inst='u_head0')])))
    with pytest.raises(G.BoundGroupError,match='multiple'):G.scope_for_member(t,'u_head0')


def test_planned_reset_materialization_lockstep_and_wrong_tap_mutant(tmp_path):
    import shutil
    import subprocess
    import qc_su_lane_cut as C
    from test_qc_su_lane_cut import fixture
    if not shutil.which('iverilog'):
        pytest.skip('iverilog unavailable')
    # The source-of-truth vehicle contains the already planned registered reset
    # and START delivery. The cut must connect the actual core reset pin to it.
    source=fixture().replace('module original(input wire clk, input wire rst_n,',
                             'module original(input wire clk, input wire rst_n,')
    source=source.replace('    wire [7:0] x_q;', '''    reg [9:0] reset_pipe=0;
    always @(posedge clk) reset_pipe<={reset_pipe[8:0],rst_n};
    wire rst_n_t9=reset_pipe[8];
    wire rst_n_t10=reset_pipe[9];
    reg start_q=0;
    always @(posedge clk) start_q<=rst_n_t10;
    wire [7:0] x_q;''').replace('.rst_n(rst_n)', '.rst_n(rst_n_t10)')
    core,frame,receipt=C.cut(source,0)
    assert receipt['reset_source']=='rst_n_t10'
    assert '.rst_n(rst_n_t10)' in frame
    leaf='''module leaf(input clk,rst_n,input [7:0] x,output reg [7:0] y=0);
    always @(posedge clk) if(!rst_n) y<=0; else y<={x[6:0],x[7]}^8'h49;
    endmodule
    '''
    tb='''module tb;
    reg clk=0,rst_n=0;reg[7:0] x=0;wire[7:0] a,b;
    original ref0(clk,rst_n,x,a);grouped dut(clk,rst_n,x,b);
    always #5 clk=~clk;
    integer i;
    initial begin
      repeat(3) @(negedge clk);rst_n=1;
      for(i=0;i<128;i=i+1) begin
        x=i;@(negedge clk);
        if(a!==b) $fatal(1,"planned reset cut differs at %0d",i);
        if(ref0.start_q!==dut.start_q) $fatal(1,"START delivery differs");
      end
      $display("RESET LOCKSTEP PASS128");$finish;
    end endmodule
    '''
    def run(body,name):
        p=tmp_path/(name+'.sv');exe=tmp_path/name
        p.write_text(leaf+source+body.replace('module original(', 'module grouped(')+core+tb)
        subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),str(p)],check=True,capture_output=True,text=True)
        return subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
    good=run(frame,'planned')
    assert good.returncode==0 and 'RESET LOCKSTEP PASS128' in good.stdout
    bad=run(frame.replace('.rst_n(rst_n_t10)', '.rst_n(rst_n_t9)'), 'wrongtap')
    assert bad.returncode!=0 and 'planned reset cut differs' in bad.stdout


def test_register_masters_records_successor_head_source_only(tmp_path):
    import qc_su_lane_cut as C
    from test_qc_su_lane_cut import fixture
    src=fixture().replace('leaf u_u_head0 (','qfd_dv_lane_h_safe2 #(.MEMORY_ALIGNMENT(3), .MEMORY_READ_EXTRA(0)) u_u_head0 (')
    assert 'qfd_dv_lane_h_safe2' in src
    rep,_,_=C.cut(src,0,memory_read_extra=9)
    b=N(base=str(tmp_path),extra_lib=[])
    with pytest.raises(G.BoundGroupError):
        G.register_masters(b,src,rep)             # successor master has no source: refused, not silently unread
    (tmp_path/'rtl/physical').mkdir(parents=True)
    f=tmp_path/'rtl/physical/qfd_dv_lane_h_su_mem9.sv'
    f.write_text('module qfd_dv_lane_h_su_mem9(); endmodule\n')
    G.register_masters(b,src,rep);G.register_masters(b,src,rep)
    assert b.extra_lib==[str(f)]                  # the new master, once; the unchanged as-built leaves not added
    b2=N(base=str(tmp_path),extra_lib=[])
    rep0,_,_=C.cut(src,0)
    G.register_masters(b2,src,rep0)
    assert b2.extra_lib==[]                       # no memory_read_extra: nothing new, default unchanged
