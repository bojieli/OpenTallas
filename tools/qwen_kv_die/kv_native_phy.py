"""Bind licensed link PHYs to their actual published LEF, Liberty and ports.

A die-facing FDI bundle is a planning convention, not a hard-macro RTL port.
The emitted die netlist must use tx_up/tx_v/tx_flit/rx_v/rx_flit and carry
exactly the width of the published macro. No implicit truncation is allowed.
"""
import argparse
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PHY = {
    'ot_qkvd_ucie_x64_phy': ROOT/'physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy',
    'ot_qfd_serdes_112g_x12_phy': ROOT/'physical/qwen_missing_phy/ot_qfd_serdes_112g_x12_phy',
}


def bind(case, only=None):
    import die_port_bind_kv as P
    wires, instances = P.parse_die(case/'die.v')
    text = (case/'die.v').read_text()
    lef = (case/'elements.lef').read_text()
    record = {}
    for master, directory in PHY.items():
        if only and master not in only:
            continue
        matches=[(inst,conns) for m,inst,conns in instances if m==master]
        if not matches:
            continue
        params,ports=P.header((directory/(master+'_bb.v')).read_text(),master)
        widths={p:P.evalw(w,params or {}) for p,(_,w) in ports.items()}
        fields=['tx_up','tx_v','tx_flit','rx_v','rx_flit']
        expected=sum(widths[p] for p in fields)
        for inst,conns in matches:
            cm=dict(re.findall(r'\.(\S+?)\(([^()]*)\)',conns))
            if 'fdi' not in cm:
                continue
            width=P.die_ports('.fdi('+cm['fdi']+')',wires)['fdi']
            if width != expected:
                raise ValueError(f'{inst}: FDI has {width} bits, native {master} needs {expected}; bind the real CRC/retry layer first')
            bus=cm.pop('fdi')
            if not re.fullmatch(r'\w+',bus):
                raise ValueError(f'{inst}: FDI must be one declared native-width bus, got {bus}')
            offset=0
            for p in fields:
                w=widths[p];cm[p]=f'{bus}[{offset}]' if w==1 else f'{bus}[{offset+w-1}:{offset}]';offset+=w
            old=f'  {master} {inst} ({conns});'
            new=f'  {master} {inst} ('+', '.join(f'.{p}({e})' for p,e in cm.items())+');'
            if text.count(old)!=1:
                raise ValueError(f'{inst}: ambiguous emitted instance')
            text=text.replace(old,new)
        raw=(directory/(master+'.lef')).read_text()
        macro=re.search(rf'^MACRO {master}\s*$.*?^END {master}\s*$',raw,re.M|re.S)
        if not macro:
            raise ValueError(f'no native LEF for {master}')
        original=re.compile(rf'^MACRO {master}\s*$.*?^END {master}\s*$',re.M|re.S)
        if len(original.findall(lef))!=1:
            raise ValueError(f'no unique planning macro for {master}')
        lef=original.sub(lambda _:macro.group(0),lef)
        record[master]=dict(directory=str(directory.relative_to(ROOT)),instances=len(matches),fdi_bits=expected,
                            ports=widths,qualification='LICENSED_ANALOG_ABSTRACT; digital link remains real RTL')
    # Mutate only after every width and port check passed.
    (case/'die.v').write_text(text)
    (case/'elements.lef').write_text(lef)
    (case/'native_phy.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def libraries(case,libs):
    from bind_views import strip_cell
    record=json.loads((case/'native_phy.json').read_text())
    for master in record:
        for corner in ('tt','ff','ss'):
            path=libs/f'qfd_elements_{corner}.lib'
            if path.exists():
                clean,_=strip_cell(path.read_text(),master);path.write_text(clean)
            shutil.copyfile(PHY[master]/f'{master}_{corner}.lib',libs/f'qfd_etm_{master}_{corner}.lib')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',type=Path,required=True)
    parser.add_argument('--libs',type=Path)
    parser.add_argument('--only',default='',help='comma list of PHY masters (kvsys v1.4: the SerDes binds; UCIe waits for the 583-b static link)')
    args=parser.parse_args()
    if args.libs:
        libraries(args.case,args.libs)
    else:
        print(json.dumps(bind(args.case,[x for x in args.only.split(',') if x] or None)))
