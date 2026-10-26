"""Exact ORFS corner library selection, including ambiguous-install controls."""
from pathlib import Path
import json
import subprocess
import tempfile
import unittest

HERE = Path(__file__).parent


class ExactTimingLibraries(unittest.TestCase):
    def probe(self, change='', output=None, load=False):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            files=[]
            for group, version in [('AO','211120'),('INVBUF','220122'),('OA','211120'),('SEQ','220123'),('SIMPLE','211120')]:
                p=root/f'asap7sc7p5t_{group}_RVT_TT_nldm_{version}.lib'
                p.write_text('fixture')
                files.append(str(p))
            newer=root/'asap7sc7p5t_SIMPLE_RVT_TT_nldm_250407.lib';newer.touch()
            wrong=root/'child_ff.lib';wrong.touch()
            config=root/'config.mk';config.write_text('export PLATFORM = asap7\n')
            words=' '.join(files)
            output=output if output is not None else f'TC_LIB_FILES: {words}'
            script='source {'+str(HERE/'timing_libs.tcl')+'}\n'
            script+='set files {'+words+'}\nset newer {'+str(newer)+'}\nset wrong {'+str(wrong)+'}\n'
            script+=change+'\n'
            if load:
                script+='set make_output {'+output+'}\nrename exec native_exec\nproc exec {args} {if {[lindex $args 0] eq "bash"} {return $::make_output};return [native_exec {*}$args]}\n'
                script+='set loaded {}\nproc read_liberty {f} {lappend ::loaded $f}\n'
                script+='ot_lib_load TT {'+str(root/'receipt.json')+'} {'+str(config)+'}\nputs "LOADED_COUNT [llength $loaded]"\n'
            else: script+='ot_lib_validate TT $files\nputs VALIDATED\n'
            # tclsh stdin reports errors without nonzero exit; script-file execution does not.
            p=root/'test.tcl';p.write_text(script)
            result=subprocess.run(['tclsh',str(p)],text=True,capture_output=True)
            receipt=json.loads((root/'receipt.json').read_text()) if (root/'receipt.json').exists() else None
            return result,receipt

    def test_exact_selected_versions_ignore_installed_newer(self):
        r,d=self.probe(load=True)
        self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(len(d['libraries']),5)
        self.assertEqual(d['status'],'LOADED')
        self.assertTrue(all('250407' not in x['path'] for x in d['libraries']))
        self.assertTrue(all(len(x['sha256'])==64 for x in d['libraries']))

    def test_standalone_tools_embed_identical_selector_without_sibling(self):
        import ast
        canonical=(HERE/'timing_libs.tcl').read_text()
        tree=ast.parse((HERE/'signoff.py').read_text())
        values=[ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='EXACT_TIMING_LIBRARIES_TCL' for t in n.targets)]
        self.assertEqual(values,[canonical])
        post=(HERE/'postcts_gate.tcl').read_text()
        self.assertEqual(post.split('# BEGIN embedded exact library selector\n',1)[1].split('# END embedded exact library selector',1)[0],canonical)
        self.assertNotIn('source [file join [file dirname [info script]] timing_libs.tcl]',post)

    def test_postgate_selector_does_not_need_sibling_file(self):
        prefix=(HERE/'postcts_gate.tcl').read_text().split('# END embedded exact library selector',1)[0]
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'postcts_gate.tcl'
            p.write_text('set ::env(OT_CORNER) TT\n'+prefix+'\nputs "SELECTOR [llength [info commands ot_lib_load]]"\n')
            result=subprocess.run(['tclsh',str(p)],text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('SELECTOR 1',result.stdout)
            self.assertFalse((Path(td)/'timing_libs.tcl').exists())

    def test_explicit_corner_macro_is_kept(self):
        result,_=self.probe('set tt [file join [file dirname $wrong] child_tt.lib];file rename $wrong $tt;lappend files $tt')
        self.assertEqual(result.returncode,0,result.stderr)

    def test_empty_list_rejected(self):
        r,_=self.probe('set files {}');self.assertNotEqual(r.returncode,0)
    def test_ambiguous_versions_rejected(self):
        r,_=self.probe('lappend files $newer');self.assertIn('ambiguous installed versions',r.stderr)
    def test_duplicate_path_rejected(self):
        r,_=self.probe('lappend files [lindex $files 0]');self.assertIn('duplicate library',r.stderr)
    def test_wrong_macro_corner_rejected(self):
        r,_=self.probe('lappend files $wrong');self.assertIn('wrong macro corner',r.stderr)
    def test_missing_file_rejected(self):
        r,_=self.probe('file delete [lindex $files 0]');self.assertIn('missing or unresolved',r.stderr)
    def test_missing_group_rejected(self):
        r,_=self.probe('set files [lrange $files 1 end]');self.assertIn('missing standard-cell group AO',r.stderr)
    def test_missing_make_record_rejected(self):
        r,d=self.probe(output='unrelated output',load=True);self.assertNotEqual(r.returncode,0);self.assertIsNone(d)
    def test_ambiguous_make_record_rejected(self):
        r,d=self.probe(output='TC_LIB_FILES: a\nTC_LIB_FILES: b',load=True);self.assertIn('ambiguous make',r.stderr);self.assertIsNone(d)


if __name__=='__main__':unittest.main()
