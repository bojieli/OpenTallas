"""Constrained fixture uses a real historical M6 PORT, not a claimed closed M5 master.

Source vm_cp_rb2-cp1-2370c0876, LEF SHA256
17aa1263363fd7e3d4084d39853a0a47772507fd04830032a8fa1f9af8871669:
ei[1001] E/M6 RECT21.53 293.12 21.6 293.152. Surrounding M5 PG/DEF is
synthetic, because no closed M5-wire/PG + M6-pin fixture currently exists.
"""
import copy
import json
import re
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import child_lint as CL
import m6_pin_grant as M6

LEF = '''MACRO fixture
 SIZE 21.6 BY 324 ;
 PIN ei[1001]
  DIRECTION INPUT ;
  USE SIGNAL ;
  PORT
   LAYER M6 ;
    RECT 21.53 293.12 21.6 293.152 ;
  END
 END ei[1001]
 PIN VDD
  USE POWER ;
  PORT
   LAYER M5 ;
    RECT 0 20 21.6 20.1 ;
    RECT 0 304 21.6 304.1 ;
  END
 END VDD
 PIN VSS
  USE GROUND ;
  PORT
   LAYER M5 ;
    RECT 0 19 21.6 19.1 ;
    RECT 0 303 21.6 303.1 ;
  END
 END VSS
END fixture
'''
DEF = '''VERSION 5.8 ;
DESIGN fixture ;
UNITS DISTANCE MICRONS 1000 ;
VIAS 1 ;
- contact + RECT M5 ( -70 -16 ) ( 0 16 )
 + RECT V5 ( -40 -10 ) ( -20 10 )
 + RECT M6 ( -70 -16 ) ( 0 16 ) ;
END VIAS
PINS 1 ;
- ei[1001] + NET ei[1001] + DIRECTION INPUT + USE SIGNAL
 + LAYER M6 ( -70 -16 ) ( 0 16 ) + FIXED ( 21600 293136 ) N ;
END PINS
NETS 1 ;
- ei[1001] ( PIN ei[1001] )
 + ROUTED M5 ( 20000 293136 ) ( 21600 * ) contact ;
END NETS
SPECIALNETS 0 ;
END SPECIALNETS
END DESIGN
'''
GRANT = {'schema': M6.SCHEMA, 'master': 'fixture', 'granted_by': 'test die lead',
         'reason': 'constrained edge-access test, no live grant', 'source_commit': 'a'*40,
         'source_spec_sha256': 'b'*64, 'ports': [{'name': 'ei[1001]', 'face': 'E',
         'span_um': [293.12,293.152], 'max_depth_um': .07, 'max_area_um2': .003}]}


class GrantTests(unittest.TestCase):
    def lint(self, lef=LEF, routed=DEF, grant=GRANT, tech=None, **kw):
        with tempfile.TemporaryDirectory() as td:
            p, d = Path(td)/'fixture.lef', Path(td)/'fixture.def'
            p.write_text(lef)
            if routed is not None:
                d.write_text(routed)
            if tech is not None:
                t = Path(td)/"tech.lef"
                t.write_text(tech)
                kw["tech_lef"] = str(t)
            return CL.lint(str(p), cap='M5', pin_grant=grant,
                           routed_def=str(d) if routed is not None else None, **kw)

    def test_actual_port_geometry_with_m5_pg_and_local_contact(self):
        r = self.lint()
        self.assertEqual(r['fails'], [])
        self.assertEqual(r['verdict'], 'PASS')
        self.assertEqual(r['info']['cap'], 'M5')
        self.assertEqual(r['info']['m6_pin_grant']['m6_ports'], ['ei[1001]'])

    def test_without_grant_existing_cap_rejects_m6(self):
        self.assertEqual(self.lint(grant=None)['verdict'], 'FAIL')

    def test_negative_m6_power(self):
        self.assertEqual(self.lint(lef=LEF.replace('LAYER M5', 'LAYER M6'))['verdict'], 'FAIL')

    def test_def_power_use_cannot_be_hidden_by_lef(self):
        self.assertEqual(self.lint(routed=DEF.replace('USE SIGNAL','USE POWER'))['verdict'], 'FAIL')

    def test_negative_obs_cannot_be_hidden_as_access(self):
        lef = LEF.replace('END fixture', ' OBS\n LAYER M6 ;\n RECT 21.53 293.12 21.6 293.152 ;\n END\nEND fixture')
        self.assertEqual(self.lint(lef=lef)['verdict'], 'FAIL')

    def test_negative_m6_nonpin_wire_even_if_abstract_strips_it(self):
        self.assertEqual(self.lint(routed=DEF.replace('ROUTED M5', 'ROUTED M6'))['verdict'], 'FAIL')

    def test_m6_wire_rectangle_must_fit_own_terminal(self):
        tech = "LAYER M6\n TYPE ROUTING ;\n WIDTH 0.032 ;\nEND M6\n"
        legal = DEF.replace('ROUTED M5 ( 20000 293136 ) ( 21600 * ) contact',
                            'ROUTED M6 ( 21546 293136 0 ) ( 21584 * 0 )')
        self.assertEqual(self.lint(routed=legal, tech=tech)['verdict'], 'PASS')
        for bad in (legal.replace('21546', '21529'),
                    legal.replace('293136 0', '293137 0'),
                    legal.replace('( 21584 * 0 )', '( 21601 * 0 )'),
                    legal.replace('M6 ( 21546', 'M7 ( 21546')):
            self.assertEqual(self.lint(routed=bad, tech=tech)['verdict'], 'FAIL')
        self.assertEqual(self.lint(routed=legal)['verdict'], 'FAIL')
        ndr = legal.replace('PINS 1 ;', 'NONDEFAULTRULES 1 ;\n- wide + LAYER M6 WIDTH 64 ;\nEND NONDEFAULTRULES\nPINS 1 ;')
        ndr = ndr.replace('+ ROUTED M6', '+ NONDEFAULTRULE wide + ROUTED M6')
        self.assertEqual(self.lint(routed=ndr, tech=tech)['verdict'], 'FAIL')

        # Default endpoint caps count as wire geometry too.
        self.assertEqual(self.lint(routed=legal.replace('( 21546 293136 0 )', '( 21546 293136 )')
                                  .replace('( 21584 * 0 )', '( 21584 * )'), tech=tech)['verdict'], 'PASS')

    def test_negative_m7_and_unknown_grant_port(self):
        for lef in [LEF.replace('LAYER M6', 'LAYER M7')]:
            self.assertEqual(self.lint(lef=lef)['verdict'], 'FAIL')
        g = copy.deepcopy(GRANT)
        g['ports'][0]['name'] = 'unknown[7]'
        self.assertEqual(self.lint(grant=g)['verdict'], 'FAIL')

    def test_negative_missing_def_mismatch_and_area_waiver(self):
        self.assertEqual(self.lint(routed=None)['verdict'], 'FAIL')
        self.assertEqual(self.lint(routed=DEF.replace('( -70 -16 ) ( 0 16 ) + FIXED', '( -700 -16 ) ( 0 16 ) + FIXED'))['verdict'], 'FAIL')
        self.assertEqual(self.lint(lef=LEF.replace('21.53 293.12', '20.53 293.12'))['verdict'], 'FAIL')

    def test_via_cannot_add_hidden_m7_or_leave_contact(self):
        self.assertEqual(self.lint(routed=DEF.replace('RECT M6', 'RECT M7'))['verdict'], 'FAIL')
        self.assertEqual(self.lint(routed=DEF.replace('( 21600 * ) contact', '( 21500 * ) contact'))['verdict'], 'FAIL')
        self.assertEqual(self.lint(routed=DEF.replace('contact ;', 'unknown ;'))['verdict'], 'FAIL')

    def test_rotated_or_array_contact_cannot_hide_geometry(self):
        self.assertEqual(self.lint(routed=DEF.replace('contact ;','contact E ;'))['verdict'], 'FAIL')
        self.assertEqual(self.lint(routed=DEF.replace('contact ;','contact DO 2 BY 1 STEP 100 0 ;'))['verdict'], 'FAIL')

    def test_exact_read_tech_via_geometry(self):
        technology = """VIA contact DEFAULT
 LAYER M5 ;
 RECT -0.07 -0.016 0 0.016 ;
 LAYER V5 ;
 RECT -0.04 -0.01 -0.02 0.01 ;
 LAYER M6 ;
 RECT -0.07 -0.016 0 0.016 ;
END contact
"""
        routed = re.sub(r'VIAS 1 ;.*?END VIAS', 'VIAS 0 ;\\nEND VIAS', DEF, flags=re.S)
        self.assertEqual(self.lint(routed=routed,tech=technology)['verdict'], 'PASS')
        self.assertEqual(self.lint(routed=routed,tech=technology.replace('LAYER M6','LAYER M7'))['verdict'], 'FAIL')

    def test_generated_rule_via_only_allowed_below_cap(self):
        for layer in ('M5','M6'):
            routed = DEF.replace('VIAS 1 ;', 'VIAS 2 ;\n- lowgen + VIARULE M5_M4 + LAYERS M4 V4 ' + layer + ' ;')
            routed = routed.replace('( 20000 293136 )', '( 20000 293136 ) lowgen')
            self.assertEqual(self.lint(routed=routed)['verdict'], 'PASS' if layer == 'M5' else 'FAIL')

    def test_skips_cannot_override_pin_only_evidence(self):
        self.assertEqual(self.lint(routed=None, skip=set('abcdefg'))['verdict'], 'FAIL')

    def test_normalized_kit_preserves_granted_source_digest(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'ref_tile'))
        import ref_tile as RT
        spec = {'name':'fixture','top':'fixture','sources':['AGENTS.md'], 'clock_port':'ck',
                'pins':{'W':['ck']}, 'outline':{'w':43.2,'h':43.2},
                'layer_cap':'M5','route':{'pin_h':'M4 M6'}}
        grant = copy.deepcopy(GRANT)
        import subprocess
        grant['source_commit'] = subprocess.check_output(['git','-C',str(RT.ROOT),'rev-parse','HEAD'],text=True).strip()
        grant['source_spec_sha256'] = M6.spec_digest(spec)
        spec['m6_pin_grant'] = grant
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/'source.json'
            p.write_text(json.dumps(spec))
            # Actual generation plus regeneration of the saved kit. Only the unused bench lint is mocked.
            with patch.object(RT,'lint_cmd', return_value='true'):
                result = RT.gen(str(p), out_root=Path(td))
                with patch.object(Path, 'read_bytes', return_value=b'changed approved source'):
                    with self.assertRaises(RT.SpecError):
                        RT.gen(str(p), write=False)
                saved = Path(td)/result['kit']/'spec.json'
                RT.gen(str(saved), write=False)
                changed = json.loads(saved.read_text())
                changed['outline']['w'] = 86.4
                saved.write_text(json.dumps(changed))
                with self.assertRaises(RT.SpecError):
                    RT.gen(str(saved), write=False)

    def test_spec_and_generated_contract_stay_m5(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'ref_tile'))
        import ref_tile as RT
        spec = {'name':'fixture','top':'fixture','kind':'tile','layer_cap':'M5',
                'route':{'pin_h':'M4 M6'},'m6_pin_grant':GRANT}
        lc = RT.layer_contract(spec, None)
        self.assertEqual(lc['rlayers'], ('M2','M5'))
        self.assertEqual(lc['pg_layer'], 'M5')
        self.assertEqual(RT.pin_layers(spec,lc), ('M4 M6','M5'))
        with self.assertRaises(RT.SpecError):
            RT.layer_contract(dict(spec, layer_cap='M6'),None)
        with self.assertRaises(RT.SpecError):
            RT.pin_layers(dict(spec,route={'pin_h':'M7'}),lc)
        self.assertEqual(M6.spec_digest(spec), M6.spec_digest(dict(spec,m6_pin_grant={})))
        self.assertNotEqual(M6.spec_digest(spec), M6.spec_digest(dict(spec,top='changed')))


if __name__ == '__main__':
    unittest.main()
