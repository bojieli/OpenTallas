#!/usr/bin/env python3
"""Thread the native dispatcher boot ABI through the actually selected vehicle sources.

Run after vehicle_closure.py, before Verilator. Replacements are private output
copies; the bound source and the staged vehicle remain untouched. A fresh
hierarchy build therefore gets the same HOST ABI as the dispatcher and image.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_host_boot_abi as abi

HOST = re.compile(r'qkd_host_root_admission_obsx_bo1_c45\s*#\s*\((.*?)\)\s*(?:u_host|host)\s*\(', re.S)


def prepare(out):
    out = Path(out).resolve()
    listing = out / 'files.f'
    paths = [Path(s.strip()) for s in listing.read_text().splitlines() if s.strip()]
    paths = list(dict.fromkeys(paths))
    texts = {p: p.read_text() for p in paths}

    def named(name):
        hits = [p for p in paths if p.name == name]
        if not hits:
            raise ValueError(f'native boot ABI: selected list lacks {name}')
        if len({texts[p] for p in hits}) != 1:
            raise ValueError(f'native boot ABI: conflicting selected copies of {name}')
        return hits

    ctl = named('qkd_kvs_ctl_nc32.sv')
    face = named('qkd_kv_ctl_nc32_face.sv')
    loader = named('qkd_host_program_loader_target.sv')
    obsx = named('qkd_host_root_admission_obsx.sv')
    c45 = named('qkd_host_root_admission_obsx_bo1_c45.sv')
    ages = abi.dispatcher_ages(texts[ctl[0]])
    replacements = {p: abi.obsx(texts[p]) for p in obsx}
    replacements.update({p: abi.c45(texts[p]) for p in c45})
    hosts = [(p, m) for p, t in texts.items() for m in HOST.finditer(t)]
    if len(hosts) != 1:
        raise ValueError(f'native boot ABI: expected one selected HOST instance, got {len(hosts)}')
    hp, match = hosts[0]
    params = abi.host_instance_params(match.group(1), ages)
    replacements[hp] = texts[hp][:match.start(1)] + params + texts[hp][match.end(1):]
    host_params = {k: int(v) for k, v in re.findall(r'\.(\w+)\s*\(\s*(\d+)\s*\)', params)}
    lparams = abi.loader_params(replacements[obsx[0]], replacements[c45[0]], host_params)
    eff, dispatch, load, image, errors = abi.check_texts(texts[ctl[0]], texts[face[0]], texts[loader[0]], lparams)
    if errors:
        raise ValueError('native boot ABI mismatch: ' + '; '.join(errors))
    # No source writes occur until the entire selected ABI has been checked.
    target = out / 'boot_abi_sources'
    target.mkdir(exist_ok=True)
    remap, records = {}, []
    for i, (path, text) in enumerate(replacements.items()):
        dst = target / f'{i}_{path.name}'
        dst.write_text(text)
        remap[str(path)] = str(dst)
        records.append({'source': str(path), 'selected': str(dst), 'sha256': hashlib.sha256(text.encode()).hexdigest()})
    listing.write_text('\n'.join(remap.get(str(p), str(p)) for p in paths) + '\n')
    receipt = {'verdict': 'PASS', 'dispatcher': eff, 'loader_params': lparams,
               'dispatcher_words': dispatch, 'loader_words': load, 'image_words': image, 'files': records}
    (out / 'native_boot_abi.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    receipt = prepare(args.out)
    print(f'NATIVE_BOOT_ABI PASS dispatcher AGES {receipt["dispatcher"].get("AGES")} '
          f'loader {receipt["loader_params"]} files {len(receipt["files"])}')


if __name__ == '__main__':
    main()
