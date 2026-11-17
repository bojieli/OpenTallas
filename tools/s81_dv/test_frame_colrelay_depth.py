"""Component proof of emitted relay depths at production bus widths."""
import importlib.util
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sp = importlib.util.spec_from_file_location('cd', HERE/'frame_colrelay_depth.py')
cd = importlib.util.module_from_spec(sp)
sp.loader.exec_module(cd)


def fixture():
    ports = ['input wire clk', 'input wire rs', 'input wire [535:0] din']
    rows=['    wire [535:0] ctrl_in;', '    ot_s81_rly #(.W(536), .RSREG(1)) u_ctrl (.ck(clk), .rs(rs), .i(din), .o(ctrl_in));']; observed=[]
    for i,(inst,(w,extra)) in enumerate(cd.LINEAR.items()):
        o=f'o{i}'; ports.append(f'output wire [{w-1}:0] {o}')
        if inst.startswith('u_lpl'):
            rows.append(f'    ot_pl_seam_r_plq #(.W({w}), .K(2), .CHUNK_BITS(24)) {inst} (.ck(clk), .rsi(rs), .d(din[{w-1}:0]), .o({o}));')
        else:
            rows.append(f'    dsfd_rly_{w}_NS {inst} (.ck(clk), .rs(rs), .i(din[{w-1}:0]), .o({o}));')
        observed.append((o,w,extra))
    for idx,(inst,(w,tp,bp)) in enumerate(cd.BRANCH.items()):
        raw=f'b{idx}'; rows.append(f'    wire [{w-1}:0] {raw};')
        rows.append(f'    dsfd_rly_{w}_NS {inst} (.ck(clk), .rs(rs), .i(din[{w-1}:0]), .o({raw}));')
    for sink,depth in [('u_bs0',3),('u_t1',2),('u_bs2',1)]:
        pin0,pin1=('xai','xbi') if sink=='u_t1' else ('i_x0','i_x1')
        for idx,w in [(0,283),(1,266)]:
            o=f'{sink[2:]}_{idx}';ports.append(f'output wire [{w-1}:0] {o}');observed.append((o,w,depth-1))
        extra = '.ck(clk), .rs(rs), '
        if sink == 'u_bs0':
            ports += ['output wire [53:0] cfg0', 'output wire go0']
            extra += '.i_cfg(ctrl_in[53:0]), .i_go(ctrl_in[0]), .cfg(cfg0), .go(go0), '
            observed += [('cfg0',54,2), ('go0',1,2)]
        if sink == 'u_t1':
            ports += ['output wire [14:0] cc1']
            extra += '.cci(ctrl_in[14:0]), .cc(cc1), '
            observed += [('cc1',15,1)]
        rows.append(f'    sink_{sink[2:]} {sink} ('+extra+f'.{pin0}(b0), .{pin1}(b1), .a({sink[2:]}_0), .b({sink[2:]}_1));')
    ports += ['output wire [1:0] tag0']
    rows.append('    elem_tag u_e0 (.clk(clk), .rst_n(rs), .go_tag(ctrl_in[1:0]), .tag(tag0));')
    observed += [('tag0',2,2)]
    src='module col_h10_l4_lp_r0 #(parameter integer MUT = 0, parameter integer DUMMY=0)(\n'+',\n'.join(ports)+'\n);\n'+'\n'.join(rows)+'\nendmodule\n'
    return src,observed


def support():
    text=''
    for w in [2,66,536,283,266]:
        text+=f'module dsfd_rly_{w}_NS(input ck,rs,input [{w-1}:0] i,output [{w-1}:0] o); ot_s81_rly #(.W({w}),.RSREG(1)) u(.*); endmodule\n'
    # The transform appends stages to the reader output. Existing seam internals
    # are abstracted to one registered producer, the minimum delay mechanism.
    text+='module ot_pl_seam_r_plq #(parameter W=2,K=2,CHUNK_BITS=24)(input ck,rsi,input[W-1:0] d,output[W-1:0] o); ot_s81_rly #(.W(W),.RSREG(1)) u(.ck(ck),.rs(rsi),.i(d),.o(o)); endmodule\n'
    for name,p0,p1 in [('bs0','i_x0','i_x1'),('t1','xai','xbi'),('bs2','i_x0','i_x1')]:
        extra = 'input ck,rs, '
        body = ''
        if name == 'bs0':
            extra += 'input[53:0] i_cfg,input i_go,output[53:0] cfg,output go, '
            body += 'assign cfg=i_cfg; assign go=i_go; '
        if name == 't1':
            extra += 'input[14:0] cci,output[14:0] cc, '
            body += 'assign cc=cci; '
        text+=f'module sink_{name}('+extra+f'input[282:0] {p0},input[265:0] {p1},output[282:0] a,output[265:0] b); '+body+f'assign a={p0}; assign b={p1}; endmodule\n' 
    text += 'module elem_tag(input clk,rst_n,input[1:0] go_tag,output[1:0] tag); assign tag=go_tag; endmodule\n'
    return text


def bench(obs):
    lines=['module tb; reg clk=0; always #5 clk=~clk; reg rs=0; reg[535:0] din=0; integer c,j,k;']
    conn=['.clk(clk)', '.rs(rs)', '.din(din)']
    for o,w,d in obs:
        lines+=[f'wire[{w-1}:0] b_{o},n_{o},z_{o};', f'reg[{w-1}:0] h_{o}[0:{d}];']
    for mode,prefix,param in [('base','b',''),('candidate','n','#(.COLRELAY_P1(1))'),('candidate','z','#(.COLRELAY_P1(0))')]:
        con=conn+[f'.{o}({prefix}_{o})' for o,_,_ in obs]
        lines.append(f'{mode} {param} u_{prefix}('+','.join(con)+');')
    lines.append('initial begin\n for(c=0;c<12000;c=c+1) begin\n @(negedge clk); rs=(c%337>3); for(k=0;k<17;k=k+1) din[k*32+:32]=$random; @(posedge clk); #2;')
    for o,w,d in obs:
        lines.append(f'if(!rs) for(j=0;j<={d};j=j+1) h_{o}[j]=0; else begin for(j={d};j>0;j=j-1) h_{o}[j]=h_{o}[j-1]; h_{o}[0]=b_{o}; end')
        lines.append(f'if(z_{o}!==b_{o}) $fatal(1,"DEFAULT {o} cycle %0d",c); if(n_{o}!==h_{o}[{d}]) $fatal(1,"DELAY {o} cycle %0d",c);')
    lines+=['end $display("COLRELAY_COMPONENT_PASS 12000 edges 36 reset bursts"); $finish; end endmodule']
    return '\n'.join(lines)


class Depth(unittest.TestCase):
    def test_production_shape_and_mutant(self):
        if not shutil.which('iverilog'):self.skipTest('iverilog unavailable')
        src,obs=fixture(); new,report=cd.transform(src)
        self.assertEqual(len(report['groups']),17)
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            primitive=HERE.parents[1]/'rtl/dsrom_sys/s81_glue/ot_s81_rly.sv'
            base=src.replace('module col_h10_l4_lp_r0','module base',1)
            new=new.replace('module col_h10_l4_lp_r0','module candidate',1)
            for mutant in [False,True]:
                candidate=new
                if mutant:
                    old='.i(cr_lpl_11_r_s0), .o(cr_lpl_11_r_s1))'
                    self.assertIn(old,candidate)
                    candidate=candidate.replace(old,'.i(cr_lpl_11_r_old), .o(cr_lpl_11_r_s1))',1)
                (d/'tb.sv').write_text(base+candidate+support()+bench(obs))
                r=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(d/'sim'),str(primitive),str(d/'tb.sv')],capture_output=True,text=True)
                self.assertEqual(r.returncode,0,r.stderr)
                r=subprocess.run(['vvp',str(d/'sim')],capture_output=True,text=True)
                if mutant:self.assertNotEqual(r.returncode,0,'bypass mutant survived')
                else:self.assertEqual(r.returncode,0,r.stdout+r.stderr)

    def test_fail_closed(self):
        s,_=fixture()
        with self.assertRaises(ValueError):cd.transform(s.replace('u_y_so_3_0','missing'))
        n,_=cd.transform(s)
        with self.assertRaises(ValueError):cd.transform(n)


if __name__=='__main__':unittest.main()
