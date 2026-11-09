"""Bounded source witness controls; no routed DRC or parent signoff claim."""
import importlib.util
from pathlib import Path
import unittest
import json
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/"tools/die_plan"))
import kit_contract as K
import gen_phys as GP
import clock_entry_pg

p=Path(__file__).with_name('prepare_access.py')
s=importlib.util.spec_from_file_location('prepare_access',p)
A=importlib.util.module_from_spec(s);s.loader.exec_module(A)


def fixture(extra=''):
    return '''MACRO core
 SIZE 10 BY 10 ;
 PIN ck
  PORT
   LAYER M5 ;
    RECT 4.9 4.7 5.1 5.3 ;
  END
 END ck
 '''+extra+'''
 OBS
  LAYER M6 ;
   RECT 0 0 4 10 ;
  LAYER M7 ;
   RECT 6 0 10 10 ;
 END
END core
'''

class Access(unittest.TestCase):
    footprints={5:[(4.98,4.98,5.02,5.02)],6:[(4.95,4.98,5.05,5.02)],7:[(4.98,4.616,5.02,5.384)]}
    def check(self,text,fp=None):
        b,t,_=A.G.geometry(text,'core','ck',7,(0,0,'MY'))
        return A.G.entry_clear(fp or self.footprints,b,t,7)
    def test_actual_rectangular_window(self): self.assertTrue(self.check(fixture()))
    def test_pg_is_obstruction(self):
        pg='PIN VDD\n PORT\n LAYER M6 ;\n RECT 4.99 4.99 5.01 5.01 ;\n END\nEND VDD'
        self.assertFalse(self.check(fixture(pg)))
    def test_blanket_obs_blocks(self):
        self.assertFalse(self.check(fixture().replace('RECT 0 0 4 10','RECT 0 0 10 10')))
    def test_wrong_pin_identity_rejected(self):
        with self.assertRaises(ValueError): self.check(fixture().replace('PIN ck','PIN other').replace('END ck','END other'))
    def test_missing_upper_obs_rejected(self):
        with self.assertRaises(ValueError): self.check(fixture().replace('LAYER M7','LAYER M4'))
    def test_missing_conductor_rejected(self):
        self.assertFalse(self.check(fixture(),{5:self.footprints[5],7:self.footprints[7]}))
    def test_lower_pad_must_fit_real_pin(self):
        fp=dict(self.footprints);fp[5]=[(4.8,4.9,5.05,5.1)]
        self.assertFalse(self.check(fixture(),fp))
    def test_unknown_geometry_rejected(self):
        with self.assertRaises(ValueError): self.check(fixture().replace('RECT 0 0 4 10','POLYGON 0 0 4 10'))
    def test_nonzero_origin_rejected(self):
        with self.assertRaises(ValueError): self.check(fixture().replace('SIZE 10','ORIGIN 1 0 ;\n SIZE 10'))
    def test_unsupported_orientation_rejected(self):
        with self.assertRaises(ValueError): A.G.geometry(fixture(),'core','ck',7,(0,0,'R90'))

class KitEntry(unittest.TestCase):
    def test_staged_plan_lef_and_real_emitted_pin(self):
        with tempfile.TemporaryDirectory() as td:
            kd=Path(td); (kd/'macros').mkdir()
            (kd/'macros/core.lef').write_text(fixture())
            access={'pin':'ck','footprints_um':{f'M{k}':v for k,v in Access.footprints.items()}}
            core={'inst':'u_core','module':'core','outline_um':[10,10],'origin_um':[0,0],
                  'orient':'MY','clock_entry_access':access}
            plan={'partition_types':{'type':{'hard_cores':[core]}}}
            (kd/'die_plan.json').write_text(json.dumps(plan))
            (kd/'macro.tcl').write_text('place_macro -macro_name u_core -location {0 0} -orientation MY\n')
            (kd/'config.mk').write_text('export MACRO_PLACEMENT_TCL = /work/macro.tcl\n')
            (kd/'io.tcl').write_text('place_pin -pin_name clk_c0 -layer M7 -location {5 5} -pin_size {0.04 0.768}\n')
            row={'port':'clk_c0','inst':'u_core','pin':'ck','clock_entry_access':access}
            budget={'schema':'opentallas.die_plan.partition_budget.v1','type':'type','signal_max':'M7','clock':{'core_taps':[row]}}
            (kd/'budget.json').write_text(json.dumps(budget))
            cuts=GP.clock_entry_pg_cuts(SimpleNamespace(types={'type':{'hard_cores':[core]}}),'type')
            (kd/'clock_entry_pg_cut.json').write_text(json.dumps({'schema':'opentallas.clock_entry_pg_cuts.v1','cuts':cuts}))
            (kd/'clock_entry_pg_cut.tcl').write_text(clock_entry_pg.render(cuts))
            (kd/'pg_island_cut.tcl').write_text(GP.pg_island_cut_tcl([('u_core','ck',(4.3,4.628,5.7,5.372))]))
            (kd/'post_pdn.tcl').write_text('source /work/pg_island_cut.tcl\nsource /work/clock_entry_pg_cut.tcl\n')
            with (kd/'config.mk').open('a') as f: f.write('export POST_PDN_TCL = /work/post_pdn.tcl\n')
            entries=[('io.tcl','clk_c0',5.,5.)]
            errors,_=K.clock_entry_clear(kd,kd,entries)
            self.assertEqual(errors,[])
            config=(kd/'config.mk').read_text()
            (kd/'config.mk').write_text(config.replace('export POST_PDN_TCL','export UNUSED_POST_PDN_TCL'))
            self.assertTrue(K.clock_entry_clear(kd,kd,entries)[0])
            (kd/'config.mk').write_text(config)
            # Default stays solid even though the LEF contains a real opening.
            row.pop('clock_entry_access')
            (kd/'budget.json').write_text(json.dumps(budget))
            self.assertTrue(K.clock_entry_clear(kd,kd,entries)[0])
            row['clock_entry_access']=dict(access,pin='other')
            (kd/'budget.json').write_text(json.dumps(budget))
            self.assertTrue(K.clock_entry_clear(kd,kd,entries)[0])

class GeneratorEntry(unittest.TestCase):
    def test_only_exact_selected_clock_can_enter(self):
        with tempfile.TemporaryDirectory() as td:
            lef=Path(td)/'core.lef'; lef.write_text(fixture())
            core={'inst':'u_core','module':'core','outline_um':[10,10],
                  'clock_entry_access':{'pin':'ck','footprints_um':{f'M{k}':v for k,v in Access.footprints.items()}}}
            p=SimpleNamespace(types={'type':{'hard_cores':[core]}},
                layer_budget={'partition_signal_max':'M7'},layers={'M7':{'dir':'V','width_um':.04}})
            macro=('u_core','core',str(lef),None,0,0,'MY')
            with patch.object(GP,'type_macros',return_value=[macro]), patch.object(GP,'core_tap_rows',return_value=[('clk_c0','u_core','ck',0,0)]):
                self.assertEqual(GP.entry_block_boxes(p,'type',root=td,port='clk_c0',entry_xy=(5,5)),[])
                self.assertEqual(GP.entry_block_boxes(p,'type',root=td,port='other',entry_xy=(5,5)),[(0.,0.,10.,10.)])
                self.assertEqual(GP.pg_island_cuts(p,'type',root=td),[('u_core','ck',(4.3,4.628,5.7,5.372))])
                core.pop('clock_entry_access')
                self.assertEqual(GP.pg_island_cuts(p,'type',root=td),[])
                self.assertEqual(GP.entry_block_boxes(p,'type',root=td,port='clk_c0',entry_xy=(5,5)),[(0.,0.,10.,10.)])
                # A legal named interior entry must not get moved away by the
                # default PG-safe snapping heuristic; targeted PG cuts own it.
                shifted={f'M{k}':[[r[0]+.024,r[1],r[2]+.024,r[3]] for r in boxes]
                         for k,boxes in Access.footprints.items()}
                core['clock_entry_access']={'pin':'ck','footprints_um':shifted}
                p.layers['M7'].update(offset_um=.032,pitch_um=.064)
                with patch.object(GP.S,'core_taps',return_value=[('clk_c0',5.024,5.,{})]), patch.object(GP,'_snap_tap',side_effect=AssertionError('must not move explicit target')):
                    self.assertEqual(GP.core_tap_pins(p,'type'),[('clk_c0',5.024,5.)])

class ParentSource(unittest.TestCase):
    def test_exact_one_leaf_param_event(self):
        ps=importlib.util.spec_from_file_location('prepare_parent',Path(__file__).with_name('prepare_parent.py'))
        P=importlib.util.module_from_spec(ps);ps.loader.exec_module(P)
        text='module parent;\n qfd_tile_nl_a0c u_t30 (.ck(clk_c1));\n other u_t31 (.ck(clk_c3));\nendmodule\n'
        result=P.explicit_idle(text)
        self.assertEqual(result.replace(' #(.IDLE_UCK(1))',''),text)
        for bad in (text.replace('u_t30','u_other'),text+text,result):
            with self.assertRaises(ValueError): P.explicit_idle(bad)

ROOT=Path(__file__).resolve().parents[3]
ADO=ROOT/'results/physical/qc_nl_clock_adoption_1551/access_v4'
BLANKET=fixture().replace('RECT 0 0 4 10','RECT 0 0 10 10').replace('RECT 6 0 10 10','RECT 0 0 10 10')
ACCESS={'pin':'ck','footprints_um':{f'M{k}':v for k,v in Access.footprints.items()}}


def plan_ns(core, contents=()):
    return SimpleNamespace(types={'type':{'hard_cores':[core],'contents':list(contents)}},
        layer_budget={'partition_signal_max':'M7'},
        layers={'M6':{'dir':'H','pitch_um':.064},'M7':{'dir':'V','width_um':.04,'pitch_um':.064}})


class DerivedAccessLef(unittest.TestCase):
    """DIE-QC-97 11-09: cbx_q10 NL DRT-0073; the kit staged the signed blanket-OBS LEF (sha c324040b)."""
    def test_reviewed_access_lef_by_construction(self):
        acc=(ADO/'qfd_tile_nl_a0c.access.lef').read_text(); ad=json.loads((ADO/'adoption.json').read_text())
        lines=acc.splitlines(keepends=True); out=[]; i=0
        while i<len(lines):
            if lines[i].startswith('      RECT '):
                while i<len(lines) and lines[i].startswith('      RECT '): i+=1
                out.append('     RECT  0 4.297 457.92 1153.463 ;\n')
            else: out.append(lines[i]); i+=1
        blanket=''.join(out)
        import hashlib
        self.assertEqual(hashlib.sha256(blanket.encode()).hexdigest(),ad['original_lef_sha256'])
        access={'pin':'ck','footprints_um':{f'M{k}':v for k,v in ad['parent_conductor_footprints'].items()}}
        new,cuts=A.G.derive_access_lef(blanket,'qfd_tile_nl_a0c',access,7,tuple(ad['parent_site']),{6:.064,7:.064})
        self.assertEqual((new,cuts),(acc,2))
        self.assertEqual(A.G.derive_access_lef(new,'qfd_tile_nl_a0c',access,7,tuple(ad['parent_site']),{6:.064,7:.064}),(acc,0))
    def test_blanket_fixture_opens_only_the_window(self):
        new,cuts=A.G.derive_access_lef(BLANKET,'core',ACCESS,7,(0,0,'MY'),{6:.064,7:.064})
        self.assertEqual(cuts,2)
        b,t,_=A.G.geometry(new,'core','ck',7,(0,0,'MY'))
        self.assertTrue(A.G.entry_clear(Access.footprints,b,t,7))
        b,t,_=A.G.geometry(BLANKET,'core','ck',7,(0,0,'MY'))
        self.assertFalse(A.G.entry_clear(Access.footprints,b,t,7))
    def test_pg_metal_in_window_still_blocks(self):
        pg='PIN VDD\n PORT\n LAYER M6 ;\n RECT 4.99 4.99 5.01 5.01 ;\n END\nEND VDD'
        text=BLANKET.replace(' OBS',pg+'\n OBS',1)
        new,_=A.G.derive_access_lef(text,'core',ACCESS,7,(0,0,'MY'),{6:.064,7:.064})
        b,t,_=A.G.geometry(new,'core','ck',7,(0,0,'MY'))
        self.assertFalse(A.G.entry_clear(Access.footprints,b,t,7))
    def test_gen_stages_access_lef_hard_core_over_shadowing_contents(self):
        with tempfile.TemporaryDirectory() as td:
            kd=Path(td)/'kit'; (kd/'macros').mkdir(parents=True)
            lef=Path(td)/'core.lef'; lef.write_text(BLANKET); (kd/'macros/core.lef').write_text(BLANKET)
            core={'inst':'u_core','module':'core','outline_um':[10,10],'orient':'MY','clock_entry_access':ACCESS}
            shadow={'inst':'u_core','module':'core_romleaf','outline_um':[10,10],'origin_um':[0,0]}
            p=plan_ns(core,[shadow])
            macro=('u_core','core',str(lef),None,0,0,'MY')
            with patch.object(GP,'type_macros',return_value=[macro]), patch.object(GP,'core_tap_rows',return_value=[('clk_c0','u_core','ck',0,0)]):
                # the hard core wins over the same-name contents entry; judged on the derived abstract
                self.assertEqual(GP.entry_block_boxes(p,'type',root=td,port='clk_c0',entry_xy=(5,5)),[])
                rows=GP.stage_clock_entry_lefs(p,'type',kd,[macro],Path)
            self.assertEqual(len(rows),1); self.assertEqual(rows[0]['obs_cuts'],2)
            staged=(kd/'macros/core.lef').read_text()
            self.assertEqual(staged,A.G.derive_access_lef(BLANKET,'core',ACCESS,7,(0,0,'MY'),{6:.064,7:.064})[0])
            rec=json.loads((kd/'clock_entry_lef.json').read_text())
            self.assertEqual(rec['schema'],'opentallas.clock_entry_lef.v1')
            # idempotent restage; a type without access writes nothing
            GP.stage_clock_entry_lefs(p,'type',kd,[macro],Path)
            self.assertEqual((kd/'macros/core.lef').read_text(),staged)
            core.pop('clock_entry_access'); (kd/'clock_entry_lef.json').unlink(); (kd/'macros/core.lef').write_text(BLANKET)
            self.assertEqual(GP.stage_clock_entry_lefs(p,'type',kd,[macro],Path),[])
            self.assertEqual((kd/'macros/core.lef').read_text(),BLANKET)
            self.assertFalse((kd/'clock_entry_lef.json').exists())
    def test_shared_lef_without_access_refused(self):
        with tempfile.TemporaryDirectory() as td:
            kd=Path(td)/'kit'; (kd/'macros').mkdir(parents=True)
            lef=Path(td)/'core.lef'; lef.write_text(BLANKET); (kd/'macros/core.lef').write_text(BLANKET)
            core={'inst':'u_core','module':'core','outline_um':[10,10],'orient':'MY','clock_entry_access':ACCESS}
            twin={'inst':'u_twin','module':'core','outline_um':[10,10],'orient':'MY'}
            p=plan_ns(core); p.types['type']['hard_cores'].append(twin)
            ms=[('u_core','core',str(lef),None,0,0,'MY'),('u_twin','core',str(lef),None,20,0,'MY')]
            with self.assertRaises(ValueError): GP.stage_clock_entry_lefs(p,'type',kd,ms,Path)

    def test_preflight_judges_hard_core_over_shadowing_contents(self):
        with tempfile.TemporaryDirectory() as td:
            kd=Path(td); (kd/'macros').mkdir()
            (kd/'macros/core.lef').write_text(fixture())
            core={'inst':'u_core','module':'core','outline_um':[10,10],'origin_um':[0,0],'orient':'MY','clock_entry_access':ACCESS}
            shadow={'inst':'u_core','module':'core_romleaf','outline_um':[10,10],'origin_um':[0,0]}
            (kd/'die_plan.json').write_text(json.dumps({'partition_types':{'type':{'hard_cores':[core],'contents':[shadow]}}}))
            (kd/'budget.json').write_text(json.dumps({'type':'type'}))
            self.assertEqual(K._plan_contents(kd,kd)['u_core']['module'],'core_romleaf')   # default order unchanged
            self.assertEqual(K._plan_contents(kd,kd,prefer_hard=True)['u_core']['module'],'core')


class ReapplyEvent(unittest.TestCase):
    def test_qc52_reapply_equals_reviewed_qc52n(self):
        spec=importlib.util.spec_from_file_location('reapply_event',Path(__file__).with_name('reapply_event.py'))
        R=importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
        por=ROOT/'physical/die_plan/qwen_compute/plan_of_record'
        base=json.loads((por/'plan_qc52.json').read_text())
        ops=json.loads((ADO/'proposed_event.patch.json').read_text())
        self.assertEqual(R.apply(base,ops),json.loads((por/'plan_qc52n.json').read_text()))
        with self.assertRaises(ValueError): R.apply(R.apply(base,ops),ops)   # already applied: test op fails

if __name__=='__main__': unittest.main()
