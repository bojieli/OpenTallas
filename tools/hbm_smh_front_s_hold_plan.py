#!/usr/bin/env python3
"""Emit a single explicit positive-buffer insertion from fresh endpoint evidence."""
import argparse
import hashlib
import json
from pathlib import Path


def generate(outputs, internal, output_stages=3):
    if output_stages < 1:
        raise ValueError("Output stages must be positive")
    plan=[]
    for item in outputs:
        top=item['topology']; paths=item['paths']
        if len(top['drivers']) != 1 or top['iterm_sinks'] or top['net_bterms'] != [item['port']]:
            raise ValueError('Output branch is not dedicated: '+item['port'])
        if paths['ss_max']['slack_ps'] < output_stages*40+15:
            raise ValueError('Insufficient SS output budget for staged buffer candidate')
        plan.append(dict(kind='output', target=item['port'], count=output_stages,
                         driver=top['drivers'][0]['instance'], net=top['net'],
                         baseline_ff_ps=paths['ff_min']['slack_ps'],
                         baseline_ss_ps=paths['ss_max']['slack_ps']))
    for item in internal:
        if item.get('ss_setup_ps',0)<55:
            raise ValueError('Internal SS margin unmeasured or insufficient: '+item['pin'])
        plan.append(dict(kind='internal',target=item['pin'],count=1,
                         baseline_ff_ps=item['slack_ps'],baseline_ss_ps=item['ss_setup_ps']))
    if len({(x['kind'],x['target']) for x in plan})!=len(plan):
        raise ValueError('Duplicate endpoint')
    return plan


def tcl(plan):
    text=['# Explicit zero-cycle data-delay candidate; no clock or SDC edits.',
          'set block [ord::get_db_block]',
          'set master [[ord::get_db] findMaster BUFx2_ASAP7_75t_R]',
          'if {$master eq "NULL"} {error "Missing real BUFx2 master"}',
          'set inserted 0']
    for index, item in enumerate(plan):
        target=item['target']
        if any(c in target for c in '{}\n'):
            raise ValueError('Unsupported Tcl endpoint name')
        if item['kind']=='output':
            text += [f'set sink [$block findBTerm {{{target}}}]',
                     'if {$sink eq "NULL"} {error "Output not found"}',
                     'set old [$sink getNet]',
                     f'set driver [$block findInst {{{item["driver"]}}}]',
                     'if {$driver eq "NULL"} {error "Pinned output driver missing"}',
                     f'if {{[$old getName] ne {{{item["net"]}}}}} {{error "Pinned output net changed"}}',
                     'set driver_pin [$driver findITerm Y]',
                     'if {$driver_pin eq "NULL" || [$driver_pin getNet] ne $old} {error "Pinned output driver connectivity changed"}',
                     'if {[llength [$old getBTerms]] != 1 || [llength [$old getITerms]] != 1} {error "Output branch topology changed"}',
                     'lassign [$driver getLocation] x y']
        else:
            instance,pin=target.rsplit('/',1)
            text += [f'set inst [$block findInst {{{instance}}}]',
                     'if {$inst eq "NULL"} {',
                     '  set matches {}',
                     '  foreach candidate [$block getInsts] {',
                     f'    if {{[string map {{\\\\ {{}}}} [$candidate getName]] eq {{{instance}}}}} {{lappend matches $candidate}}',
                     '  }',
                     '  if {[llength $matches] != 1} {error "Canonical internal register missing or ambiguous"}',
                     '  set inst [lindex $matches 0]',
                     '}',
                     f'set sink [$inst findITerm {{{pin}}}]',
                     'if {$sink eq "NULL"} {error "Internal D pin missing"}',
                     'set old [$sink getNet]', 'lassign [$inst getLocation] x y']
        text += ['if {$old eq "NULL"} {error "Unconnected hold sink"}', 'set upstream $old']
        for stage in range(item['count']):
            name=f'front_s_hold_{index}_{stage}';net=name+'_net'
            text += [f'if {{[$block findInst {name}] ne "NULL" || [$block findNet {net}] ne "NULL"}} {{error "No replay on modified checkpoint"}}',
                     f'set cell [odb::dbInst_create $block $master {name}]',
                     f'set next [odb::dbNet_create $block {net}]',
                     '$cell setLocation $x $y', '$cell setPlacementStatus PLACED',
                     'set a [$cell findITerm A]', 'set ypin [$cell findITerm Y]',
                     'if {$a eq "NULL" || $ypin eq "NULL"} {error "Buffer pin contract changed"}',
                     '$a connect $upstream', '$ypin connect $next',
                     'if {[$a getNet] ne $upstream || [$ypin getNet] ne $next} {error "Buffer connectivity failed"}',
                     'set upstream $next',f'set_dont_touch [get_cells {name}]','incr inserted']
        text += ['$sink disconnect', '$sink connect $upstream',
                 'if {[$sink getNet] ne $upstream || $upstream eq $old} {error "Hold sink relocation failed"}']
    count=sum(x['count'] for x in plan)
    text += [f'if {{$inserted != {count}}} {{error "Wrong inserted inventory"}}',
             'puts "OT_FRONT_S_HOLD_INSERTED $inserted"',
             '# Driver owns incremental legalization and routing, then fresh-process SS/FF STA.',
             '# Never accept timing from this modified in-memory timing graph.']
    return '\n'.join(text)+'\n'


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--outputs',type=Path,required=True)
    ap.add_argument('--internal',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--output-stages',type=int,default=3,
                    help='Priced positive data buffers per selected output (default: 3)')
    ap.add_argument('--source',default='f7f1a0ee4bfd331c9d6bb873d9a772a5fa88cb48',
                    help='Exact RTL source commit for the measured checkpoint')
    ap.add_argument('--checkpoint-manifest',type=Path,
                    help='Optional immutable checkpoint hash JSON bound into this plan')
    args=ap.parse_args()
    if len(args.source)!=40 or any(c not in '0123456789abcdef' for c in args.source):
        ap.error('--source must be a full lowercase commit hash')
    checkpoint=None
    if args.checkpoint_manifest:
        checkpoint=json.loads(args.checkpoint_manifest.read_text())
    if args.out.exists():ap.error('--out must be new')
    plan=generate(json.loads(args.outputs.read_text()),json.loads(args.internal.read_text()),args.output_stages)
    for entry in plan:
        entry['purpose']='required_hold_repair' if entry['baseline_ff_ps']<15 else 'optional_guard_margin'
    script=tcl(plan)
    args.out.mkdir(parents=True)
    (args.out/'insert_hold.tcl').write_text(script)
    count=sum(x['count'] for x in plan)
    (args.out/'plan.json').write_text(json.dumps(dict(
        source=args.source,adopted=False,
        checkpoint=checkpoint,
        checkpoint_manifest_sha256=(hashlib.sha256(args.checkpoint_manifest.read_bytes()).hexdigest()
                                    if args.checkpoint_manifest else None),
        input_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [args.outputs,args.internal]},
        output_stages=args.output_stages,
        required_hold_repair_endpoints=sum(x['purpose']=='required_hold_repair' for x in plan),
        optional_guard_margin_endpoints=sum(x['purpose']=='optional_guard_margin' for x in plan),
        cells=count,area_um2=count*.0729,added_cycles=0,added_clock_sinks=0,
        estimated_delay_is_not_measured=True,entries=plan),indent=2)+'\n')


if __name__=='__main__':main()
