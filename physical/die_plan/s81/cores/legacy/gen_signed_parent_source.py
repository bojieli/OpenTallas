#!/usr/bin/env python3
"""Opt-in source vehicle for a legacy parent with actual SIGNED hard children.

This stages native child LEF/TT/FF/BB/clock insertion and exact instance sites.
The ordinary generator keeps its refusal. Physical goals remain disabled until
parent clock planning, interface adoption and placement review are completed.
"""
import argparse
import copy
import json
import math
from pathlib import Path
import re
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_core_kit_legacy as G


def signed_view(path):
    d = Path(path)
    master = d.name
    needed = [f'{master}.lef', f'{master}_tt.lib', f'{master}_ff.lib',
              f'{master}_bb.v', 'pins.json', 'insertion.json', 'signoff.json', 'lec_post.json']
    missing = [name for name in needed if not (d/name).is_file()]
    if missing:
        raise ValueError(f'{master}: incomplete signed child: {missing}')
    so = json.loads((d/'signoff.json').read_text())
    if so.get('verdict') != 'SIGNED':
        raise ValueError(f'{master}: child is not SIGNED')
    if json.loads((d/'lec_post.json').read_text()).get('verdict') != 'EQUIVALENT':
        raise ValueError(f'{master}: routed child is not EQUIVALENT')
    policy = so['policy']
    if [policy[k] for k in ['period_ps', 'uncertainty_setup_ps', 'uncertainty_hold_ps']] != [833, 60, 25]:
        raise ValueError(f'{master}: timing policy differs')
    clock = json.loads((d/'insertion.json').read_text())
    for corner in ['tt', 'ff']:
        actual = so['checks']['clock']['by_corner'][corner]['pinflops']
        if clock[corner]['boundary'] != actual or not math.isfinite(actual['mean']) or actual['mean'] < 0:
            raise ValueError(f'{master}: insertion is not the actual signed {corner} measurement')
    text = (d/f'{master}.lef').read_text()
    size = re.search(r'\bSIZE\s+(\S+)\s+BY\s+(\S+)\s*;', text)
    if not size:
        raise ValueError(f'{master}: LEF outline missing')
    outline = [float(v) for v in size.groups()]
    dirs = G.lef_dirs(d/f'{master}.lef')
    pins = json.loads((d/'pins.json').read_text())
    names = {p['bus'] if p.get('bit') is None else f"{p['bus']}[{p['bit']}]" for p in pins}
    if set(dirs)-{'VDD','VSS','VDDPHY','VSSPHY'} != names:
        raise ValueError(f'{master}: signed pins differ from actual LEF')
    bb = (d/f'{master}_bb.v').read_text()
    if not re.search(r'\bmodule\s+'+re.escape(master)+r'\b', bb):
        raise ValueError(f'{master}: blackbox master differs')
    bb_dirs = {}
    for direction, hi, lo, name in re.findall(r"\b(input|output|inout)\s+(?:wire\s+)?(?:\[(\d+):(\d+)\]\s*)?(\w+)\s*;", bb):
        bits = [name] if hi == "" else [f"{name}[{i}]" for i in range(min(int(lo),int(hi)),max(int(lo),int(hi))+1)]
        bb_dirs.update({pin:direction for pin in bits})
    if bb_dirs != {name:dirs[name].lower() for name in names}:
        raise ValueError(f'{master}: blackbox ports differ from the actual signed LEF')
    return dict(master=master, view=str(d.resolve()), outline_um=outline,
                tt_insertion_ps=clock['tt']['boundary']['mean'], ff_insertion_ps=clock['ff']['boundary']['mean'],
                pins=len(names), signoff='SIGNED', routed_lec='EQUIVALENT')


def placement(spec, view_records):
    """Original instance identities choose sites; no interchange by master/name sort."""
    lines = ['# Exact original spec instance sites; source-only, not route authority.',
             'set sc_blk [ord::get_db_block]', 'set sc_dbu [$sc_blk getDbUnitsPerMicron]', 'set sc_seen {}']
    for child in spec.get('macros', []) + spec.get('children', []):
        master = Path(child['view']).name
        pattern = child.get('inst')
        if not pattern:
            raise ValueError(f'{master}: exact instance identity required')
        x,y = child['at']; orient = child.get('orient','R0')
        lines += ['set sc_hit {}',
                  f'foreach i [$sc_blk getInsts] {{ if {{[[$i getMaster] getName] eq "{master}" && [string match {{{pattern}}} [string map [list [format %c 92] {{}}] [$i getName]]]}} {{lappend sc_hit $i}} }}',
                  f'if {{[llength $sc_hit] != 1}} {{error "signed child site {pattern}: expected one actual instance"}}',
                  'set i [lindex $sc_hit 0]',
                  'if {[dict exists $sc_seen [$i getName]]} {error "signed child instance assigned twice"}',
                  'dict set sc_seen [$i getName] 1', f'$i setOrient {orient}', '$i setLocation 0 0',
                  'set sc_box [$i getBBox]',
                  f'$i setLocation [expr {{round({x}*$sc_dbu)-[$sc_box xMin]}}] [expr {{round({y}*$sc_dbu)-[$sc_box yMin]}}]',
                  '$i setPlacementStatus FIRM']
    return '\n'.join(lines)+'\n'


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--enable-signed-source-only', action='store_true')
    ap.add_argument('--module', required=True, choices=['dsdv_bksel_q'])
    ap.add_argument('--child-views', required=True, help='JSON: original spec view -> complete actual signed view')
    ap.add_argument('--define', action='append', default=[])
    ap.add_argument('--plan', required=True)
    ap.add_argument('--out', required=True)
    a=ap.parse_args()
    if not a.enable_signed_source_only:
        raise SystemExit('explicit --enable-signed-source-only is required; default parent refusal is unchanged')
    out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
    recipes=json.loads((G.HERE/'recipes.json').read_text())
    rec=recipes[a.module]
    if rec.get('spec_git'):
        raise SystemExit('historical parent spec needs an explicit current source event')
    original=json.loads((G.REPO/rec['ref_tile']/'spec.json').read_text())
    children=original.get('children',[])
    if not children:
        raise SystemExit('no hard children in the declared parent')
    mapping=json.loads(Path(a.child_views).read_text())
    if set(mapping) != {c['view'] for c in children}:
        raise SystemExit('signed replacement set must equal every original child view')
    views={old:signed_view(path) for old,path in mapping.items()}
    for old,v in views.items():
        old_text=(G.REPO/old/f"{v['master']}.lef").read_text()
        old_size=re.search(r'\bSIZE\s+(\S+)\s+BY\s+(\S+)\s*;',old_text)
        if [float(x) for x in old_size.groups()] != v['outline_um']:
            raise SystemExit('signed child outline differs from its declared parent slot')
    staged=copy.deepcopy(original)
    native=[]
    for c in children:
        q=copy.deepcopy(c);q['view']=views[c['view']]['view'];native.append(q)
    # The new entrypoint validates SIGNED children before adapting their actual
    # physical views to the existing fixed-macro staging path. No parent guard
    # is relaxed, and the resulting runner cannot enter a physical stage.
    staged['macros']=staged.get('macros',[])+native
    staged.pop('children')
    # Replace a dedicated child definition with its exact fixed-interface
    # signed blackbox. Mixed-definition files are refused instead of edited.
    masters={v['master'] for v in views.values()}
    retained=[]
    replaced=[]
    patch_root=out/'parent_rtl';patch_root.mkdir(exist_ok=True)
    for source in staged['sources']:
        text=(G.REPO/source).read_text()
        mask=re.sub(r'/\*.*?\*/|//[^\n]*',lambda m: ''.join('\n' if c=='\n' else ' ' for c in m.group()),text,flags=re.S)
        spans=[]
        for hit in re.finditer(r'\bmodule\s+(\w+)\b',mask):
            if hit.group(1) in masters:
                end=re.search(r'\bendmodule\b',mask[hit.end():])
                if not end:
                    raise SystemExit('hard child module has no exact endmodule')
                spans.append((hit.start(),hit.end()+end.end()))
        if spans:
            for start,end in reversed(spans):text=text[:start]+text[end:]
            target=patch_root/Path(source).name
            target.write_text(text)
            retained.append(str(target))
            replaced.append(dict(source=source,removed_modules=sorted(masters),preserved_helpers=True))
        else:
            retained.append(source)
    staged['sources']=retained
    sp=out/'spec';sp.mkdir(exist_ok=True)
    (sp/'spec.json').write_text(json.dumps(staged,indent=2)+'\n')
    test_rec=copy.deepcopy(rec);test_rec['ref_tile']=str(sp)
    test_rec['defines']=list(dict.fromkeys(test_rec.get('defines',[])+a.define))
    test_rec.setdefault('orfs_vars',{})['SYNTH_BLACKBOXES']=' '.join(sorted(v['master'] for v in views.values()))
    recipes[a.module]=test_rec
    rp=out/'recipes.json';rp.write_text(json.dumps(recipes,indent=2)+'\n')
    subprocess.run([sys.executable,'-I',str(G.HERE/'gen_core_kit_legacy.py'),'--module',a.module,
                    '--recipes',str(rp),'--plan',a.plan,'--out',str(out/'kits'),'--suffix','signed_source'],check=True)
    kd=out/'kits'/f"{original['top']}_signed_source"
    (kd/'macro_place.tcl').write_text((kd/'macro_place.tcl').read_text()+'\n'+placement(original,views))
    for v in views.values():
        # bb is also retained as an explicit interface artifact. Synthesis uses
        # SYNTH_BLACKBOXES on the corresponding original fixed-parameter module.
        import shutil
        shutil.copyfile(Path(v['view'])/f"{v['master']}_bb.v",kd/f"{v['master']}_bb.v")
    runner=kd/'run_kit.sh';s=runner.read_text()
    anchor='set -uo pipefail\n'
    assert s.count(anchor)==1
    s=s.replace(anchor,anchor+'if [ "${2:-finish}" != synth ]; then echo "NOT RUN: signed-parent SOURCE VEHICLE; parent clock/interface/placement review pending" >&2; exit 78; fi\n')
    runner.write_text(s)
    ledger=dict(schema='opentallas.s81.signed_parent_source.v1',module=a.module,source_only=True,
                physical_status='NOT RUN',children=views,instances=len(children),
                original_spec=rec['ref_tile']+'/spec.json',defines_added=a.define,
                clock_status='parent compensation/local clock plan NOT RUN',
                functional_cycles_added=0,child_sites='exact original instances/sites/orientations',source_replacements=replaced)
    (kd/'signed_children.json').write_text(json.dumps(ledger,indent=2)+'\n')
    print(f"SIGNED_PARENT_SOURCE GEN PASS {a.module}: {len(children)} actual signed instances; PHYSICAL HELD")

if __name__=='__main__':
    main()
