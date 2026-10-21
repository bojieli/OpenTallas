"""Source-pinned single real clock; an actual parent clock is not an SDC frequency waiver.

Evidence comprises the complete parent GEN manifest, native source contract and GEN SDC.
Every consumed instance clock must connect directly to the declared real source.
The tile RTL and parameters are separately bound, so edited hardware invalidates it.
"""
import hashlib
import json
import math
import re
from pathlib import Path

SCHEMA = 'opentallas.single_clock_contract.v1'
ROOT = Path(__file__).resolve().parents[2]


def _number(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError('single_clock_contract: period must be finite and positive')
    return float(value)


def _file(root, item):
    if not isinstance(item, dict) or set(item) != {'path', 'sha256'}:
        raise ValueError('single_clock_contract: evidence needs exact path/sha256')
    rel = item['path']
    if not isinstance(rel, str) or not re.fullmatch(r'[A-Za-z0-9_./-]+', rel) or Path(rel).is_absolute() or '..' in Path(rel).parts:
        raise ValueError('single_clock_contract: unsafe evidence path')
    path = Path(root) / rel
    if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
        raise ValueError('single_clock_contract: stale evidence hash: ' + rel)
    return path


def evidence_paths(spec):
    c = spec.get('single_clock_contract')
    return [c[k]['path'] for k in ('manifest', 'native_contract', 'sdc')] if c else []


def validate(spec, root=None):
    c = spec.get('single_clock_contract')
    if c is None:
        return None
    root = ROOT if root is None else Path(root)
    keys = {'schema', 'clock_port', 'period_ps', 'top', 'params', 'sources_sha256',
            'manifest', 'native_contract', 'sdc', 'domain', 'source', 'instances', 'consumer_master'}
    if not isinstance(c, dict) or set(c) != keys or c['schema'] != SCHEMA:
        raise ValueError('single_clock_contract: exact v1 schema required')
    if spec.get('kind', 'tile') != 'tile' or spec.get('clock', 'cts') not in ('cts', 'spine'):
        raise ValueError('single_clock_contract: ordinary single-clock tile only')
    if any(spec.get(k) for k in ('clock_ports', 'clock_entry_domains', 'clock_relationship', 'clock_data_paths',
                                 'sdc_extra', 'forwarded_clock', 'cdc_synchronizers')):
        raise ValueError('single_clock_contract: secondary/relationship clocks are forbidden')
    if c['clock_port'] != spec.get('clock_port') or c['top'] != spec.get('top') or c['params'] != spec.get('params', {}):
        raise ValueError('single_clock_contract: tile clock/top/params mismatch')
    sources = spec.get('sources', [])
    if not sources or not isinstance(c['sources_sha256'], dict) or set(c['sources_sha256']) != set(sources):
        raise ValueError('single_clock_contract: bind every actual tile source')
    for rel, sha in c['sources_sha256'].items():
        _file(root, dict(path=rel, sha256=sha))
    period = _number(c['period_ps'])
    route = spec.get('route', {})
    if any(_number(route.get(k)) != period for k in ('period_ps', 'signoff_period_ps')):
        raise ValueError('single_clock_contract: route/signoff must equal actual source period')
    manifest = json.loads(_file(root, c['manifest']).read_text())
    native = json.loads(_file(root, c['native_contract']).read_text())
    if manifest.get('input_sha256', {}).get('contract') != c['native_contract']['sha256']:
        raise ValueError('single_clock_contract: manifest/native source hash mismatch')
    sdc = _file(root, c['sdc']).read_text()
    domain = c['domain']
    if not isinstance(domain, str) or not re.fullmatch(r'[A-Za-z0-9_]+', domain):
        raise ValueError('single_clock_contract: invalid domain')
    if manifest.get('clock_domains', {}).get(domain, {}).get('period_ps') != period:
        raise ValueError('single_clock_contract: manifest domain period mismatch')
    source = c['source']
    if not isinstance(source, dict) or set(source) != {'instance', 'pin', 'master'} or any(
            not isinstance(v, str) or not re.fullmatch(r'[A-Za-z0-9_]+', v) for v in source.values()):
        raise ValueError('single_clock_contract: exact actual source instance/pin/master required')
    if native.get('instances', {}).get(source['instance'], {}).get('master') != source['master']:
        raise ValueError('single_clock_contract: wrong native source instance/master')
    instances = c['instances']
    if not isinstance(instances, dict) or not instances or any(
            not isinstance(k, str) or not re.fullmatch(r'[A-Za-z0-9_]+', k) or
            not isinstance(v, str) or not re.fullmatch(r'[A-Za-z0-9_]+', v) for k, v in instances.items()):
        raise ValueError('single_clock_contract: explicit consumed instances required')
    master = c['consumer_master']
    if not isinstance(master, str) or not re.fullmatch(r'[A-Za-z0-9_]+', master):
        raise ValueError('single_clock_contract: invalid consumed native master')
    family = {k for k, v in native.get('instances', {}).items() if v.get('master') == master}
    if family != set(instances):
        raise ValueError('single_clock_contract: consumed native family instance count mismatch')
    entries = manifest.get('clock_entry_map', {}).get(domain, {})
    # The evidence lists exactly the consumed family, not a guessed count or aliases.
    native_entries = {k: v for k, v in entries.items() if k in instances}
    if native_entries != {k: [k, v] for k, v in instances.items()}:
        raise ValueError('single_clock_contract: manifest instance entry mismatch')
    clocks = [row for row in native.get('clock_resets', []) if row.get('kind') == 'clock' and row.get('instance') in instances]
    expected = {k: dict(port=v, domain=domain, source=[source['instance'], source['pin']]) for k, v in instances.items()}
    actual = {}
    for row in clocks:
        inst = row['instance']
        if inst in actual or row.get('bits') != 1:
            raise ValueError('single_clock_contract: ambiguous native clock entry ' + inst)
        actual[inst] = {k: row.get(k) for k in ('port', 'domain', 'source')}
    if actual != expected:
        raise ValueError('single_clock_contract: wrong native source/domain/port')
    source_pin = source['instance'] + '/' + source['pin']
    clocks = re.findall(r'create_clock\s+-name\s+([A-Za-z0-9_]+)\s+-period\s+([0-9.]+)\s+\[get_pins\s+\{?([^}\] ]+)\}?\]', sdc)
    actual = [(n, float(t)) for n, t, pin in clocks if pin == source_pin]
    if not actual or set(actual) != {(domain, period)}:
        raise ValueError('single_clock_contract: actual GEN source SDC period/root mismatch')
    return period


def guard(spec):
    if not spec.get('single_clock_contract'):
        return ''
    p = validate(spec)
    port = spec['clock_port']
    return f"set ::ot_single_clock_period_ps {p}\nset ::ot_single_clock_port {{{port}}}\n" + r'''
proc ot_single_clock_check {} {
  set real 0
  foreach c [all_clocks] {
    set n [get_full_name $c]
    set sources [get_property $c sources]
    if {[llength $sources]} {
      incr real
      if {$n ne "core_clk" || [llength $sources] != 1 || [get_full_name [lindex $sources 0]] ne $::ot_single_clock_port} {
        error "OT_SINGLE_CLOCK wrong actual root $n"
      }
    } elseif {![regexp {^(vclk[A-Za-z0-9_]*|ot_lb_v_core_clk|nbr_clk)$} $n]} {
      error "OT_SINGLE_CLOCK unowned virtual clock $n"
    }
    if {abs([get_property $c period] - $::ot_single_clock_period_ps) > 0.001} {
      error "OT_SINGLE_CLOCK period mismatch $n expected $::ot_single_clock_period_ps"
    }
  }
  if {$real != 1} { error "OT_SINGLE_CLOCK expected exactly one real root" }
  puts "OT_SINGLE_CLOCK PASS actual/virtual period $::ot_single_clock_period_ps"
}
ot_single_clock_check
'''
