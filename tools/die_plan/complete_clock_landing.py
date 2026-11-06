"""Opt-in complete native clock-leaf routing; no GEN activation or signoff waiver.

stage -> run.sh prepare -> render and VIEW -> REVIEW.txt -> run.sh route.
Only R0 hard children with one native M5 clk PORT, actual OBS below M6,
VIA56/M6 escape, and explicit selected master/count are supported. The fixture
retains every physical instance and PG obstacle. It temporarily routes each real
driver to an outside waypoint, then restores the complete original interface
while encoding that prefix plus the legal M6 landing as one complete FIXED wire.
A native physical graph must connect the real driver and real macro PORT.

A mechanism PASS still requires normal full-core routing, DRC and signoff.
Run each heavy phase through ot-run with its measured memory/CPU budget.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def stage(args):
    source = args.db.resolve(strict=True)
    if not source.is_file() or args.count <= 0 or not args.master:
        raise ValueError('regular source DB, explicit master and positive count required')
    out = args.out.resolve()
    if out.exists():
        raise ValueError('output directory must be fresh; preserve prior failures')
    out.mkdir(parents=True)
    here = Path(__file__).resolve().parent
    for name in ('plan.tcl', 'fixture.py', 'route.tcl', 'export.tcl', 'merge.tcl'):
        shutil.copyfile(here / 'complete_clock_landing' / name, out / name)
    shutil.copyfile(here / 'clk_freeze.tcl', out / 'clk_freeze.tcl')
    shutil.copyfile(here / 'core_clock_landing_audit.py', out / 'audit.py')
    manifest = dict(schema='opentallas.complete_clock_landing.v1', source_db=str(source),
                    source_sha256=digest(source), master=args.master, count=args.count,
                    native_pin_layer='M5', escape_layer='M6', child_obs_below='M6',
                    orientation='R0', added_cycles=0, gen_activation=False,
                    final_requirement='normal full-core routing, clock/data DRC, STA and routed LEC')
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    verify = '''import hashlib,json,pathlib\nm=json.loads(pathlib.Path(__file__).with_name('manifest.json').read_text())\nh=hashlib.sha256()\nwith open(m['source_db'],'rb') as f:\n for b in iter(lambda:f.read(8388608),b''):h.update(b)\nif h.hexdigest()!=m['source_sha256']:raise SystemExit('source DB changed: prepare a new event')\n'''
    (out / 'verify_input.py').write_text(verify)
    script = '''#!/bin/bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
PHASE=${1:?prepare or route}; MEM=${2:-8}; CPUS=${3:-4}
python3 "$ROOT/verify_input.py"
INPUT=SOURCE_INPUT
MASTER=SELECTED_MASTER
COUNT=SELECTED_COUNT
case "$PHASE" in
 prepare) test ! -e "$ROOT/clock_leaf_fixture.odb" ;;
 route) test -s "$ROOT/REVIEW.txt" || { echo 'Render and VIEW fixture_geom.json; record findings in REVIEW.txt before route'; exit 2; }
        test ! -e "$ROOT/complete_clock_merged.odb"
        test ! -e "$ROOT/ROUTE_STARTED"
        : > "$ROOT/ROUTE_STARTED" ;;
 *) echo 'phase must be prepare or route'; exit 2 ;;
esac
docker run --rm --name "complete-clock-$PHASE-$$" --memory="${MEM}g" --cpus="$CPUS" \
 -v "$INPUT":/input.odb:ro -v "$ROOT":/out \
 -e IN=/input.odb -e PLAN=/out/landing_plan.tsv \
 -e OT_LANDING_MASTER="$MASTER" -e OT_LANDING_COUNT="$COUNT" \
 "${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}" bash -lc '
 set -e
 source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
 if [ "$1" = prepare ]; then
   openroad -exit /out/plan.tcl
   openroad -python -exit /out/fixture.py
   echo PREPARED_RENDER_AND_VIEW_REQUIRED
 else
   openroad -exit /out/route.tcl
   test ! -s /out/clock_component.drc || { echo COMPONENT_DRC_FAILED; exit 3; }
   openroad -exit /out/export.tcl
   openroad -exit /out/merge.tcl
   openroad -python -exit /out/audit.py /out/complete_clock_merged.odb "$OT_LANDING_MASTER" "$OT_LANDING_COUNT" /out/native_audit.json
   echo MECHANISM_PASS_PENDING_FULL_CORE_ROUTE_AND_SIGNOFF
 fi' bash "$PHASE"
'''
    script = script.replace('SOURCE_INPUT', shlex.quote(str(source))).replace('SELECTED_MASTER', shlex.quote(args.master)).replace('SELECTED_COUNT', str(args.count))
    (out / 'run.sh').write_text(script)
    (out / 'run.sh').chmod(0o755)
    print(out / 'run.sh', 'prepare (through ot-run); render/view; REVIEW.txt; run.sh route')


def render(args):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    data = json.loads(args.fixture.read_text())
    fig, ax = plt.subplots(figsize=(8, 9))
    q = data['core']; ax.set_xlim(q[0], q[2]); ax.set_ylim(q[1], q[3]); ax.set_aspect('equal')
    for _, q in data['macros']:
        ax.add_patch(Rectangle((q[0], q[1]), q[2]-q[0], q[3]-q[1], facecolor='lightgray', edgecolor='black'))
    for _, q in data['drivers']:
        ax.plot((q[0]+q[2])/2, (q[1]+q[3])/2, 'bo', markersize=3)
    for px, py, xe, stub in data['landings']:
        u = data['dbu']; px, py, xe, stub = [v/u for v in (px, py, xe, stub)]
        ax.plot([px, xe, xe], [py, py, stub], color='orange', linewidth=.8)
        ax.plot(xe, stub, 'g+', markersize=5)
    ax.set_title('Complete clock leaf: real drivers (blue), outside waypoints (green)\nAll original physical instances and PG obstacles retained')
    fig.savefig(args.out, dpi=150)
    print(args.out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('stage')
    p.add_argument('--db', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--master', required=True)
    p.add_argument('--count', type=int, required=True)
    p.set_defaults(func=stage)
    p = sub.add_parser('render')
    p.add_argument('--fixture', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.set_defaults(func=render)
    args = parser.parse_args(); args.func(args)

if __name__ == '__main__':
    main()
