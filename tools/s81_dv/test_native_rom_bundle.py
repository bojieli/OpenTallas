import copy
import json
from pathlib import Path
import tempfile
import unittest
import native_rom_bundle as B


class Bundle(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        source=self.root/'xg.sv';source.write_text('module xg; ot_s81sl_xs4 u_s (); endmodule\n')
        self.names={};self.programmes=[]
        for n in range(2):
            sl=f'u_s_{n}S';base=self.root/sl;base.mkdir();frames=base/'frame_images';frames.mkdir()
            for key in B.XS:(base/(key+'.viamap.hex')).write_text(str(n)+'\n')
            (frames/(f'frame{n}.viamap.hex')).write_text(str(n)+'\n')
            p=dict(schema='opentallas.s81.aproj_native_programme.v1',slice=sl,op='L0.attn.a_proj',
                   status='PARTIAL',lifetime_qualified=False,sealed_programme_held=True,
                   selected_slice_source=dict(streamer='ot_s81sl_xs4',xg='xg',source_root=str(self.root),
                       source_sha256={'xg.sv':B.digest(source)},resolved_module_sources={'xg':'xg.sv'}))
            path=base/'programme.json';path.write_text(json.dumps(p));self.programmes.append(path)
            self.names[f's_{n}S_C.u_xg']=sl+'.u_sl.u_xg'
        self.report=dict(n_errors=0,errors=[],type_splits=[],instance_path_params=[
            dict(module='ot_rom_4096x72_m8',param='INSTANCE',value='"frame0"'),
            dict(module='ot_rom_4096x72_m8',param='INSTANCE',value='"uncompiled"')])

    def emit(self,**kwargs):
        return B.bundle(self.programmes,self.names,self.report,self.root/'bundle',**kwargs)

    def test_different_calendars_keep_distinct_runtime_keys(self):
        m=self.emit(dut='tb.dut')
        self.assertEqual(len(m['images']),16)
        self.assertEqual((self.root/'bundle/u_s_0S_pq_phase0.viamap.hex').read_text(),'0\n')
        self.assertEqual((self.root/'bundle/u_s_1S_pq_phase0.viamap.hex').read_text(),'1\n')
        text=(self.root/'bundle/instances.svh').read_text()
        self.assertIn('tb.dut.s_1S_C.u_xg.u_s.u_phase0.INSTANCE = "u_s_1S_pq_phase0"',text)
        self.assertEqual(m['missing_bound_images'],['uncompiled.viamap.hex'])
        self.assertEqual(len(m['missing_slice_programmes']),14)
        self.assertFalse(m['production_enabled'])
        self.assertTrue(all(p['sealed_programme_held'] for p in m['programmes']))

    def test_conflicting_frame_alias_does_not_silently_overwrite(self):
        f=self.programmes[1].parent/'frame_images/frame0.viamap.hex';f.write_text('MUTANT\n')
        with self.assertRaisesRegex(ValueError,'different image payloads'):self.emit()
        self.assertFalse((self.root/'bundle').exists())

    def test_bound_hierarchy_and_selected_source_mutants_refused(self):
        original=copy.deepcopy(self.names);self.names.pop('s_0S_C.u_xg')
        with self.assertRaisesRegex(ValueError,'one exact bound hierarchy'):self.emit()
        self.names=original
        (self.root/'xg.sv').write_text('module xg; wrong_streamer u_s (); endmodule\n')
        with self.assertRaisesRegex(ValueError,'source changed'):self.emit()

    def test_duplicate_programme_and_failed_bind_refused(self):
        self.programmes.append(self.programmes[0])
        with self.assertRaisesRegex(ValueError,'one native programme'):self.emit()
        self.programmes.pop();self.report['n_errors']=1
        with self.assertRaisesRegex(ValueError,'clean strict bind'):self.emit()


if __name__=='__main__':unittest.main()
