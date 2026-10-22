#!/usr/bin/env python3
"""Q-RSTGEN7 10-19: reset release into foreign clocks (tools/qwen_split/reset_sync_contract.py).

  candidate: the dv2f15r reset last hops (testdata excerpt of the GEN netlist) carry 3 untreated releases (io_ucie
             stream -> ucie 6:5, d2d_rom / sys_face tile synchroniser inputs timed as releases); the plan re-clocks the
             io_ucie last hop onto clk_ucie, declares 3 synchroniser endpoints, and the audit of the planned netlist is
             0; the landing / hop-0 reset pins on the same nets and the mesochronous SerDes rst_n stay timed.
  mutants:   OT_SPLIT_RST_SYNC=0 (no plan) reproduces the dv2f15codex fail classes; a tile whose rst_n also drives a
             plain flop fails its RTL proof; a repeater with logic between its flops fails; a PHY sink sharing its
             repeater with a stream sink is refused.
    python3 tools/qwen_split/test_reset_sync_contract.py      (from the repo root)
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_split'))
import reset_sync_contract as R  # noqa: E402

# 1. RTL proofs of the declared tile synchroniser pins and of the repeater
ok = R.rtl_check(ROOT)
assert ok == {'qfd_d2d_static.rst_n': (True, 'ok'), 'qfd_d2d_static.por_n': (True, 'ok'),
              'qfd_sys_face.rst_n': (True, 'ok')}, ok
assert R.rep_check(ROOT) == (True, 'ok')

# 2. mutants of the RTL proofs
sf = 'rtl/qwen_split/qfd_sys_face.sv'
t = (ROOT / sf).read_text()
bad = t.replace('    wire rst_boot = rr_q[0]', '    reg mut_q; always @(posedge ck) if (!rst_n) mut_q <= 1\'b0;\n'
                '    wire rst_boot = rr_q[0]', 1)
assert bad != t
r = R.rtl_check(ROOT, texts={sf: bad})['qfd_sys_face.rst_n']
assert not r[0] and 'used' in r[1], r
d2 = 'rtl/lib/ot_rst_pipe.sv'
t2 = (ROOT / d2).read_text()
bad2 = t2.replace("else begin s0 <= 1'b1; s1 <= s0; end", "else begin s0 <= rst_n_in; s1 <= s0; end")
assert bad2 != t2
r = R.rtl_check(ROOT, texts={d2: bad2})['qfd_d2d_static.rst_n']
assert not r[0], r
rp = R.REP_SYNC['qfd_rst_rep']
t3 = (ROOT / rp).read_text()
bad3 = t3.replace('r0 <= s[PAD];', 'r0 <= s[PAD] & d;')
assert bad3 != t3 and not R.rep_check(ROOT, texts={rp: bad3})[0]

# 3. the dv2f15r last hops: fail classes before, none after
net = (Path(__file__).parent / 'testdata' / 'rstgen7_dv2f15r_reset_excerpt.v').read_text()
cells, wires, ckb, ckof, mof = R.model_from_netlist(net)
before = R.audit(wires, dict(ckb), ckof, mof, [])
hops = sorted(b['hop'] for b in before)
assert hops == ['rstt_rst_d2d__fo1__r3_12 -> d2d_rom/rst_n', 'rstt_rst_d2d__fo2__r4_9 -> sys_face/rst_n',
                'rstt_rst_io_0 -> io_ucie/rst_n'], hops               # MUTANT (no plan) = the dv2f15codex fail classes
p = R.plan(cells, wires, ckb, ckof, mof, ok)
assert not p['errors'], p['errors']
assert p['reclock'] == {'rstt_rst_io_0': 'clk_ucie'}, p['reclock']        # io_serdes*: mesochronous, stay timed
pins = sorted(e['pin'] for e in p['endpoints'])
assert pins == ['d2d_rom/rst_n', 'rstt_rst_io_0/d', 'sys_face/rst_n'], pins
assert not any(e['pin'].startswith('rly_') for e in p['endpoints'])          # landing rs / hop-0 en stay timed
after = R.audit(wires, {c[0]: p['reclock'].get(c[0], ckb[c[4]]) for c in cells}, ckof, mof, p['endpoints'])
assert after == [], after                                                    # CANDIDATE: PASS
s = R.sdc(p['endpoints'])
assert sum(ln.startswith('ot_rsync {') for ln in s.splitlines()) == 3 and 'set_false_path -to $q' in s
assert 'set_multicycle_path' not in s and 'OT_RESET_SYNC set $::ot_rsync_n missing $::ot_rsync_miss of 3' in s
# a die whose SerDes roots are NOT mesochronous (no PHY-clock collective): the SerDes last hops re-clock too
pm = R.plan(cells, wires, ckb, ckof, mof, ok, R.mesochronous({}))
assert sorted(pm['reclock']) == ['rstt_rst_io_0', 'rstt_rst_io_1', 'rstt_rst_io_2', 'rstt_rst_io_3'], pm['reclock']
assert len(R.audit(wires, dict(ckb), ckof, mof, [], R.mesochronous({}))) == 6

# 4. mutants of the plan: shared repeater refused; a failed RTL proof is not declared
w2 = [w for w in wires if w[1] != 'rstt_rst_io_0'] + [('n_rst_io__t111', 'rstt_rst_io_0',
      [('rstt_rst_io_0', 'q0'), ('io_ucie', 'rst_n'), ('rly_sf_cfg_data_2', 'rs')])]
ckof2 = dict(ckof, rly_sf_cfg_data_2=[('clk_coll', 'ck')])
p2 = R.plan(cells, w2, ckb, ckof2, mof, ok)
assert any(e.get('rep') == 'rstt_rst_io_0' and 'shares' in e['error'] for e in p2['errors']), p2['errors']
p3 = R.plan(cells, wires, ckb, ckof, mof, dict(ok, **{'qfd_d2d_static.rst_n': (False, 'mutant')}))
assert any('RTL check' in e['error'] for e in p3['errors']) and 'd2d_rom/rst_n' not in [e['pin'] for e in p3['endpoints']]
print('RSTGEN7 PASS: 3 untreated reset releases before (mutant: d2d_rom, sys_face, io_ucie), 0 after; io_ucie last '
      'hop re-clocked onto clk_ucie; 3 synchroniser endpoints; RTL / repeater / shared-hop mutants refused')
