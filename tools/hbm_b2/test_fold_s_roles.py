#!/usr/bin/env python3
"""TOK-HBM-4: fold-map VERIFY mode of tools/hbm_b2/fold_s_roles.py (fail closed). A synthetic composed top with one N hub
(q0 port free, q1 port read by the N client) and two open S inputs; one positive map and one must-fail map per check."""
import json, os, subprocess, sys, tempfile, unittest

TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fold_s_roles.py')
TOP = '''module t (hb_x_SE__rq, hleaf_SE__cfg);
  input wire [7:0] hb_x_SE__rq;
  input wire [3:0] hleaf_SE__cfg;
  wire [7:0] hb_x_NE__rq_q0;
  wire [7:0] hb_x_NE__rq;
  wire [3:0] hb_x_NE__cfg;
  wire [0:0] y;
  ot_hub #(.Q(1)) hb_x_NE (
    .rq_q0(hb_x_NE__rq_q0[7:0]),
    .rq(hb_x_NE__rq[7:0]),
    .cfg(hb_x_NE__cfg[3:0])
  );
  ot_cli cl_NE (
    .rq(hb_x_NE__rq[7:0]),
    .cfg(hb_x_NE__cfg[3:0])
  );
  ot_cli cl_SE (
    .rq(hb_x_SE__rq[7:0]),
    .cfg(hleaf_SE__cfg[3:0])
  );
  ot_sm sm_NW0 (
    .y(y[0:0])
  );
endmodule
'''
CEN = {'nets': [{'net': 'hb_x_SE__rq', 'width': 8, 'mirror_driver': None}, {'net': 'hleaf_SE__cfg', 'width': 4, 'mirror_driver': None}]}
GOOD = {'hb_x_SE__rq': {'src_instance': 'hb_x_NE', 'src_port': 'rq_q0', 'leg': 'L1'},
        'hleaf_SE__cfg': {'src_instance': 'hb_x_NE', 'src_port': 'cfg', 'broadcast': True}}

def run(nets, tmp):
    for n, c in (('top.sv', TOP), ('cen.json', json.dumps(CEN)), ('map.json', json.dumps({'schema': 'opentallas.hbm.s_fold_map.v1', 'nets': nets}))):
        open(os.path.join(tmp, n), 'w').write(c)
    r = subprocess.run([sys.executable, '-I', TOOL, f'{tmp}/top.sv', f'{tmp}/cen.json', f'{tmp}/o', '--map', f'{tmp}/map.json'], capture_output=True, text=True)
    return r.returncode, json.load(open(f'{tmp}/o.json')), open(f'{tmp}/o.svh').read()

class T(unittest.TestCase):
    def go(self, nets):
        with tempfile.TemporaryDirectory() as d: return run(nets, d)
    def bad(self, nets, code):
        rc, rep, _ = self.go(nets)
        self.assertEqual((rc, rep['verdict']), (2, 'FAIL_CLOSED')); self.assertIn(code, rep['errors'])
    def test_positive(self):
        rc, rep, svh = self.go(GOOD)
        self.assertEqual((rc, rep['verdict'], rep['errors'], rep['sm_instances'], rep['legs_named']), (0, 'BOUND', {}, 1, 1))
        self.assertIn('assign hb_x_SE__rq = hb_x_NE__rq_q0[7:0];', svh); self.assertIn('assign hleaf_SE__cfg = hb_x_NE__cfg[3:0];', svh)
    def test_missing(self): self.bad({k: v for k, v in GOOD.items() if k != 'hleaf_SE__cfg'}, 'MAP_MISSING')
    def test_extra(self): self.bad(dict(GOOD, foo_SE__z={'src_instance': 'hb_x_NE', 'src_port': 'rq_q0'}), 'MAP_EXTRA')
    def test_absent(self): self.bad(dict(GOOD, hb_x_SE__rq={'src_instance': 'hb_x_NE', 'src_port': 'nope'}), 'SRC_ABSENT')
    def test_s_role(self): self.bad(dict(GOOD, hb_x_SE__rq={'src_instance': 'hb_x_SE', 'src_port': 'rq'}), 'SRC_S_ROLE')
    def test_width(self): self.bad(dict(GOOD, hb_x_SE__rq={'src_instance': 'hb_x_NE', 'src_port': 'rq_q0', 'lsb': 1}), 'WIDTH')
    def test_shared_queue(self):   # the N client already reads rq: a request queue may not be shared
        self.bad(dict(GOOD, hb_x_SE__rq={'src_instance': 'hb_x_NE', 'src_port': 'rq'}), 'SHARED_SRC')
    def test_shared_cfg_needs_broadcast(self): self.bad(dict(GOOD, hleaf_SE__cfg={'src_instance': 'hb_x_NE', 'src_port': 'cfg'}), 'SHARED_SRC')
    def test_new_sm(self): self.bad(dict(GOOD, hb_x_SE__rq={'src_instance': 'sm_SW4', 'src_port': 'y'}), 'SM_COUNT')

if __name__ == '__main__':
    unittest.main()
