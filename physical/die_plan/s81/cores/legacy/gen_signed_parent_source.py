#!/usr/bin/env python3
"""Opt-in source vehicle for a legacy parent with actual SIGNED hard children.

This stages native child LEF/TT/FF/BB/clock insertion and exact instance sites.
The ordinary generator keeps its refusal. Physical goals remain disabled until
parent clock planning, interface adoption and placement review are completed,
unless --enable-signed-physical is given (FLOW-19 10-31, COORD 15:4x: the kit
then runs every stage with the normal kit gates).

FLOW-19 10-31 (COORD 15:4x, S81 ot_s81sl_capc5r, 12.28b fewer refusals):
  * a child is accepted under any released sign-off policy (SIGNED by signoff.py
    at the die clock period), not only the 833/60/25 policy of 10-30;
  * a signed child is checked against its slot in the CURRENT parent: its oriented
    outline at the spec site lies inside the plan outline of the parent and does
    not overlap a sibling (was: equal to the old declared view outline).
"""
import argparse
import ast
import copy
import json
import math
from pathlib import Path
import re
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_core_kit_legacy as G


def _mask(text):
    return re.sub(r'"(?:\\.|[^"\\])*"|/\*.*?\*/|//[^\n]*',
                  lambda m: ''.join('\n' if c == '\n' else ' ' for c in m.group()), text, flags=re.S)


def _integer(expr, values):
    """Only constant integer arithmetic; never execute an RTL expression as Python."""
    def number(m):
        value=int(m[4].replace('_',''),{'d':10,'h':16,'b':2,'o':8}[m[3].lower()])
        width=int(m[1]) if m[1] else max(32,value.bit_length())
        if width<=0:raise ValueError('zero-width integer constant')
        value &= (1<<width)-1
        if m[2] and value&(1<<(width-1)):value-=1<<width
        return str(value)
    expr = re.sub(r"(\d*)'([sS]?)([dDhHbBoO])([0-9a-fA-F_]+)",number,expr)
    trunc=lambda a,b:abs(a)//abs(b)*(-1 if (a<0)!=(b<0) else 1)
    ops = {ast.Add: lambda a,b:a+b, ast.Sub:lambda a,b:a-b, ast.Mult:lambda a,b:a*b,
           ast.Div:trunc, ast.Mod:lambda a,b:a-trunc(a,b)*b,
           ast.LShift:lambda a,b:a<<b, ast.RShift:lambda a,b:a>>b,
           ast.BitOr:lambda a,b:a|b, ast.BitAnd:lambda a,b:a&b, ast.BitXor:lambda a,b:a^b}
    def visit(n):
        if isinstance(n, ast.Constant) and type(n.value) is int:return n.value
        if isinstance(n, ast.Name) and n.id in values:return int(values[n.id])
        if isinstance(n, ast.BinOp) and type(n.op) in ops:return ops[type(n.op)](visit(n.left),visit(n.right))
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd,ast.USub,ast.Invert)):
            v=visit(n.operand);return v if isinstance(n.op,ast.UAdd) else -v if isinstance(n.op,ast.USub) else ~v
        raise ValueError(f'hard child parameter is not a resolved integer constant: {expr}')
    try:return visit(ast.parse(expr.strip(), mode='eval').body)
    except (SyntaxError, ZeroDivisionError) as e:raise ValueError(f'hard child parameter {expr}: {e}') from e


def _close(text, start):
    depth=0
    for i in range(start,len(text)):
        if text[i]=='(':depth+=1
        elif text[i]==')':
            depth-=1
            if not depth:return i+1
    raise ValueError('unterminated hard child parameter list')


def _defaults(mask, module, overrides=None):
    values=dict(overrides or {})
    hit=re.search(r'\bmodule\s+'+re.escape(module)+r'\s*#\s*\(',mask)
    if not hit:return values
    start=hit.end()-1;body=mask[start+1:_close(mask,start)-1]
    # Module parameter declarations may omit "parameter" after the first comma.
    parts=[];depth=0;last=0
    for i,c in enumerate(body):
        if c in '({[':depth+=1
        elif c in ')}]':depth-=1
        elif c==',' and depth==0:parts.append(body[last:i]);last=i+1
    parts.append(body[last:])
    for part in parts:
        m=re.search(r'(\w+)\s*=\s*(.+)$',part.strip(),re.S)
        if not m or m[1] in values:continue
        try:values[m[1]]=_integer(m[2],values)
        except ValueError:
            # An unrelated derived parameter need not be evaluated. If a hard
            # binding actually uses it, _integer below refuses the unresolved use.
            pass
    return values


def fixed_child_sources(spec, root, views, out):
    """Keep helpers and parent RTL intact; remove proved child definitions and
    redundant parameter overrides only after checking the fixed signed shape.
    Mixed-definition files are supported (xfin and its child share one source).
    """
    root,out=Path(root),Path(out);out.mkdir(parents=True,exist_ok=True)
    masters={v['master'] for v in views.values()}
    expected={};defaults={}
    for source in spec['sources']:
        mask=_mask((root/source).read_text())
        for master in masters:
            if re.search(r'\bmodule\s+'+re.escape(master)+r'\b',mask):
                defaults[master]=_defaults(mask,master)
    for old,v in views.items():
        child_spec=root/Path(old).parent.parent/'spec.json'
        expected[v['master']]=dict(defaults.get(v['master'],{}))
        if child_spec.is_file():expected[v['master']].update(json.loads(child_spec.read_text()).get('params',{}))
    retained,replaced=[],[]
    for source in spec['sources']:
        text=(root/source).read_text();mask=_mask(text);spans=[]
        for hit in re.finditer(r'\bmodule\s+(\w+)\b',mask):
            if hit[1] in masters:
                end=re.search(r'\bendmodule\b',mask[hit.end():])
                if not end:raise ValueError('hard child module has no exact endmodule')
                spans.append((hit.start(),hit.end()+end.end()))
        for start,end in reversed(spans):text=text[:start]+text[end:]
        mask=_mask(text);edits=[];bindings=[]
        for master in masters:
            for hit in re.finditer(r'\b'+re.escape(master)+r'\b\s*(#\s*\()?',mask):
                start=mask.index('(',hit.start(1)) if hit[1] else None
                end=_close(mask,start) if start is not None else hit.end()
                if not re.match(r'\s*\w+\s*(?:\[[^]]+\]\s*)?\(',mask[end:]):continue
                # Scope the expressions to their actual enclosing module.
                modules=list(re.finditer(r'\bmodule\s+(\w+)\b',mask[:hit.start()]))
                if not modules:raise ValueError(f'{master}: cannot locate containing module')
                values=(_defaults(mask,spec['top'],spec.get('params',{}))
                        if modules[-1][1]==spec['top'] else {})
                actual=dict(defaults.get(master,{}))
                args=mask[start+1:end-1] if start is not None else '';pos=0
                while pos<len(args):
                    pm=re.match(r'\s*,?\s*\.(\w+)\s*\(',args[pos:])
                    if not pm:raise ValueError(f'{master}: expected named constant parameter overrides')
                    astart=pos+pm.end()-1;aend=_close(args,astart)
                    actual[pm[1]]=_integer(args[astart+1:aend-1],values);pos=aend
                    if not args[pos:].strip():break
                if actual!=expected[master]:
                    raise ValueError(f'{master}: actual parameters {actual} differ from signed child {expected[master]}')
                if start is not None:edits.append((hit.start(1),end))
                bindings.append(dict(master=master,parameters=actual))
        for start,end in sorted(edits,reverse=True):text=text[:start]+text[end:]
        if spans or edits:
            target=out/Path(source).name
            if target.exists() and target.read_text()!=text:raise ValueError(f'duplicate parent source basename {target.name}')
            target.write_text(text);retained.append(str(target));replaced.append(dict(source=source,removed_modules=sorted(masters),preserved_helpers=True,parameter_bindings=bindings))
        else:retained.append(source)
    return retained,replaced


def signed_view(path, period_ps=None):
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
    if period_ps is not None and abs(float(policy['period_ps']) - float(period_ps)) > 1e-6:
        raise ValueError(f'{master}: signed at period {policy["period_ps"]} ps, die period {period_ps} ps')
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
                pins=len(names), signoff='SIGNED', routed_lec='EQUIVALENT',
                policy={k: policy.get(k) for k in ['period_ps', 'uncertainty_setup_ps', 'uncertainty_hold_ps']})


def slot_check(children, views, outline):
    """each child's signed outline (R90/R270/MXR90/MYR90 swap w/h) at its spec site inside the parent outline [w, h]
    and not overlapping a sibling (abutment allowed).  -> [(inst, rect)] or SystemExit naming every violation"""
    W, H = (float(v) for v in outline)
    rects, bad = [], []
    for c in children:
        w, h = views[c['view']]['outline_um']
        if '90' in c.get('orient', 'R0') or '270' in c.get('orient', 'R0'):
            w, h = h, w
        x, y = (float(v) for v in c['at'])
        r = (x, y, x + w, y + h)
        name = c.get('inst', c['view'])
        if x < -1e-6 or y < -1e-6 or r[2] > W + 1e-6 or r[3] > H + 1e-6:
            bad.append(f'{name} {r} outside the parent outline {W:g}x{H:g}')
        for n2, q in rects:
            if min(r[2], q[2]) - max(r[0], q[0]) > 1e-6 and min(r[3], q[3]) - max(r[1], q[1]) > 1e-6:
                bad.append(f'{name} {r} overlaps {n2} {q}')
        rects.append((name, r))
    if bad:
        raise SystemExit('signed child does not fit its parent slot: ' + '; '.join(bad))
    return rects


def placement(spec, view_records):
    """Original instance identities choose sites; no interchange by master/name sort."""
    lines = ['# Exact original spec instance sites; source-only, not route authority.',
             'set sc_blk [ord::get_db_block]', 'set sc_dbu [$sc_blk getDbUnitsPerMicron]', 'set sc_seen {}']
    entries=[c for c in spec.get('macros',[]) if c.get('inst')]+spec.get('children',[])
    for child in entries:
        master = Path(child['view']).name
        pattern = child.get('inst')
        if not pattern:
            raise ValueError(f'{master}: exact instance identity required')
        actual='[string map [list [format %c 92] {}] [$i getName]]'
        # Legacy profiles deliberately use * / ? (including ?0? to match [0]).
        # A literal generated path containing brackets is not itself a glob.
        match=(f'[string match {{{pattern}}} {actual}]' if '*' in pattern or '?' in pattern
               else f'{{{pattern}}} eq {actual}')
        x,y = child['at']; orient = child.get('orient','R0')
        lines += ['set sc_hit {}',
                  f'foreach i [$sc_blk getInsts] {{ if {{[[$i getMaster] getName] eq "{master}" && {match}}} {{lappend sc_hit $i}} }}',
                  f'if {{[llength $sc_hit] != 1}} {{error "signed child site {pattern}: expected one actual instance"}}',
                  'set i [lindex $sc_hit 0]',
                  'if {[dict exists $sc_seen [$i getName]]} {error "signed child instance assigned twice"}',
                  'dict set sc_seen [$i getName] 1', f'$i setOrient {orient}', '$i setLocation 0 0',
                  'set sc_box [$i getBBox]',
                  f'$i setLocation [expr {{round({x}*$sc_dbu)-[$sc_box xMin]}}] [expr {{round({y}*$sc_dbu)-[$sc_box yMin]}}]',
                  '$i setPlacementStatus FIRM']
    return '\n'.join(lines)+'\n'


def prepare(spec, rec, root, out, outline, period_ps, mapping=None):
    """Adapt complete signed child views to the already supported macro path.
    Unsigned children keep the ordinary generator's existing refusal.
    """
    root,out=Path(root),Path(out);children=spec.get('children',[])
    if not children:raise ValueError('no declared hard children')
    mapping=mapping or {c['view']:str(root/c['view']) for c in children}
    if set(mapping)!={c['view'] for c in children}:raise ValueError('signed replacement set must equal every original child view')
    views={old:signed_view(path,period_ps) for old,path in mapping.items()}
    for old,v in views.items():
        declared=root/old/f"{v['master']}.lef"
        expected=G.lef_dirs(declared)
        actual=G.lef_dirs(Path(v['view'])/f"{v['master']}.lef")
        pg={'VDD','VSS','VDDPHY','VSSPHY'}
        if {k:d for k,d in expected.items() if k not in pg}!={k:d for k,d in actual.items() if k not in pg}:
            raise ValueError(f"{v['master']}: signed child interface differs from current declared child")
    slots=slot_check(children,views,outline)
    staged=copy.deepcopy(spec)
    staged['macros']=staged.get('macros',[])+[dict(c,view=views[c['view']]['view']) for c in children]
    staged.pop('children')
    staged['sources'],replacements=fixed_child_sources(spec,root,views,out/'parent_rtl')
    staged_rec=copy.deepcopy(rec)
    staged_rec.setdefault('orfs_vars',{})['SYNTH_BLACKBOXES']=' '.join(sorted(v['master'] for v in views.values()))
    ledger=dict(schema='opentallas.s81.signed_parent_source.v1',module=spec['top'],
                children=views,instances=len(children),parent_outline_um=list(outline),
                child_slots={n:list(r) for n,r in slots},functional_cycles_added=0,
                child_sites='exact original instances/sites/orientations',source_replacements=replacements)
    return staged,staged_rec,ledger


def stage_contract(kd, original, ledger, root_pin, clock_only=False):
    """Use measured child boundary insertion in the existing physical tap balancer.
    clock_only refreshes a finished owned kit without regenerating its RTL or
    repeating macro placement; the caller may retain the old contracts first.
    """
    kd=Path(kd);rows={'tt':[],'ff':[]};contracts=[]
    for child in original['children']:
        v=ledger['children'][child['view']];d=Path(v['view'])
        lib=(d/f"{v['master']}_tt.lib").read_text()
        clocks=re.findall(r'\bpin\s*\(\s*"?([^"\)]+)"?\s*\)\s*\{[^{}]*\bclock\s*:\s*true\s*;',lib)
        clock=json.loads((d/'insertion.json').read_text())
        for pin in clocks:
            pin=pin.strip()
            means={}
            for corner in ('tt','ff'):
                cm=(clock.get('clock_measurements') or {}).get(pin,{}).get(corner,{}).get('boundary',{})
                mean=float(cm.get('mean',v[f'{corner}_insertion_ps']))
                means[corner]=dict(mean_ps=mean,basis='actual SIGNED child boundary mean')
                rows[corner].append(f"{{{child['inst']}}} {{{pin}}} {mean:.6f} {{{root_pin}}}")
            contracts.append(dict(inst=child['inst'],pin=pin,rise_ps=means['tt']['mean_ps'],tap=root_pin,
                                  corners=means,source=v['view'],signed=True))
        if not clocks:raise ValueError(f"{v['master']}: native timing model has no clock input")
    for corner,name in [('tt','core_latency.txt'),('ff','core_latency_ff.txt')]:
        (kd/name).write_text(f'# inst pin mean_pin_register_insertion_ps tap ({corner.upper()}; actual SIGNED child means)\n'+'\n'.join(rows[corner])+'\n')
    (kd/'core_latency.json').write_text(json.dumps(dict(edge='rise',rows=contracts),indent=2)+'\n')
    cfg=kd/'config.mk'
    cfg.write_text(re.sub(r'^export OT_CORE_LAT\s*=.*\n?','',cfg.read_text(),flags=re.M).rstrip()+'\nexport OT_CORE_LAT = /work/core_latency.txt\n')
    if not clock_only:
        with (kd/'macro_place.tcl').open('a') as f:f.write('\n'+placement(original,ledger['children']))
    (kd/'signed_children.json').write_text(json.dumps(ledger,indent=2)+'\n')
    freeze=kd/'freeze.json'
    if freeze.is_file():
        record=json.loads(freeze.read_text());record['signed_children']=ledger;record['kit_hash']=G.kit_hash(kd)
        freeze.write_text(json.dumps(record,indent=1)+'\n')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--enable-signed-source-only', action='store_true')
    ap.add_argument('--module', required=True, help="parent recipe, including 'ot_s81sl_capc5r' and ot_s81dv_xfin")
    ap.add_argument('--recipes', default=str(G.HERE/'recipes.json'),
                    help='parent recipe JSON (same default as the ordinary core generator)')
    ap.add_argument('--enable-signed-physical', action='store_true',
                    help='opt-in: run_kit runs every stage (normal kit gates) instead of exiting 78 after synth')
    ap.add_argument('--child-views', required=True, help='JSON: original spec view -> complete actual signed view')
    ap.add_argument('--define', action='append', default=[])
    ap.add_argument('--plan', required=True)
    ap.add_argument('--out', required=True)
    a=ap.parse_args()
    if not a.enable_signed_source_only:
        raise SystemExit('explicit --enable-signed-source-only is required; default parent refusal is unchanged')
    out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
    recipes=json.loads(Path(a.recipes).read_text())
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
    plan=json.loads(Path(a.plan).read_text())
    if rec.get('plan'):
        plan=json.loads((G.REPO/rec['plan']).read_text())
    try:
        views={old:signed_view(path, plan['die']['period_ps']) for old,path in mapping.items()}
    except ValueError as e:
        raise SystemExit(str(e))
    try:
        _,hc=G.plan_core(plan, rec.get('plan_module', a.module), rec.get('plan_pins_file'))
        outline,outline_src=hc['outline_um'],f"plan {Path(a.plan).name} hard core {hc['module']}"
    except SystemExit:
        outline,outline_src=[original['outline']['w'],original['outline']['h']],'parent spec outline'
    slots=slot_check(children, views, outline)
    for old,v in views.items():
        old_size=re.search(r'\bSIZE\s+(\S+)\s+BY\s+(\S+)\s*;',(G.REPO/old/f"{v['master']}.lef").read_text())
        v['declared_outline_um']=[float(x) for x in old_size.groups()] if old_size else None
    staged,test_rec,prepared=prepare(original,rec,G.REPO,out,outline,plan['die']['period_ps'],mapping)
    sp=out/'spec';sp.mkdir(exist_ok=True)
    (sp/'spec.json').write_text(json.dumps(staged,indent=2)+'\n')
    test_rec['ref_tile']=str(sp)
    test_rec['defines']=list(dict.fromkeys(test_rec.get('defines',[])+a.define))
    test_rec.setdefault('orfs_vars',{})['SYNTH_BLACKBOXES']=' '.join(sorted(v['master'] for v in views.values()))
    recipes[a.module]=test_rec
    rp=out/'recipes.json';rp.write_text(json.dumps(recipes,indent=2)+'\n')
    subprocess.run([sys.executable,'-I',str(G.HERE/'gen_core_kit_legacy.py'),'--module',a.module,
                    '--recipes',str(rp),'--plan',a.plan,'--out',str(out/'kits'),'--suffix','signed_source'],check=True)
    kd=out/'kits'/f"{original['top']}_signed_source"
    stage_contract(kd,original,prepared,original['clock_port'])
    for v in views.values():
        # bb is also retained as an explicit interface artifact. Synthesis uses
        # SYNTH_BLACKBOXES on the corresponding original fixed-parameter module.
        import shutil
        shutil.copyfile(Path(v['view'])/f"{v['master']}_bb.v",kd/f"{v['master']}_bb.v")
    runner=kd/'run_kit.sh';s=runner.read_text()
    anchor='set -uo pipefail\n'
    assert s.count(anchor)==1
    if not a.enable_signed_physical:
        s=s.replace(anchor,anchor+'if [ "${2:-finish}" != synth ]; then echo "NOT RUN: signed-parent SOURCE VEHICLE; parent clock/interface/placement review pending" >&2; exit 78; fi\n')
    runner.write_text(s)
    ledger=dict(schema='opentallas.s81.signed_parent_source.v1',module=a.module,
                source_only=not a.enable_signed_physical,
                physical_status='ENABLED (normal kit gates)' if a.enable_signed_physical else 'NOT RUN',
                children=views,instances=len(children),
                parent_outline_um=[float(v) for v in outline],parent_outline_source=outline_src,
                child_slots={n:list(r) for n,r in slots},
                original_spec=rec['ref_tile']+'/spec.json',defines_added=a.define,
                clock_status='parent compensation/local clock plan NOT RUN',
                functional_cycles_added=0,child_sites='exact original instances/sites/orientations',source_replacements=prepared['source_replacements'])
    (kd/'signed_children.json').write_text(json.dumps(ledger,indent=2)+'\n')
    freeze=kd/'freeze.json'
    record=json.loads(freeze.read_text());record['signed_children']=ledger;record['kit_hash']=G.kit_hash(kd)
    freeze.write_text(json.dumps(record,indent=1)+'\n')
    print(f"SIGNED_PARENT_SOURCE GEN PASS {a.module}: {len(children)} actual signed instances; "
          f"{'PHYSICAL ENABLED' if a.enable_signed_physical else 'PHYSICAL HELD'}")

if __name__=='__main__':
    main()
