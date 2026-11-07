#!/usr/bin/env python3
"""Private Wi pilot: expose bound-only io_pad_die_id[2:0] as declared ID strap strap_io_pad_die_id[2:0] (OWNER 10-25 option B,
COORD 11-07 08:04 ruling 3).  Bit-exact rename at the partition top only; the child port keeps its name.  No tie value here:
the package map (docs/QWEN_TP8_HOST_TRANSPORT.md, kv_die.py:1004) sets the value per package location."""
import hashlib, json, re, shutil, sys
from pathlib import Path
k = Path(sys.argv[1]).resolve(); bk = k/'alias_before'; bk.mkdir(exist_ok=False)
OLD, NEW = 'io_pad_die_id', 'strap_io_pad_die_id'; TOP = 'kv3_hub_Wi_part'
base = k/'run/results/asap7/dp_kv3_hub_Wi/base'
sha = lambda b: hashlib.sha256(b).hexdigest()
rec = dict(schema='opentallas.private_strap_alias.v1', type='kv3_hub_Wi', old=OLD, new=NEW, width=3,
           map={f'{OLD}[{i}]': f'{NEW}[{i}]' for i in range(3)}, rule='OWNER 10-25 option B; COORD 11-07 08:04 (3)',
           tie_value=None, value_source='package identity strap, per package location: docs/QWEN_TP8_HOST_TRANSPORT.md:167, tools/qwen_kv_die/kv_die.py:1004; one mask, eight locations, so no literal value exists at die level',
           por=False, files={})
def save(p):
    d = bk/p.relative_to(k); d.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, d)
def write(p, new):
    old = p.read_bytes(); save(p); p.write_bytes(new); rec['files'][str(p.relative_to(k))] = dict(before=sha(old), after=sha(new))
# RTL: declaration and the one connection at the partition top
p = k/'rtl/kv3_hub_Wi_part.sv'; s = p.read_text()
a1 = 'input  wire [2:0] io_pad_die_id,  // bound-only pin (die IO / reset spine / clock role): not a plan bus'
b1 = 'input  wire [2:0] strap_io_pad_die_id,  // OWNER 10-25 option B ID strap: package identity, set at package assembly'
a2 = '.io_pad_die_id(io_pad_die_id),'; b2 = '.io_pad_die_id(strap_io_pad_die_id),'
assert s.count(a1) == 1 and s.count(a2) == 1 and len(re.findall(r'\bio_pad_die_id\b', s)) == 3
write(p, s.replace(a1, b1).replace(a2, b2).encode())
# Mapped netlist: top module only, exact token
p = base/'1_2_yosys.v'; s = p.read_text()
m = re.search(r'(?ms)^module ' + TOP + r'\b.*?^endmodule\b', s); assert m
tok = re.compile(r'(?<![\w.\\$])' + OLD + r'\b')
assert len(re.findall(OLD, s)) == len(tok.findall(m.group(0))) == 25 and NEW not in s
top = tok.sub(NEW, m.group(0)); n = s[:m.start()] + top + s[m.end():]
assert re.sub(r'\bstrap_' + OLD + r'\b', OLD, n) == s, 'rename is not reversible'
rec['netlist_tokens_renamed'] = 25; write(p, n.encode())
# SDC: the one strap false path, kept byte-identical between kit and flow copy
s = (k/'constraint.sdc').read_bytes(); assert s == (base/'1_2_yosys.sdc').read_bytes()
t = s.decode(); fp = 'set_false_path -from [get_ports {strap_ca_efall '
assert t.count(fp) == 1 and OLD not in t
n = t.replace(fp, 'set_false_path -from [get_ports {' + NEW + ' strap_ca_efall ').encode()
write(k/'constraint.sdc', n); write(base/'1_2_yosys.sdc', n)
# Declarations
def jw(name, f):
    p = k/name; j = json.loads(p.read_text()); f(j); write(p, (json.dumps(j, indent=1) + '\n').encode())
jw('straps.json', lambda j: j['straps'].append(NEW))
def lint(j):
    assert OLD not in j['inputs'] and NEW not in j['inputs']; j['inputs'].append(NEW); j['straps'].append(NEW)
jw('sdc_lint.json', lint)
jw('port_bind_pins.json', lambda j: j.extend(dict(bus=NEW, bit=i) for i in range(3)))
# Stale products of the old names: keep them as evidence, the runner rebuilds them
for r in ('FAIL_PREFLOOR', 'port_bind.json', 'port_bind.log', 'run/results/asap7/dp_kv3_hub_Wi/base/1_synth.odb', 'run/results/asap7/dp_kv3_hub_Wi/base/1_synth.sdc'):
    d = bk/r; d.parent.mkdir(parents=True, exist_ok=True); shutil.move(str(k/r), d)
(k/'.kwrs_done.1').unlink(missing_ok=True)
(k/'STRAP_ALIAS.json').write_text(json.dumps(rec, indent=1) + '\n')
print(json.dumps({x: rec[x] for x in ('new', 'netlist_tokens_renamed', 'tie_value')}))
