#!/usr/bin/env python3
"""Require separate physical FF storage for complementary embedding metadata.
Accepts the actual mapped netlist (not the RTL), parsed without optimization.
An inverter/buffer may carry a stored bit, but complementary bits must
resolve to distinct FF instances. Unsupported combinational cones fail closed.
"""
import argparse,json,re,shutil,subprocess,tempfile
from pathlib import Path
def storage(module, name):
    """Resolve each named bit through only known one-input wires to one FF.

    Technology mapping may invert a stored bit, including reset-polarity
    conversion. Counting the endpoint net itself would reject that legal
    implementation. Resolving both copies to their storage cells also catches
    the unsafe implementation where a shadow is just an inverted primary.
    """
    nets = module['netnames']
    alias = re.fullmatch(r'(fifo|fifo_n)\[(\d+)\]', name)
    if alias:
        stable = f'g_metadata_fifo[{alias.group(2)}].' + ('primary' if alias.group(1) == 'fifo' else 'shadow')
        if stable in nets or any(k.startswith(stable + '[') for k in nets):
            name = stable
    if name in nets:
        bits = nets[name]['bits']
    else:
        split = sorted((int(match.group(1)), net['bits'])
                       for key, net in nets.items()
                       if (match := re.fullmatch(re.escape(name) + r'\[(\d+)\]', key)))
        if not split or [i for i, _ in split] != list(range(len(split))) or any(len(b) != 1 for _, b in split):
            raise AssertionError(f'{name}: missing or non-contiguous split vector storage')
        bits = [b[0] for _, b in split]
    drivers = {}
    for cellname, cell in module['cells'].items():
        kind = cell['type'].lstrip('\\')
        connections = cell['connections']
        if re.search('DFF|dff', kind):
            for port in ('Q', 'QN'):
                for bit in connections.get(port, []):
                    drivers.setdefault(bit, []).append(('ff', cellname))
        elif (kind in ('$_NOT_', '$_BUF_', 'BUFx4f_ASAP7_75t_R', 'BUFx6f_ASAP7_75t_R') or
              re.fullmatch(r'(?:INV|BUF)x(?:[0-9]+(?:p[0-9]+)?|p[0-9]+)_ASAP7_75t_[A-Za-z]+', kind)):
            # Explicit cell whitelist, never traverse arbitrary logic by name.
            if len(connections.get('A', [])) == len(connections.get('Y', [])) == 1:
                drivers.setdefault(connections['Y'][0], []).append(('wire', connections['A'][0]))

    def resolve(bit, seen):
        if bit in seen:
            raise AssertionError(f'{name}: cyclic storage cone at {bit}')
        candidates = drivers.get(bit, [])
        if len(candidates) != 1:
            raise AssertionError(f'{name} bit {bit}: expected one FF or supported buffer/inverter driver, got {candidates}')
        kind, source = candidates[0]
        return source if kind == 'ff' else resolve(source, seen | {bit})

    found = {resolve(bit, set()) for bit in bits}
    if len(found) != len(bits):
        raise AssertionError(f'{name}: aliased FF storage')
    return found


def check_module(m, top):
    scale = 'scale' in top
    pairs = [('fault','fault_n',1),('wp','wp_n',2),('rp','rp_n',2),
             ('credits','credits_n',4),('phase','phase_n',1),
             ('valid_pipe','valid_n',4),('addr_q','addr_n',12),
             ('ce_q','ce_n',1),('iv_q','iv_n',1),('cr_q','cr_n',1)]
    pairs += [('row_q','row_n',18)] if scale else [('ia_q','ia_n',12)]
    pairs += [(f'fifo[{i}]', f'fifo_n[{i}]',18 if scale else 12) for i in range(2)]
    if scale:
        pairs += [(f'lane_pipe[{i}]', f'lane_n[{i}]',4) for i in range(4)]
    checks = {}
    for left, right, width in pairs:
        l, r = storage(m,left), storage(m,right)
        assert len(l) == len(r) == width, (left,right,'incomplete storage',len(l),len(r),width)
        assert not l & r, (left,right,'shared FFs')
        checks[left+'/'+right] = {'primary_FFs':len(l),'shadow_FFs':len(r),'separate':True}
    capture = 'capture' if scale else 'capture_data'
    count = len(storage(m,capture))
    assert count == (256 if scale else 512), (capture,'incomplete storage',count)
    checks[capture] = {'capture_FFs':count}
    count = len(storage(m,'capture_en_q'))
    assert count == (8 if scale else 16), ('capture_en_q','incomplete storage',count)
    checks['capture_en_q'] = {'capture_enable_FFs':count}
    return checks


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--netlist',required=True)
    p.add_argument('--top',required=True)
    p.add_argument('--out',required=True)
    a=p.parse_args()
    y=Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys'
    y=str(y) if y.exists() else shutil.which('yosys')
    with tempfile.TemporaryDirectory(prefix='embedding-retention-') as d:
        q=Path(d)/'mapped.json'
        subprocess.run([y,'-Q','-T','-p',f'read_verilog "{Path(a.netlist).resolve()}"; write_json "{q}"'],check=True,stdout=subprocess.DEVNULL)
        m=json.loads(q.read_text())['modules'][a.top]
        checks=check_module(m,a.top)
    Path(a.out).write_text(json.dumps({'top':a.top,'netlist':str(a.netlist),'verdict':'PASS','checks':checks},indent=2)+'\n')
    print('PASS embedding mapped metadata has independent FF storage')


if __name__ == '__main__':
    main()
