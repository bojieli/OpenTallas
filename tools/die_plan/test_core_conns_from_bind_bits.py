from pathlib import Path
import pytest
import core_conns_from_bind as C


def lef(tmp, name, ports):
    rows=['MACRO '+name]
    for pin,(direction,width) in ports.items():
        for i in range(width):
            n=pin+f'[{i}]'
            rows += [' PIN '+n, ' DIRECTION '+direction+' ;', ' END '+n]
    rows += ['END '+name]
    p=tmp/(name+'.lef');p.write_text('\n'.join(rows)+'\n');return str(p)


def plan(tmp, src_width=4, dst_ports=None):
    a=lef(tmp,'HS',{'q':('OUTPUT',src_width)})
    b=lef(tmp,'HT',dst_ports or {'x':('INPUT',4),'y':('INPUT',4),'z':('INPUT',1)})
    return {'partition_types':{'top':{'module':'top','buses':[{'name':'in_bus','dir':'in','width':4},{'name':'out_bus','dir':'out','width':4}],
        'hard_cores':[{'inst':'src','module':'HS','lef':a},{'inst':'dst','module':'HT','lef':b}]}}}


def test_concat_slice_does_not_join_other_fields_or_constants(tmp_path):
    p=plan(tmp_path)
    text='''module top(input wire [3:0] in_bus);
wire [3:0] q,iq;
wire [8:0] mix;
HS u_src (.q(q));
ot_dp_st u_bin_in_bus (.d(in_bus),.q(iq));
assign mix = {q,1'b0,iq};
HT u_dst (.x(mix[8:5]),.y(mix[3:0]),.z(mix[4]));
endmodule'''
    r=C.trace(p,'top',text)
    cc=r['core_conns']['top']
    assert cc['dst']['x']==['core:src.q']
    assert cc['dst']['y']==['bus:in_bus']
    assert 'z' not in cc['dst']
    assert cc['src']['q']==['core:dst.x']
    assert next(x for x in r['paths'] if x['core']=='src')['bit_ranges']==[[0,3]]


def test_partial_assigns_preserve_bit_offsets(tmp_path):
    p=plan(tmp_path)
    text='''module top(input wire [3:0] in_bus);
wire [3:0] q,iq;
wire [7:0] mix;
HS u_src (.q(q));
ot_dp_st u_bin_in_bus (.d(in_bus),.q(iq));
assign mix[7:4]=q;
assign mix[3:0]=iq;
HT u_dst (.x(mix[7:4]),.y(mix[3:0]));
endmodule'''
    cc=C.trace(p,'top',text)['core_conns']['top']
    assert cc['dst']['x']==['core:src.q']
    assert cc['dst']['y']==['bus:in_bus']


def test_signed_extension_and_constant_replication():
    w={'q':(1,0,True)}
    q,sgn=C.expression_bits('q',w)
    assert C.align_bits(list(range(4)),q,sgn)==[(0,'q[1]'),(1,'q[1]'),(2,'q[1]'),(3,'q[0]')]
    assert C.expression_bits("{2{q[1],1'b0}}",w)[0]==['q[1]',None,'q[1]',None]
    assert C.expression_bits("8'sh80",w)[0]==[None]*8
    assert C.expression_bits('q[1:0]',w)[1] is False


def test_actual_pin_mask_retains_only_low_connected_output_bits(tmp_path):
    p=plan(tmp_path,src_width=8,dst_ports={'x':('INPUT',4)})
    text='''module top();
wire [3:0] q;
HS u_src (.q(q));
HT u_dst (.x(q));
endmodule'''
    r=C.trace(p,'top',text)
    row=next(x for x in r['paths'] if x['core']=='src')
    assert row['bit_ranges']==[[0,3]] and row['bits_connected']==4


def test_real_transport_stages_exclude_face_boundary(tmp_path):
    p=plan(tmp_path,dst_ports={'x':('INPUT',4)})
    text='''module top(input wire [3:0] in_bus);
wire [3:0] iq,a,b,c;
ot_dp_st u_bin_in_bus (.d(in_bus),.q(iq));
ot_dp_dly #(.D(4)) u_lpad (.d(iq),.q(a));
ot_pl_seam_r_plq #(.K(2)) u_seam (.d(a),.o(b));
dsfd_rly_536_SW u_relay (.i(b),.o(c));
HT u_dst (.x(c));
endmodule'''
    row=C.trace(p,'top',text)['paths'][0]
    assert row['stages_existing']==6
    assert row['via']==['u_relay','u_seam','u_lpad']


def test_two_input_ports_are_never_each_others_producer(tmp_path):
    p=plan(tmp_path,dst_ports={'x':('INPUT',4)})
    p['partition_types']['top']['hard_cores'][0]={'inst':'src','module':'HT','lef':p['partition_types']['top']['hard_cores'][1]['lef']}
    text='''module top();
wire [3:0] w_input_x;
HT u_src (.x(w_input_x));
HT u_dst (.x(w_input_x));
endmodule'''
    assert C.trace(p,'top',text)['core_conns']['top']=={}


def test_unknown_logic_is_not_wiring(tmp_path):
    p=plan(tmp_path,dst_ports={'x':('INPUT',4)})
    text='''module top();
wire [3:0] q,a;
HS u_src (.q(q));
assign a=q & 4'b1010;
HT u_dst (.x(a));
endmodule'''
    r=C.trace(p,'top',text)
    assert r['core_conns']['top']=={} and r['wiring_warnings']


def test_unique_generated_underscore_alias_and_collision_rejection():
    rows=[{'inst':'u_r.u_t9__payload','module':'PAY'}]
    assert C.match_hard_cores(rows,[('PAY','u_u_t9_payload',{},None)])[0]=={'u_u_t9_payload':'u_r.u_t9__payload'}
    rows.append({'inst':'u_r.u_t9_payload','module':'PAY'})
    matched,bad=C.match_hard_cores(rows,[('PAY','u_u_t9_payload',{},None)])
    assert not matched and len(bad)==1


def test_widths_and_instances_do_not_leak_between_modules(tmp_path):
    p=plan(tmp_path,dst_ports={'x':('INPUT',4)})
    text='''module other();
wire [31:0] q;
HT u_not_top (.x(q));
endmodule
module top();
wire [3:0] q;
HS u_src (.q(q));
HT u_dst (.x(q));
endmodule'''
    r=C.trace(p,'top',text)
    assert r['n_insts']==2
    assert r['paths'][0]['bits_connected']==4


def test_nonliteral_transport_depth_fails_closed(tmp_path):
    p=plan(tmp_path,dst_ports={'x':('INPUT',4)})
    text='''module top(input wire [3:0] in_bus);
wire [3:0] iq,q;
ot_dp_st u_bin_in_bus (.d(in_bus),.q(iq));
ot_dp_dly #(.D(UNKNOWN)) u_d (.d(iq),.q(q));
HT u_dst (.x(q));
endmodule'''
    r=C.trace(p,'top',text)
    assert not r['core_conns']['top']
    assert any(x['reason']=='nonliteral delay D' for x in r['wiring_warnings'])
