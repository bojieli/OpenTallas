"""Coherent CBF INNER floor: companion/downstream timing, actual binder strap widths, real delay-bank miter."""
from pathlib import Path
import importlib.util, json, subprocess
import pytest
import cbf_inner_event as E
import bind
from test_inner_strap_pads import _binder
ROOT=Path(__file__).resolve().parents[2]


def graph():
    e=lambda src,po='t_out',d=0:dict(src=src,src_port=po,delta=d)
    return {('c.u_t_0_2','tap'):e('root'),('c.u_t_1_2','tap'):e('root'),
      ('c.u_t_0_2','n_a'):e('c.u_t_0_2'),('c.u_t_0_2','n_b'):e('c.u_t_1_2'),
      ('c.u_t_0_0','n_a'):e('c.u_t_0_2','n_y'),('c.u_t_0_0','n_b'):e('other')}


def test_floor_balances_companion_and_downstream():
    pads,t=E.coherent_pads(graph(),{('c.u_t_0_2','n_b'):1})
    assert pads=={('c.u_t_0_2','n_a'):1,('c.u_t_0_2','n_b'):1,('c.u_t_0_0','n_b'):1}
    assert t[('c.u_t_0_2','n_y')]==t[('c.u_t_0_0','n_y')]==1


def test_unaligned_seed_is_rejected_and_missing_companion_is_not_silent():
    e=graph();e[('c.u_t_0_2','n_b')]['delta']=1
    with pytest.raises(ValueError,match='not coherent'):E.coherent_pads(e,{('c.u_t_0_2','n_b'):1})
    e=graph();del e[('c.u_t_0_2','n_a')]
    with pytest.raises(ValueError,match='complete paired'):E.coherent_pads(e,{('c.u_t_0_2','n_b'):1})


def test_no_floor_is_exact_noop():
    pads,t=E.coherent_pads(graph(),{})
    assert pads=={} and set(t.values())=={0}


def test_actual_binder_new_fixed_floor_preserves_optional_span_and_counts():
    b=_binder({'a':[3]*514,'b':[3]*514},port_w=514)
    inner=[dict(id=f'INNER:{p}:{p}_u.x<-{p}_s@{old}',sink=f'{p}_u',source=f'{p}_s',sink_port='x',asbuilt=3,landed=old+1)
      for p,old in [('a',3),('b',4)]]
    st={'stale':0};b._apply_inner(inner,{c.path:i for i,c in enumerate(b.F.cells)},st)
    assert st['stale']==0 and st['inner']['changed_bits']==1028
    b.inner_strap_sites({'T':['a','b']});s=next(iter(b.r8_sites['T'].values()))
    assert (s['base'],s['span'],s['counts'],s['width'])==(4,1,{'a':0,'b':1},514)


def sim(tmp, count, mutant):
    # The actual binder CELLS and released ot_dp_dly_cnt are the DUT, not a mirror implementation.
    tb=f'''module bank #(parameter integer BASE=3,CNT=0)(input wire clk,input wire[513:0]d,output wire[513:0]q);
wire[513:0]f,c;ot_dp_dly #(.W(514),.D(BASE))u_f(clk,d,f);ot_dp_dly_cnt #(.W(514),.DMAX(1))u_c(clk,4'd{{CNT}},f,c);ot_dp_dly #(.W(514),.D(1))u_pc(clk,c,q);endmodule
module tb;reg clk=0;always #5 clk=~clk;reg[513:0]a=0,b=0;wire[513:0]oa,ob,na,nb0;wire[513:0]nb=nb0^{"514'd1" if mutant==3 else "514'd0"};reg[513:0]ra=0,rb=0;integer cyc=0;
bank #(.BASE(3),.CNT({count}))old_a(clk,a,oa),old_b(clk,b,ob);
bank #(.BASE(4),.CNT({count}))new_a(clk,a,na);
bank #(.BASE({3 if mutant==1 else 4}),.CNT({1-count if mutant==2 else count}))new_b(clk,b,nb0);
always @(posedge clk)begin ra<=oa;rb<=ob;end
always @(negedge clk)begin
if(cyc>24 && (na!==ra || nb!==rb || na[512]!==nb[512]))$fatal(1,"CBF_LOCKSTEP cycle%0d",cyc);
cyc=cyc+1;a={{16{{cyc[31:0]}}}};b={{16{{~cyc[31:0]}}}};a[513]=0;b[513]=0;a[512]=(cyc%13==0);b[512]=a[512];
if(cyc==2048)begin $display("CBF_LOCKSTEP_PASS count{count} edges2048 width514");$finish;end end endmodule'''
    tb=tb.replace("4'd{CNT}","CNT[3:0]")
    (tmp/'cells.sv').write_text(bind.CELLS);(tmp/'tb.sv').write_text(tb)
    exe=tmp/f'sim_{count}_{mutant}'
    p=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),str(tmp/'cells.sv'),str(ROOT/'rtl/common/ot_dp_dly_cnt.sv'),str(tmp/'tb.sv')],capture_output=True,text=True)
    assert p.returncode==0,p.stdout+p.stderr
    p=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);(tmp/f'run_{count}_{mutant}.log').write_text(p.stdout+p.stderr)
    return p.returncode,p.stdout


def test_real_r8_banks_plus_one_lockstep_and_seeded_controls(tmp_path):
    for c in [0,1]:
        assert sim(tmp_path,c,0)[0]==0
        for mutant in [1,2,3]:assert sim(tmp_path,c,mutant)[0]!=0


def tcl_procs(names):
    import re
    src=(ROOT/'tools/die_plan/core_input_chain.tcl').read_text();out=[]
    for name in names:
        m=re.search(r'^proc '+re.escape(name)+r'\s+\{[^\n]*?\}\s+\{',src,re.M);assert m,name
        i=m.end();depth=1
        while depth:
            c=src[i];i+=1
            if c=='\\':i+=1;continue
            if c=='{':depth+=1
            elif c=='}':depth-=1
        out.append(src[m.start():i])
    return '\n'.join(out)+'\n'


def test_actual_tcl_name_aliases_and_minimum_count_corridor(tmp_path):
    funcs=tcl_procs(['nc_hit','nc_len','nc_ok','nc_at','nc_cnt_route_ok','nc_cnt_layout','nc_cnt_parse_name'])
    script=funcs+r'''
set f0 {u_bound.u_r8b_strap_r8pad_u_t_0_2_n_b_in_f.r[0][78]$_DFF_P_}
set fq {u_bound.u_r8b_strap_r8pad_u_t_0_2_n_b_in_f.q[78]$_DFF_P_}
set cr {u_bound.u_r8b_strap_r8pad_u_t_0_2_n_b_in/r[0][78]$_DFF_P_}
set pq {u_bound.u_pc_nk_u_t_0_2_n_b.q[78]$_DFF_P_}
foreach n [list $f0 $fq $cr $pq] want {fixed fixedq count pc} {if {[lindex [nc_cnt_parse_name $n] 0] ne $want} {error "alias $want lost"}}
set nc_mac {{691200 77760 1149120 1235520} {86400 77760 544320 1235520}}
set route {{1162080 986000} {1162080 1244160} {550080 1244160} {550080 885000}}
if {![catch {nc_cnt_layout $route 3 1 1000} err] || ![string match *NEED_PIN_CYCLE* $err]} {error "N3 must reject insufficient reach"}
set z [nc_cnt_layout $route 4 1 1000]
if {[llength [dict get $z fixed]]!=3 || [llength [dict get $z count]]!=1 || [dict get $z max_hop_um]>405} {error "N4 layout invalid"}
# Every legal optional count: bypass0 or through1 stays in the same last fixed->PC hop.
set fixed [concat [list [lindex $route 0]] [dict get $z fixed]]
foreach suffix [list [list [lindex $route end]] [concat [dict get $z count] [list [lindex $route end]]]] {
 set p [concat $fixed $suffix]
 for {set k 1} {$k<[llength $p]} {incr k} {lassign [lindex $p [expr {$k-1}]] a b;lassign [lindex $p $k] c d;if {abs($a-$c)+abs($b-$d)>405000} {error "optional count over reach"}}
}
if {![catch {nc_cnt_layout {{0 0} {1 1}} 4 1 1}]} {error "diagonal corridor was accepted"}
puts TCL_CBF_CORRIDOR_PASS
'''
    f=tmp_path/'probe.tcl';f.write_text(script)
    p=subprocess.run(['tclsh',str(f)],capture_output=True,text=True)
    assert p.returncode==0,p.stdout+p.stderr
    assert 'TCL_CBF_CORRIDOR_PASS' in p.stdout


def test_failing_strict_seed_cannot_emit_an_event(tmp_path):
    (tmp_path/'plan.json').write_text(json.dumps({'partitions':[]}))
    (tmp_path/'bind_report.json').write_text(json.dumps({'n_errors':1,'errors':['R8_STALE actualseed']}))
    with pytest.raises(ValueError,match='clean strict seed'):
        E.generate(tmp_path/'plan.json',tmp_path,'not-read-r8.json','not-read-extra.json')
