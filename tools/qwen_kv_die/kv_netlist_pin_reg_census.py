#!/usr/bin/env python3
"""KVPC-R 10-23: pin-register census of a MAPPED flat netlist (ORFS 1_2_yosys.v, ASAP7 cells).

Per top port bit: input -> forward through BUF/INV/HB cells; registered when every reached load is a flip-flop D pin
(no logic, no macro); DEAD when the bit has no load at all.  Output -> backward through BUF/INV/HB to its driver;
registered when that driver is a flip-flop Q/QN.  Reports per port: width, registered, dead, logic (other), and the
max buffer depth.  Usage: kv_netlist_pin_reg_census.py NETLIST.v TOP [OUT.json]
"""
import json
import re
import sys
from collections import defaultdict

BUF = re.compile(r'^(BUF|INV|HB|CKINV|CKBUF)')
SEQ = re.compile(r'^(DFF|DHL|DLL|SDF|ASYNC|ICG)')


def parse(fn, top):
    txt = open(fn).read()
    m = re.search(r'\nmodule %s\((.*?)\nendmodule' % re.escape(top), txt, re.S)
    body = m.group(1)
    ports = {}
    for d, msb, lsb, n in re.findall(r'^\s*(input|output)\s+(?:\[(\d+):(\d+)\]\s+)?(\S+);', body, re.M):
        ports[n] = (d, int(msb or 0), int(lsb or 0), bool(msb))
    insts = []
    for cm, inm, conns in re.findall(r'^\s*(\w+)\s+(\S+)\s*\((.*?)\);', body, re.M | re.S):
        if cm in ('wire', 'input', 'output', 'assign', 'module'):
            continue
        cc = {}
        for pin, net in re.findall(r'\.(\w+)\(([^()]*)\)', conns):
            cc[pin] = net.strip()
        insts.append((cm, inm, cc))
    assigns = re.findall(r'^\s*assign\s+(.*?)\s*=\s*(.*?);', body, re.M)
    return ports, insts, assigns


def main(fn, top, out=None):
    ports, insts, assigns = parse(fn, top)
    alias = {}
    for l, r in assigns:
        alias[l.strip()] = r.strip()
    loads = defaultdict(list)
    drv = {}
    for cm, inm, cc in insts:
        for pin, net in cc.items():
            if not net:
                continue
            net = alias.get(net, net)
            if pin in ('Y', 'Q', 'QN', 'CON', 'SN') or (not BUF.match(cm) and not SEQ.match(cm) and pin.startswith(('Q', 'D', 'O')) and pin not in ('D',)):
                drv[net] = (cm, inm, pin)
            else:
                loads[net].append((cm, inm, pin))
    for l, r in assigns:                       # an output assigned from a net: the output net is the alias target
        pass
    res = {}
    for p, (d, msb, lsb, vec) in ports.items():
        if p in ('ck', 'hck', 'rst_n', 'hrst_n'):
            continue
        reg = dead = logic = 0
        maxd = 0
        for i in range(lsb, msb + 1):
            n = f'{p}[{i}]' if vec else p
            if vec and msb == lsb and n not in loads and n not in drv and p in loads.keys() | drv.keys():
                n = p                                   # a [0:0] port written as a scalar net
            n = alias.get(n, n)
            if d == 'input':
                front, seen, ok, any_load, depth = [n], {n}, True, False, 0
                while front:
                    nf = []
                    for x in front:
                        for cm, inm, pin in loads.get(x, []):
                            any_load = True
                            if SEQ.match(cm):
                                ok = ok and pin == 'D'
                            elif BUF.match(cm):
                                y = cc_out(insts_by_name, inm)
                                if y and y not in seen:
                                    seen.add(y)
                                    nf.append(y)
                            else:
                                ok = False
                    front = nf
                    depth += 1 if nf else 0
                maxd = max(maxd, depth)
                if not any_load:
                    dead += 1
                elif ok:
                    reg += 1
                else:
                    logic += 1
            else:
                x, depth, ok = n, 0, False
                for _ in range(8):
                    dv = drv.get(x)
                    if dv is None:
                        break
                    cm, inm, pin = dv
                    if SEQ.match(cm):
                        ok = True
                        break
                    if BUF.match(cm):
                        x = alias.get(insts_by_name[inm][1].get('A', ''), insts_by_name[inm][1].get('A', ''))
                        depth += 1
                        continue
                    break
                maxd = max(maxd, depth)
                reg += ok
                logic += not ok
        res[p] = dict(dir=d, width=msb - lsb + 1, registered=reg, dead=dead, logic=logic, max_buf_depth=maxd)
    if out:
        json.dump(res, open(out, 'w'), indent=1, sort_keys=True)
    tot = defaultdict(int)
    for p, r in sorted(res.items()):
        for k in ('width', 'registered', 'dead', 'logic'):
            tot[k] += r[k]
        print(f"{p:22s} {r['dir']:6s} w={r['width']:4d} reg={r['registered']:4d} dead={r['dead']:4d} logic={r['logic']:4d} bufdepth={r['max_buf_depth']}")
    print('TOTAL', dict(tot))


insts_by_name = {}


def cc_out(ib, inm):
    return ib[inm][1].get('Y')


if __name__ == '__main__':
    _p, _i, _a = parse(sys.argv[1], sys.argv[2])
    for cm, inm, cc in _i:
        insts_by_name[inm] = (cm, cc)
    main(*sys.argv[1:4])
