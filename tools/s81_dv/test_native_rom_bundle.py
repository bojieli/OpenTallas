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
        streamer=self.root/'xs.sv';streamer.write_text('\n'.join(f'ROM("{key}") {macro} ();' for key,macro in B.XS.items()))
        self.names={};self.programmes=[]
        for n in range(2):
            sl=f'u_s_{n}S';base=self.root/sl;base.mkdir();frames=base/'frame_images';frames.mkdir()
            for key in B.XS:(base/(key+'.viamap.hex')).write_text(str(n)+'\n')
            (frames/(f'frame{n}.viamap.hex')).write_text(str(n)+'\n')
            p=dict(schema='opentallas.s81.aproj_native_programme.v1',slice=sl,op='L0.attn.a_proj',
                   status='PARTIAL',lifetime_qualified=False,sealed_programme_held=True,
                   selected_slice_source=dict(streamer='ot_s81sl_xs4',xg='xg',source_root=str(self.root),
                       source_sha256={'xg.sv':B.digest(source),'xs.sv':B.digest(streamer)},resolved_module_sources={'xg':'xg.sv','ot_s81sl_xs4':'xs.sv'}))
            path=base/'programme.json';path.write_text(json.dumps(p));self.programmes.append(path)
            self.names[f's_{n}S_C.u_xg']=sl+'.u_sl.u_xg'
        self.names['frame_partition.u_frame']='frame0'
        self.report=dict(n_errors=0,errors=[],type_splits=[],instance_path_params=[
            dict(module='ot_rom_4096x72_m8',param='INSTANCE',inst='frame0',value='"frame0"'),
            dict(module='ot_rom_4096x72_m8',param='INSTANCE',value='"uncompiled"')])

    def emit(self,**kwargs):
        return B.bundle(self.programmes,self.names,self.report,self.root/'bundle',**kwargs)

    def test_different_calendars_keep_distinct_runtime_keys(self):
        m=self.emit(dut='tb.dut')
        self.assertEqual(len(m['images']),16)
        self.assertEqual((self.root/'bundle/u_s_0S_pq_phase0.viamap.hex').read_text(),'0\n')
        self.assertEqual((self.root/'bundle/u_s_1S_pq_phase0.viamap.hex').read_text(),'1\n')
        text=(self.root/'bundle/instances.svh').read_text()
        self.assertIn('tb.dut.s_1S_C.u_xg.u_s.u_phase0.VIAMAP',text)
        self.assertIn('u_s_1S_pq_phase0.viamap.hex',text)
        self.assertEqual(m['missing_bound_images'],['uncompiled.viamap.hex'])
        self.assertEqual(m['direct_viamap_macros'],15)
        self.assertIn('dut.frame_partition.u_frame.VIAMAP', (self.root/'bundle/direct_viamap.svh').read_text())
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

    def test_qx_actual_bound_shape_and_identity(self):
        key='u_f_0L01.u_r0.u_e0'
        self.report['instance_path_params'].append(dict(
            module='ot_v41_rom_elem_q_qxpq_w10',param='INSTANCE',inst=key,value='"'+key+'"'))
        self.names['fW0.u_elem']=key
        for suffix in ('_0','_1','b_0','b_1'):
            (self.programmes[0].parent/'frame_images'/(key+suffix+'.viamap.hex')).write_text(suffix+'\n')
        rom=self.root/B.QX_ROM;rom.parent.mkdir(parents=True);rom.write_text('module ot_rom_4096x274_m8;\n        else if (VIAMAP != "")\n            $readmemh(VIAMAP, arr);\nendmodule\n')
        top=self.root/'top.sv';top.write_text('module top;\n part #(.P_IMAGE("'+key+'")) fW0 ();\nendmodule\n')
        part=self.root/'part.sv'
        part.write_text('module part;\n ot_v41_rom_elem_q_qxpq_w10_gb #(.NB(2),.PP(1),.INSTANCE(P_IMAGE)) u_elem ();\nendmodule\n')
        m=self.emit(bound_top=top)
        self.assertEqual(m['direct_viamap_qx_banks'],4)
        text=(self.root/'bundle/direct_viamap.svh').read_text()
        self.assertNotIn('g_mac[',text)
        self.assertIn(str((self.root/'bundle'/key).resolve()),(self.root/'bundle/bind_rtl/top.sv').read_text())
        self.assertEqual(m['qx_bindings'][0]['banks'][3]['hierarchy'],'fW0.u_elem.u_e.g_mac[1].g_pp.u_rom1')
        self.assertEqual(m['qx_bindings'][0]['banks'][3]['image'],key+'b_1.viamap.hex')
        self.assertEqual(len(m['bound_rtl_overlays']),1)
        self.assertEqual(part.read_text(),'module part;\n ot_v41_rom_elem_q_qxpq_w10_gb #(.NB(2),.PP(1),.INSTANCE(P_IMAGE)) u_elem ();\nendmodule\n')
        # A different generated shape or parent image key must never reuse
        # guessed macro paths, even when all four files happen to exist.
        part.write_text(part.read_text().replace('.NB(2)','.NB(1)'))
        with self.assertRaisesRegex(ValueError,'NB2/PP1'):
            B.bundle(self.programmes,self.names,self.report,self.root/'wrong_shape',bound_top=top)
        part.write_text(part.read_text().replace('.NB(1)','.NB(2)'))
        top.write_text(top.read_text().replace(key,'wrong_image'))
        with self.assertRaisesRegex(ValueError,'identity differs'):
            B.bundle(self.programmes,self.names,self.report,self.root/'wrong_identity',bound_top=top)
        top.write_text('module top;\n part fW0 ();\nendmodule\n')
        part.write_text('module part;\n ot_v41_rom_elem_q_qxpq_w10_gb #(.NB(2),.PP(1),.INSTANCE("'+key+'")) u_elem ();\nendmodule\n')
        literal=B.bundle(self.programmes,self.names,self.report,self.root/'literal',bound_top=top)
        self.assertEqual(len(literal['bound_rtl_overlays']),1)
        self.assertIn(str((self.root/'literal'/key).resolve()),(self.root/'literal/bind_rtl/part.sv').read_text())
        self.assertIn('.NB(2),.PP(1)',(self.root/'literal/bind_rtl/part.sv').read_text())


if __name__=='__main__':unittest.main()
