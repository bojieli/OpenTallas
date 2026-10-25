# PATH-QC-SRAMIF F6 table in the GEOM-REVIEW form: per SRAM pin group, nearest connected register through <= 4 logic
# levels (reviewer dumpif.py / dumpif_in.py), p50 / max um and count > 20 um.
import sys, re, statistics, collections
mif, inp = sys.argv[1], sys.argv[2]
g = collections.defaultdict(list); regs = collections.defaultdict(set)
def grp(p):
    b = re.sub(r'\[\d+\]$', '', p)
    return {'r_ce_in': 'r_addr/r_ce', 'r_addr_in': 'r_addr/r_ce', 'w_ce_in': 'w_addr/w_ce', 'w_addr_in': 'w_addr/w_ce',
            'wd_in': 'wd_in', 'rd_out': 'rd_out'}.get(b)
for ln in open(mif):
    f = ln.rstrip('\n').split('\t')
    if f[2] == '1' and grp(f[1]) == 'rd_out':
        g[(f[0], 'rd_out')].append(float(f[5])); regs[(f[0], 'rd_out')].add(f[6])
for ln in open(inp):
    f = ln.rstrip('\n').split('\t')
    gg = grp(f[1])
    if gg and gg != 'rd_out' and float(f[4]) >= 0:
        g[(f[0], gg)].append(float(f[4])); regs[(f[0], gg)].add(re.sub(r'\\\[\d+\\\]', '', f[5].split('|')[0]))
allok = True
print('F6\tsram\tgroup\tn\tp50_um\tmax_um\tn_gt20\tdepth')
for (m, gg), v in sorted(g.items()):
    d = sorted({r.split('|')[-1] for r in regs[(m, gg)] if '|' in r})
    n20 = sum(x > 20 for x in v); allok &= n20 == 0
    print('F6\t%s\t%s\t%d\t%.1f\t%.1f\t%d\t%s' % (m.replace('\\', ''), gg, len(v), statistics.median(v), max(v), n20, ','.join(d)))
print('F6_VERDICT', 'PASS' if allok else 'FAIL', '(every SRAM pin group: launch/capture register <= 20 um)')
