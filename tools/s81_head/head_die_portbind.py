#!/usr/bin/env python3
"""HEAD-RTL-3 2026-10-26: strict die port-bind (tools/die_port_bind.py, owner NO STUBS rule) of an s81_head plan.

  head_die_portbind.py PLAN.json --out DIR        (repo root cwd; DIR repo-relative, e.g. results/arch/...)

1. tools/die_plan/gen.py rtl PLAN --rtl-root .  (leaf port binding of every type's contents; rc must be 0)
2. the generated die top is re-emitted with a NON-ANSI header (same ports, same body): die_port_bind reads die-top ports
   from body declarations only (as bind.py emits its bound tops), so ANSI header ports clk/rst_n/start were UNPARSED;
3. pads: ONLY the reset/START wavefront outs rst_o_<k> / start_o_<k> that the generated top leaves open.  By the reset
   tool contract (tools/die_plan/reset_tree.py: "pins are uniform per type (the union of the sites any instance uses)")
   an instance whose wavefront has no child on face k leaves that registered out unloaded; declared per INSTANCE with
   that reason.  Every other open output, tie, undriven or unread bit still fails;
4. filelist = generated wrappers + every type `sources` entry, all REPO-RELATIVE (no absolute / frozen-tree paths);
5. die_port_bind.py DIR/s81_head_top.sv --top s81_head_top -f DIR/portbind.f --pad-file DIR/pads.json --out DIR/port_bind_strict.json
0. tools/s81_head/head_module_check.py PLAN (content providers): REQUIRED, because die_port_bind does not see a missing
   provider -- the canonical plan's wrappers instantiate THEMSELVES as u_core (ot_s81hd_ctl u_core inside module
   ot_s81hd_ctl), which die_port_bind indexes as a 'real' master (HEAD-RTL-3 10-26: canonical 4 missing, port-bind PASS).
   HEAD-RTL-4: die_port_bind now itself reports a self-instantiating master (no parameter override) as STUB, and with
   --logic-free-stub (passed here) a wiring-only master too, so the canonical plan fails in die_port_bind as well.
HEAD-RTL-5 (10-26): die_port_bind runs --manifest-only: modules resolve ONLY from portbind.f (generated wrappers + plan
   type sources + the declared supplement tools/s81_head/head_portbind_extra.f), never from the rtl/ + physical/**/rtl
   tree index, whose physical/ref_tile/*/src snapshots made the HEAD-RTL-4 candidate run AMBIGUOUS (ot_s81ph_mem1r1w:
   pre-WREG copy of dscoll_lane_w_rt) and made the HEAD-RTL-3 PASS depend on what the checkout held.  A child missing
   from the manifest is unresolved (FAIL), a manifest entry that does not exist fails, and two manifest definitions with
   different ports/parameters fail.  The supplement lists the closure modules the plan `sources` omit (to move into the
   plan with the next PLAN-DELTA).
HEAD-BIND-4 (10-27, COORD ruling on HEAD-CORE-R13 ASK4):
6. die_port_bind gets --strap-file DIR/straps.json = the plan's partition ID straps [[wrapper module, strap port]]
   (OWNER 10-25 option B; gen.py rtl DIR/gen/parent_id_straps.json): a literal on a declared strap is recorded, any other
   tie still fails.  straps.audit_top_ties re-checks every literal on the die top against that manifest (tie_audit.json).
7. NESTED leaf-pin check (tools/die_plan/port_bind_gate.py nested_check): every instance inside every generated wrapper
   against its master header (every port bound, no unknown port, widths equal).  die_port_bind sees only the die-top
   partition pins, so an open leaf pin inside a wrapper (hd_serdes u_phy .rx/.tx only, 10-26) passed it silently.
Exit 0 iff module check 0 missing AND die_port_bind PASS AND tie audit PASS AND nested check PASS."""
import argparse, json, re, subprocess, sys
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('plan'); ap.add_argument('--out', required=True)
a = ap.parse_args()
out = Path(a.out)
if out.is_absolute():
    raise SystemExit('--out must be repo-relative')
out.mkdir(parents=True, exist_ok=True)
mc = subprocess.run([sys.executable, 'tools/s81_head/head_module_check.py', a.plan, '--out', str(out / 'module_check.json')],
                    capture_output=True, text=True)
missing = json.loads((out / 'module_check.json').read_text())['missing_modules'] if (out / 'module_check.json').exists() else None
print('MODULE_CHECK missing=%s rc=%d' % (missing, mc.returncode))
gen = out / 'gen'
gen.mkdir(parents=True, exist_ok=True)
g = subprocess.run([sys.executable, 'tools/die_plan/gen.py', 'rtl', a.plan, '--out', str(gen), '--rtl-root', '.'],
                   capture_output=True, text=True)
(out / 'gen_rtl.log').write_text(g.stdout + g.stderr)
if g.returncode:
    print('GEN_RTL FAIL rc', g.returncode); sys.exit(g.returncode)
top = gen / 's81_head_top.sv'
t = top.read_text()
m = re.search(r'module\s+s81_head_top\s*\((.*?)\);', t, re.S)
decl = [d.strip() for d in m.group(1).split(',') if d.strip()]
names = [d.split()[-1] for d in decl]
t2 = t[:m.start()] + 'module s81_head_top (' + ', '.join(names) + ');\n' + ''.join('    %s;\n' % d for d in decl) + t[m.end():]
top.write_text(t2)
pads = {}
for im in re.finditer(r'^\s{4}(\w+)(?:\s*#\(.*?\))?\s+(\w+)\s*\((.*?)\n\s{4}\);', t2, re.S | re.M):
    mst, inst, body = im.groups()
    opn = re.findall(r'\.((?:rst|start)_o_\d+)\(\s*\)', body)
    if opn:
        pads[inst] = dict(master=mst, reason='reset/START wavefront out with no child at this instance '
                          '(reset_tree.py: wavefront pins are the per-type union of the sites any instance uses)',
                          ports={p: [[0, 0]] for p in opn})
sys.path.insert(0, 'tools/die_plan')
import straps as STR  # noqa: E402
import port_bind_gate as PBG  # noqa: E402
pim = gen / 'parent_id_straps.json'
pman = json.loads(pim.read_text()) if pim.is_file() else dict(types={}, instances={})
plan0 = json.loads(Path(a.plan).read_text())
modof = {tn: ty['module'] for tn, ty in plan0['partition_types'].items()}
(out / 'straps.json').write_text(json.dumps(dict(straps=sorted([modof[tn], pn] for tn, ps in pman['types'].items()
                                                                for pn in ps)), indent=1) + '\n')
aud = STR.audit_top_ties(t2, pman, {m: tn for tn, m in modof.items()})
(out / 'tie_audit.json').write_text(json.dumps(dict(aud, rows=len(aud['rows'])), indent=1) + '\n')
print('TIE_AUDIT %s accepted=%d rejected=%d' % (aud['verdict'], len(aud['accepted']), len(aud['rejected'])))
(out / 'pads.json').write_text(json.dumps({'pads': {}, 'instances': pads}, indent=1) + '\n')
plan = json.loads(Path(a.plan).read_text())
src = []
for ty in plan['partition_types'].values():
    for s in ty.get('sources', []):
        if Path(s).is_absolute():
            raise SystemExit('absolute source path in plan: ' + s)
        if s not in src:
            src.append(s)
EXTRA = Path('tools/s81_head/head_portbind_extra.f')
extra = [ln.split('#')[0].strip() for ln in EXTRA.read_text().split('\n') if ln.split('#')[0].strip()]
for s in extra:
    if Path(s).is_absolute() or not Path(s).is_file():
        raise SystemExit('supplement entry must be an existing repo-relative file: ' + s)
dup = [s for s in extra if s in src]
if dup:
    # A source-closure PLAN-DELTA migrates these exact paths into their owning
    # types. Include each file once; manifest-only still rejects conflicting
    # module definitions and missing dependencies below.
    print('SUPPLEMENT_IN_PLAN %d' % len(dup))
    extra = [s for s in extra if s not in src]
# DIE-HEAD-28 10-29: the landed wrappers instantiate the clock-landing rings (rtl/common/ot_dp_clk_landing*.sv), which
# instantiate ot_meso_ring/_ohor/... (rtl/common/ot_meso_fifo.sv); no type `sources` list them.  Take the SAME transitive
# closure gen_phys.landing_rtl gives the kits (DIE-HEAD-7 10-28) so --manifest-only resolves them (SOURCE7 strict bind
# unit 3445572 FAIL: unresolved ot_meso_ohor).  Repo-relative, deduplicated against src + extra.
import gen_phys as GP  # noqa: E402
land = [str(f) for f in GP.landing_rtl('.', '\n'.join(p.read_text() for p in sorted(gen.glob('*.sv'))))
        if str(f) not in src and str(f) not in extra]
print('LANDING_CLOSURE %d %s' % (len(land), land))
fl = sorted(str(p) for p in gen.glob('*.sv')) + src + extra + land
(out / 'portbind.f').write_text('\n'.join(fl) + '\n')
print('pads: %d instances, %d open wavefront outs' % (len(pads), sum(len(v['ports']) for v in pads.values())))
r = subprocess.run([sys.executable, 'tools/die_port_bind.py', str(top), '--top', 's81_head_top', '-f', str(out / 'portbind.f'),
                    '--pad-file', str(out / 'pads.json'), '--strap-file', str(out / 'straps.json'), '--out', str(out / 'port_bind_strict.json'), '--logic-free-stub',
                    '--manifest-only'],
                   capture_output=True, text=True)
(out / 'port_bind_strict.txt').write_text(r.stdout + r.stderr)
print(r.stdout[-3000:], r.stderr[-1000:])
nest = PBG.nested_check({p.name: p.read_text() for p in sorted(gen.glob('*.sv')) if p.name != 's81_head_top.sv'},
                        [Path(x).read_text(errors='replace') for x in src + extra])
(out / 'nested_portbind.json').write_text(json.dumps(nest, indent=1) + '\n')
print('PORT_BIND_NESTED', nest['verdict'], json.dumps({k: v for k, v in nest.items() if k != 'examples'}))
for k, v in nest.get('examples', {}).items():
    print(' ', k, v[:6])
ok = missing == 0 and r.returncode == 0 and aud['verdict'] == 'PASS' and nest['verdict'] == 'PASS'
print('HEAD_DIE_PORTBIND %s module_missing=%s port_bind_rc=%d tie_audit=%s nested=%s' % (
    'PASS' if ok else 'FAIL', missing, r.returncode, aud['verdict'], nest['verdict']))
sys.exit(0 if ok else 1)
