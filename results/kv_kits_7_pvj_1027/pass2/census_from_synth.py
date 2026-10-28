"""KV-KITS-7 10-28: re-derive the pv_join entry-trunk sink census from the kit's OWN synthesized netlist.

The pass2 census was carried from the old placed netlist. QK-CORES-10 4eeb71cf7 (fp32 add DRST0) changed the
yosys cell identity of g_join[*].u_add.err[0] from $_SDFF_PN0_ to $_DFF_P_, so the carried census named 16 sinks
that no longer exist and core_infra CTS stopped (OT_CORE_INFRA_SINK_INSTANCE, autopilot 123ab8799e77/f4fe40e9cd9b).
Sinks = every register CLK pin on net clk in 1_synth_odb.v (OpenDB write_verilog of the synthesized ODB), in
OpenDB name form (brackets escaped as in the carried census). No alias, no waiver: fail closed unless the new set
has the same count and the same register multiset once the yosys cell-type suffix is ignored.
usage: census_from_synth.py OLD_CENSUS NETLIST OUT
"""
import collections, hashlib, json, re, sys

old_p, net_p, out_p = sys.argv[1:4]
old = json.load(open(old_p))
txt = open(net_p).read()
new = []
for m in re.finditer(r'^\s*(\w+)\s+(\\\S+|\w+)\s+\((.*?)\);', txt, re.S | re.M):
    _cell, name, body = m.groups()
    for pin, net in re.findall(r'\.(\w+)\((\S+?)\)', body):
        if net == 'clk' and pin == 'CLK':
            n = name[1:] if name.startswith('\\') else name
            new.append(n.replace('[', '\\[').replace(']', '\\]') + '/' + pin)
strip = lambda s: re.sub(r'\$_\w+_/', '$/', s)
assert len(new) == len(set(new)), 'duplicate sinks'
if collections.Counter(map(strip, old['sinks'])) != collections.Counter(map(strip, new)):
    sys.exit('CENSUS_FAIL register set differs beyond yosys cell-type suffix')
by = {strip(s): s for s in new}
sinks = [by[strip(s)] for s in old['sinks']]  # keep carried order
changed = sorted(set(old['sinks']) - set(sinks))
out = dict(old)
out['sinks'] = sinks
out['census_source'] = dict(netlist=net_p, netlist_sha256=hashlib.sha256(txt.encode()).hexdigest(), rule='register CLK pins on net clk, OpenDB name form',
                            carried_from=old_p, renamed=len(changed))
json.dump(out, open(out_p, 'w'), indent=1)
open(out_p, 'a').write('\n')
print('CENSUS_PASS sinks', len(sinks), 'renamed', len(changed), changed[:2])
