"""Changed-parent reuse must not hide changed arithmetic, ABI or compile inputs."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC=importlib.util.spec_from_file_location('hbm_compile',Path(__file__).resolve().parents[1]/'tools/hbm_integrated_formatter_parent_compile.py')
R=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(R)

class ComponentReuse(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.work=Path(self.tmp.name)/'old';(self.work/'src').mkdir(parents=True)
        texts={'pkg.sv':'package types; typedef logic [7:0] word_t; endpackage\n',
               'parent.sv':'module parent(input x, output y); leaf u(x,y); endmodule\n',
               'leaf.sv':'module leaf(input x, output y); helper u(x,y); endmodule\n',
               'helper.sv':'module helper(input x, output y); assign y=x; endmodule\n',
               'norm.sv':'module norm(input x, output y); assign y=x; endmodule\n'}
        self.m={'sources':list(texts),'source_sha256':{}}
        for p,text in texts.items():self.edit(p,text)
        (self.work/'src/hierarchy.vlt').write_text('`verilator_config\nhier_block -module "leaf"\nhier_block -module "helper"\n')
        self.jobs=[]
        for name,deps in [('helper',[]),('leaf',['Vhelper']),('norm',[]),('parent',['Vleaf','Vnorm'])]:
            args=self.work/(name+'.f');args.write_text(f'--cc\n--top-module-encoded {name}\n--hierarchical-block {name},{name}\n-GWIDTH=8\n-Wno-fatal\n')
            self.jobs.append(dict(prefix='V'+name,top=name,directory=str(self.work/'obj'/('V'+name)),verilator_args=str(args),deps=deps,sources=[]))
        self.tool={'bin/verilator':'wrapper','bin/verilator_bin':'compiler','include/runtime.h':'runtime'}
    def edit(self,p,text):
        path=self.work/'src'/p;path.write_text(text);self.m['source_sha256'][p]=R.sha(path)
    def contracts(self):return R.component_contracts(self.work,self.m,self.jobs,self.tool)
    def test_changed_parent_and_norm_keep_independent_leaf(self):
        before=self.contracts()
        self.edit('parent.sv','module parent(input x, output y); leaf u(x,y); wire [72:0] protected_frame; endmodule\n')
        self.edit('norm.sv','module norm(input x, output y); assign y=~x; endmodule\n')
        after=self.contracts()
        self.assertEqual(before['Vleaf'],after['Vleaf'])
        self.assertNotEqual(before['Vnorm'],after['Vnorm'])
        self.assertNotEqual(before['Vparent'],after['Vparent'])
    def test_transitive_implementation_change_rejects_leaf(self):
        before=self.contracts();self.edit('helper.sv','module helper(input x, output y); assign y=~x; endmodule\n')
        self.assertNotEqual(before['Vleaf'],self.contracts()['Vleaf'])
    def test_package_change_rejects_leaf(self):
        before=self.contracts();self.edit('pkg.sv','package types; typedef logic [15:0] word_t; endpackage\n')
        self.assertNotEqual(before['Vleaf'],self.contracts()['Vleaf'])
    def test_preprocessor_context_change_rejects_leaf(self):
        before=self.contracts();self.edit('parent.sv','`define NEW_ABI 1\n'+(self.work/'src/parent.sv').read_text())
        self.assertNotEqual(before['Vleaf'],self.contracts()['Vleaf'])
    def test_parameters_defines_and_child_binding_reject(self):
        before=self.contracts()
        args=Path(self.jobs[0]['verilator_args']);args.write_text(args.read_text().replace('-GWIDTH=8','-GWIDTH=16')+'-DOTHER=1\n')
        self.assertNotEqual(before['Vleaf'],self.contracts()['Vleaf'])
    def test_tool_or_runtime_change_rejects(self):
        before=self.contracts();self.tool['include/runtime.h']='changed'
        self.assertNotEqual(before['Vleaf'],self.contracts()['Vleaf'])
    def test_header_and_generated_hierarchy_tampering_rejects(self):
        j=self.jobs[1];directory=Path(j['directory']);directory.mkdir(parents=True)
        for name in ['Vleaf.cpp','Vleaf.h','leaf.sv']:(directory/name).write_text(name)
        terminal=directory/'terminal.json';terminal.write_text('{"exit":0}')
        c=self.contracts()['Vleaf'];model=dict(contract_sha256=R.digest(c),directory=str(directory),terminal=str(terminal),terminal_sha256=R.sha(terminal),artifacts={p.name:R.sha(p) for p in directory.iterdir()},interfaces={},parse_only_diagnostics=[])
        out=self.work/'out';out.mkdir()
        for name in ['Vleaf.h','leaf.sv']:
            original=(directory/name).read_text();(directory/name).write_text('stale ABI')
            with self.assertRaises(ValueError):R.reuse_component(j,c,{'models':{'Vleaf':model}},out)
            (directory/name).write_text(original)
        self.assertTrue(R.reuse_component(j,c,{'models':{'Vleaf':model}},out))
    def test_verilator_encoded_private_namespace(self):
        self.edit('private.sv','module native__exp(input x, output y); assign y=x; endmodule\n')
        self.m['sources'].append('private.sv')
        args=self.work/'private.f';args.write_text('--cc\n--hierarchical-block native___05Fexp,native___05Fexp_1\n')
        self.jobs.append(dict(prefix='Vprivate',top='native___05Fexp_1',directory=str(self.work/'private'),verilator_args=str(args),deps=[],sources=[]))
        self.assertEqual(self.contracts()['Vprivate']['original_module'],'native__exp')
    def test_own_include_content_change_rejects(self):
        self.edit('constant.svh','`define VALUE 1\n')
        self.edit('helper.sv','`include "constant.svh"\nmodule helper(input x,output y);assign y=`VALUE;endmodule\n')
        before=self.contracts();self.edit('constant.svh','`define VALUE 0\n')
        self.assertNotEqual(before['Vhelper'],self.contracts()['Vhelper'])
    def test_generation_time_input_replacement_rejects(self):
        d=self.work/'generated';d.mkdir();binary=self.work/'verilator_bin';binary.write_text('original')
        st=binary.stat();record=d/'Vleaf__verFiles.dat'
        record.write_text(f'S {st.st_size} {st.st_ino} 0 0 {st.st_mtime_ns//10**9} {st.st_mtime_ns%10**9} "unhashed" "{binary}"\n')
        self.assertIn(str(binary),R.recorded_dependencies(d,'Vleaf'))
        binary.write_text('changed implementation')
        with self.assertRaises(ValueError):R.recorded_dependencies(d,'Vleaf')
    def test_macro_constructed_module_refuses_enrollment(self):
        self.edit('parent.sv','`define MOD(x) name``x\nmodule parent; endmodule\n')
        with self.assertRaises(ValueError):self.contracts()

if __name__=='__main__':unittest.main()
