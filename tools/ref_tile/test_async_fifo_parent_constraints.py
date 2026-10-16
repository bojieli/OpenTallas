"""Actual source-parent audit and mapped CDC consumers; no physical timing claim."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import async_gray_fifo_constraints as A
import clock_entry_constraints as C
from test_async_gray_fifo_constraints import YOSYS, STA, ROOT, fixture_lib


PARENT='''module audited_parent(
 input wire stream_clk,hbm_clk,stream_rst_n,hbm_rst_n,
 input wire wr_valid,rd_ready,input wire [1:0] din,
 output wire wr_ready,output reg [1:0] dout,output reg valid,
 output wire wr_fault,rd_fault);
 wire [1:0] data;wire rv;
 ot_hbm_svc_async_fifo #(.WIDTH(2),.DEPTH(4)) u_fifo(
 .wr_clk(hbm_clk),.wr_rst_n(hbm_rst_n),.wr_valid(wr_valid),.wr_ready(wr_ready),.wr_data(din),.wr_overflow(wr_fault),
 .rd_clk(stream_clk),.rd_rst_n(stream_rst_n),.rd_valid(rv),.rd_ready(rd_ready),.rd_data(data),.rd_underflow(rd_fault));
 always @(posedge stream_clk)begin dout<=data;valid<=rv;end
endmodule
'''


def parent_spec():
    return dict(clock='multiple_cts_roots',kind='tile',top='audited_parent',
                clock_port='stream_clk',clock_ports=['stream_clk','hbm_clk'],
                sources=list(A.SOURCES)+['parent.sv'],params={},clock_data_paths='async_gray_fifo',
                clock_relationship=copy.deepcopy(A.RELATIONSHIP),clock_entry_domains=dict(
                    core=dict(ratio=[1,1],ports=['stream_clk'],inputs=['stream_rst_n','rd_ready'],outputs=['dout','valid','rd_fault']),
                    hbm=dict(ratio=[3072000,2499999],ports=['hbm_clk'],inputs=['hbm_rst_n','wr_valid','din'],outputs=['wr_ready','wr_fault'])))


def source_tree(root):
    root=Path(root)
    for f in A.SOURCES:
        p=root/f;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/f).read_bytes())
    (root/'parent.sv').write_text(PARENT)


@unittest.skipUnless(Path(YOSYS).exists()and Path(STA).exists(),'actual Yosys/OpenSTA tools required')
class ParentAdmission(unittest.TestCase):
    def test_actual_source_payload_targets_and_source_drift(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp);source_tree(root);s=parent_spec()
            normal=A.load(s,root)
            self.assertEqual(normal['verdict'],'PASS_SOURCE_GRAPH_ONLY')
            self.assertEqual(len(normal['fifo_instances']),1)
            self.assertEqual(normal['payload_consumer_public_nets']['u_fifo'],['dout[0]','dout[1]'])
            generated=C.generate(s,root)
            self.assertIn('set ::ot_ag_targets [dict create {u_fifo}',generated)
            self.assertNotIn('set_false_path',generated)
            # Additional synchronizer stages outside the FIFO are not an
            # alternative admission path, including for fault-only status.
            bad=PARENT.replace('always @(posedge stream_clk)begin dout<=data;valid<=rv;end',
                'reg bad_h,bad_s1,bad_s2;always @(posedge hbm_clk)bad_h<=din[0];\n'
                'always @(posedge stream_clk)begin bad_s1<=bad_h;bad_s2<=bad_s1;dout<=data;valid<=bad_s2;end')
            (root/'parent.sv').write_text(bad)
            with self.assertRaisesRegex(ValueError,'extra_crossing'):C.generate(s,root)

    def test_shared_input_clock_bypass_and_unknown_state_refused(self):
        mutations=[
            PARENT.replace('dout<=data','dout<=din'),
            PARENT.replace('dout<=data','dout<=data').replace('output wire wr_fault,rd_fault);','output wire wr_fault,rd_fault);\nreg [1:0] h;always @(posedge hbm_clk)h<=din;').replace('dout<=data','dout<=h'),
        ]
        for bad in mutations:
            with tempfile.TemporaryDirectory()as tmp:
                root=Path(tmp);source_tree(root);(root/'parent.sv').write_text(bad)
                with self.assertRaises(ValueError):C.generate(parent_spec(),root)
        # Declared output ownership is checked against actual produced values.
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp);source_tree(root);s=parent_spec()
            s['clock_entry_domains']['core']['outputs'].remove('dout')
            s['clock_entry_domains']['hbm']['outputs'].append('dout')
            with self.assertRaisesRegex(ValueError,'output_owner_mismatch'):C.generate(s,root)

    def test_reverse_direction_source_and_mapped_constraints(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp);source_tree(root);s=parent_spec()
            source=PARENT.replace('.wr_clk(hbm_clk),.wr_rst_n(hbm_rst_n)', '.wr_clk(stream_clk),.wr_rst_n(stream_rst_n)')
            source=source.replace('.rd_clk(stream_clk),.rd_rst_n(stream_rst_n)', '.rd_clk(hbm_clk),.rd_rst_n(hbm_rst_n)')
            source=source.replace('always @(posedge stream_clk)', 'always @(posedge hbm_clk)')
            (root/'parent.sv').write_text(source)
            ds=s['clock_entry_domains']
            ds['core'].update(inputs=['stream_rst_n','wr_valid','din'],outputs=['wr_ready','wr_fault'])
            ds['hbm'].update(inputs=['hbm_rst_n','rd_ready'],outputs=['dout','valid','rd_fault'])
            record=A.load(s,root)
            self.assertEqual(record['fifo_instances'][0]['writer_domain'],'core')
            self.assertEqual(record['fifo_instances'][0]['reader_domain'],'hbm')
            args='read_verilog -sv -DSYNTHESIS '+' '.join(str(root/f)for f in s['sources'])
            args+='; hierarchy -check -top audited_parent; synth -top audited_parent -flatten -noabc; dffunmap; abc -g simple; clean; write_json '+str(root/'parent.json')
            args+='; write_verilog -noattr -noexpr '+str(root/'mapped.v')
            p=subprocess.run([YOSYS,'-Q','-T','-p',args],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            module=json.loads((root/'parent.json').read_text())['modules']['audited_parent']
            (root/'probe.lib').write_text(fixture_lib(module))
            body=f'read_liberty {{{root}/probe.lib}}\nread_verilog {{{root}/mapped.v}}\nlink_design audited_parent\n'
            body+=C.clocks(s,833.333)+C.generate(s,root).rsplit('\not_ce_apply\n',1)[0]
            body+='\nset ins [dict create stream_rst_n core hbm_rst_n hbm wr_valid core rd_ready hbm {din[0]} core {din[1]} core]\n'
            body+='set outs [dict create wr_ready core {dout[0]} hbm {dout[1]} hbm valid hbm wr_fault core rd_fault hbm]\n'
            body+='if {[catch {ot_ce_leaf_ownership $ins $outs} message]} {puts stderr $message;exit 1}\nputs ACTUAL_REVERSE_PARENT_PASS\nexit 0\n'
            (root/'mapped.tcl').write_text(body)
            p=subprocess.run([STA,'-exit',str(root/'mapped.tcl')],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            self.assertIn('ACTUAL_REVERSE_PARENT_PASS',p.stdout+p.stderr)

    def test_build_defines_and_hard_define_are_explicitly_refused(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp);source_tree(root)
            normal='always @(posedge stream_clk)begin dout<=data;valid<=rv;end'
            bad='reg bad_h;always @(posedge hbm_clk)bad_h<=din[0];always @(posedge stream_clk)begin dout<=data;valid<=bad_h;end'
            (root/'parent.sv').write_text(PARENT.replace(normal,'`ifdef BYPASS\n'+bad+'\n`else\n'+normal+'\n`endif'))
            self.assertEqual(A.load(parent_spec(),root)['verdict'],'PASS_SOURCE_GRAPH_ONLY')
            for key,value in [('defines',['BYPASS']),('hard_define','BYPASS'),('hard_defines',['BYPASS']),('orfs_vars',{'VERILOG_DEFINES':'-DBYPASS'})]:
                candidate=parent_spec();candidate[key]=value
                with self.subTest(key=key),self.assertRaisesRegex(ValueError,'unsupported build defines'):
                    C.generate(candidate,root)

    def test_exact_payload_bit_and_control_pin_mutants(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp);source_tree(root);s=parent_spec()
            (root/'parent.sv').write_text(PARENT.replace('dout<=data',"dout<={1'b0,data[0]}").replace('valid<=rv','valid<=data[1]'))
            record=A.load(s,root)
            self.assertEqual(record['payload_consumer_bits']['u_fifo'],{'0':['dout[0]'],'1':['valid']})
            args='read_verilog -sv -DSYNTHESIS '+' '.join(str(root/f)for f in s['sources'])
            args+='; hierarchy -check -top audited_parent; synth -top audited_parent -flatten -noabc; dffunmap; abc -g simple; clean; write_json '+str(root/'parent.json')
            p=subprocess.run([YOSYS,'-Q','-T','-p',args],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            original=json.loads((root/'parent.json').read_text())
            for mutation in ('normal','new_vector_bit','wrong_payload_source_bit','async_control'):
                d=copy.deepcopy(original);m=d['modules']['audited_parent'];dout=m['netnames']['dout']['bits']
                template=next(c for c in m['cells'].values()if c['type'].startswith('$_DFF')and c['connections']['Q']==[dout[0]])
                if mutation=='new_vector_bit':
                    fresh=max(b for n in m['netnames'].values()for b in n['bits']if isinstance(b,int))+1
                    rogue=copy.deepcopy(template);rogue['connections']['Q']=[fresh]
                    rogue['connections']['D']=[m['netnames']['u_fifo.mem[0]']['bits'][0]]
                    m['cells']['rogue_new_payload_receiver']=rogue
                    m['ports']['dout']['bits'][1]=fresh;m['netnames']['dout']['bits'][1]=fresh
                elif mutation=='wrong_payload_source_bit':
                    template['connections']['D']=[m['netnames']['u_fifo.mem[0]']['bits'][1]]
                elif mutation=='async_control':
                    # A legitimate payload D receiver must not grant a new
                    # FIFO-payload path to that same receiver's async reset.
                    template['type']='$_DFF_PN0_'
                    template['connections']['R']=[m['netnames']['u_fifo.mem[0]']['bits'][0]]
                    template['port_directions']['R']='input'
                (root/'mapped.json').write_text(json.dumps(d));(root/'probe.lib').write_text(fixture_lib(m))
                p=subprocess.run([YOSYS,'-Q','-T','-p',f'read_json {root}/mapped.json; write_verilog -noattr -noexpr {root}/mapped.v'],capture_output=True,text=True)
                self.assertEqual(p.returncode,0,p.stdout+p.stderr)
                body=f'read_liberty {{{root}/probe.lib}}\nread_verilog {{{root}/mapped.v}}\nlink_design audited_parent\n'
                body+=C.clocks(s,833.333)+C.generate(s,root).rsplit('\not_ce_apply\n',1)[0]
                body+='\nset ins [dict create stream_rst_n core hbm_rst_n hbm wr_valid hbm rd_ready core {din[0]} hbm {din[1]} hbm]\n'
                # Pure constant dout[1] uses the existing OpenROAD/ODB constant proof,
                # outside this standalone STA data-graph fixture. Every actual
                # receiver D/control pin is still traversed, including mutants.
                body+='set outs [dict create wr_ready hbm {dout[0]} core valid core wr_fault hbm rd_fault core]\n'
                body+='if {[catch {ot_ce_leaf_ownership $ins $outs} message]} {puts stderr $message;exit 1}\nputs EXACT_BIT_GRAPH_PASS\nexit 0\n'
                (root/'mapped.tcl').write_text(body)
                p=subprocess.run([STA,'-exit',str(root/'mapped.tcl')],capture_output=True,text=True)
                if mutation=='normal':self.assertEqual(p.returncode,0,p.stdout+p.stderr)
                else:
                    self.assertNotEqual(p.returncode,0,mutation+'\n'+p.stdout+p.stderr)
                    self.assertIn('OT_ASYNC_GRAY:',p.stdout+p.stderr)

    def test_ascending_and_offset_vector_positive_and_swapped_bit_negative(self):
        for declaration,labels in [('[0:1]',['dout[1]','dout[0]']),('[4:5]',['dout[5]','dout[4]']),('[5:4]',['dout[4]','dout[5]'])]:
            with self.subTest(declaration=declaration),tempfile.TemporaryDirectory()as tmp:
                root=Path(tmp);source_tree(root);s=parent_spec()
                (root/'parent.sv').write_text(PARENT.replace('output reg [1:0] dout','output reg '+declaration+' dout'))
                record=A.load(s,root)
                self.assertEqual(record['payload_consumer_bits']['u_fifo'],{'0':[labels[0]],'1':[labels[1]]})
                args='read_verilog -sv -DSYNTHESIS '+' '.join(str(root/f)for f in s['sources'])
                args+='; hierarchy -check -top audited_parent; synth -top audited_parent -flatten -noabc; dffunmap; abc -g simple; clean; write_json '+str(root/'parent.json')
                p=subprocess.run([YOSYS,'-Q','-T','-p',args],capture_output=True,text=True)
                self.assertEqual(p.returncode,0,p.stdout+p.stderr)
                original=json.loads((root/'parent.json').read_text());m=original['modules']['audited_parent']
                (root/'probe.lib').write_text(fixture_lib(m))
                for mutant in (False,True):
                    data=copy.deepcopy(original);m=data['modules']['audited_parent']
                    if mutant:
                        for i,qb in enumerate(m['netnames']['dout']['bits']):
                            ff=next(c for c in m['cells'].values()if c['type'].startswith('$_DFF')and c['connections']['Q']==[qb])
                            ff['connections']['D']=[m['netnames']['u_fifo.mem[0]']['bits'][1-i]]
                    (root/'mapped.json').write_text(json.dumps(data))
                    p=subprocess.run([YOSYS,'-Q','-T','-p',f'read_json {root}/mapped.json; write_verilog -noattr -noexpr {root}/mapped.v'],capture_output=True,text=True)
                    self.assertEqual(p.returncode,0,p.stdout+p.stderr)
                    body=f'read_liberty {{{root}/probe.lib}}\nread_verilog {{{root}/mapped.v}}\nlink_design audited_parent\n'
                    body+=C.clocks(s,833.333)+C.generate(s,root).rsplit('\not_ce_apply\n',1)[0]
                    body+='\nset ins [dict create stream_rst_n core hbm_rst_n hbm wr_valid hbm rd_ready core {din[0]} hbm {din[1]} hbm]\n'
                    body+='set outs [dict create wr_ready hbm {'+labels[0]+'} core {'+labels[1]+'} core valid core wr_fault hbm rd_fault core]\n'
                    body+='if {[catch {ot_ce_leaf_ownership $ins $outs} message]} {puts stderr $message;exit 1}\nputs EXACT_DECLARATION_GRAPH_PASS\nexit 0\n'
                    (root/'mapped.tcl').write_text(body)
                    p=subprocess.run([STA,'-exit',str(root/'mapped.tcl')],capture_output=True,text=True)
                    if mutant:
                        self.assertNotEqual(p.returncode,0,p.stdout+p.stderr)
                        self.assertIn('unapproved actual crossing',p.stdout+p.stderr)
                    else:
                        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
                        self.assertIn('EXACT_DECLARATION_GRAPH_PASS',p.stdout+p.stderr)

    def test_ascending_offset_clock_bus_actual_source_ownership(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp);source_tree(root);s=parent_spec()
            source=PARENT.replace('input wire stream_clk,hbm_clk,stream_rst_n,hbm_rst_n,','input wire [4:5] clocks,input wire stream_rst_n,hbm_rst_n,')
            source=source.replace('.wr_clk(hbm_clk)', '.wr_clk(clocks[4])').replace('.rd_clk(stream_clk)', '.rd_clk(clocks[5])').replace('posedge stream_clk','posedge clocks[5]')
            (root/'parent.sv').write_text(source)
            s['clock_port']='clocks[5]';s['clock_ports']=['clocks[5]','clocks[4]']
            s['clock_entry_domains']['core']['ports']=['clocks[5]'];s['clock_entry_domains']['hbm']['ports']=['clocks[4]']
            record=A.load(s,root)
            self.assertEqual(record['fifo_instances'][0]['writer_domain'],'hbm')
            self.assertEqual(record['fifo_instances'][0]['reader_domain'],'core')
            self.assertIn('get_ports {clocks[5]}',C.clocks(s,833.333))

    def test_actual_mapped_parent_and_undeclared_payload_consumer_mutant(self):
        with tempfile.TemporaryDirectory()as tmp:
            root=Path(tmp);source_tree(root);s=parent_spec()
            args='read_verilog -sv -DSYNTHESIS '+' '.join(str(root/f)for f in s['sources'])
            args+='; hierarchy -check -top audited_parent; synth -top audited_parent -flatten -noabc; dffunmap; abc -g simple; clean; write_json '+str(root/'parent.json')
            p=subprocess.run([YOSYS,'-Q','-T','-p',args],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            original=json.loads((root/'parent.json').read_text());m=original['modules']['audited_parent']
            (root/'probe.lib').write_text(fixture_lib(m))
            for mutant in (False,True):
                d=copy.deepcopy(original);m=d['modules']['audited_parent']
                if mutant:
                    qb=m['netnames']['valid']['bits'][0]
                    ff=[c for c in m['cells'].values()if c['type'].startswith('$_DFF')and c['connections']['Q']==[qb]]
                    self.assertEqual(len(ff),1)
                    ff[0]['connections']['D']=[m['netnames']['u_fifo.mem[0]']['bits'][0]]
                (root/'mapped.json').write_text(json.dumps(d))
                p=subprocess.run([YOSYS,'-Q','-T','-p',f'read_json {root}/mapped.json; write_verilog -noattr -noexpr {root}/mapped.v'],capture_output=True,text=True)
                self.assertEqual(p.returncode,0,p.stdout+p.stderr)
                body=f'read_liberty {{{root}/probe.lib}}\nread_verilog {{{root}/mapped.v}}\nlink_design audited_parent\n'
                body+=C.clocks(s,833.333)+C.generate(s,root).rsplit('\not_ce_apply\n',1)[0]
                body+='\nset ins [dict create stream_rst_n core hbm_rst_n hbm wr_valid hbm rd_ready core {din[0]} hbm {din[1]} hbm]\n'
                body+='set outs [dict create wr_ready hbm {dout[0]} core {dout[1]} core valid core wr_fault hbm rd_fault core]\n'
                body+='if {[catch {ot_ce_leaf_ownership $ins $outs} message]} {puts stderr $message;exit 1}\nputs ACTUAL_PARENT_GRAPH_PASS\nexit 0\n'
                (root/'mapped.tcl').write_text(body)
                p=subprocess.run([STA,'-exit',str(root/'mapped.tcl')],capture_output=True,text=True)
                if mutant:
                    self.assertNotEqual(p.returncode,0,p.stdout+p.stderr)
                    self.assertIn('unapproved actual crossing',p.stdout+p.stderr)
                else:
                    self.assertEqual(p.returncode,0,p.stdout+p.stderr)
                    self.assertIn('ACTUAL_PARENT_GRAPH_PASS',p.stdout+p.stderr)


if __name__=='__main__':unittest.main()
