#!/usr/bin/env python3
"""DIE-CLOCK: re-point an S81 die STA kit from the PLANNED clock (clock-only CTS plan + balance_latency) to the
MEASURED physical die clock built by tools/die_clock/build.py (Claude DIE-CLOCK 2026-10-16).

  kit_latency.py --kit KIT_DIR --phys BUILD_DIR --out NEW_KIT_DIR
KIT_DIR: tools/s81/die_sta.py kit output (libs_<c>.txt, sta_<c>.tcl, latency_<c>.tcl, kit.json, die.v ...).
BUILD_DIR: build.py output with manifest.json and arrivals_<c>.tsv for c in tt, ff (ss optional; missing ss -> the
  kit's planned ss stays and is marked).
Semantics:
  * pin latency = the MEASURED propagated arrival at the tile clock pin (the tree was trimmed to phi - R, so the
    view's in-arc insertion R is already compensated physically: no balance_latency, no plan + D - R);
  * the ETM clock_tree_path reference compensation of die_sta.sta_latency_lines is applied unchanged;
  * a column clock ck_col_<i> (created on cf<i>/co) gets source latency = the measured stream arrival at its cfifo
    ck pin + the cfifo's ck -> co pass (die_sta.co_delay); column sink latencies are measured from co (their own
    clock root), as the plan's were.
The new kit dir is a copy of the old one (symlinked large files) with latency_<c>.tcl and sta_<c>.tcl rewritten and
clock_physical.json recording sources, hashes and per-tree statistics.
"""
import argparse, hashlib, json, os, re, shutil, statistics, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 's81'))
sys.path.insert(0, str(HERE.parent))


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 23), b''):
            h.update(b)
    return h.hexdigest()


def kit_pin(p):
    inst, port = p.rsplit('/', 1)
    return f"{inst}/{port[:-3] if port.endswith('[0]') else port}"


def lib_index(paths):
    """master -> lib path, from the cell() groups of every lib the kit reads"""
    out = {}
    for p in paths:
        if not os.path.exists(p):
            continue
        with open(p, errors='ignore') as f:
            for m in re.finditer(r'\bcell\s*\(\s*"?([A-Za-z0-9_$]+)"?\s*\)', f.read()):
                out.setdefault(m.group(1), p)
    return out


def read_arr(path):
    a = {}
    for ln in open(path):
        f = ln.rstrip('\n').split('\t')
        try:
            a[f[0]] = float(f[1])
        except (ValueError, IndexError):
            pass
    return a


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--kit', required=True, type=Path)
    ap.add_argument('--phys', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--lib-root', default='', help='prefix to map container lib paths (/kit/...) to this host')
    a = ap.parse_args()
    import die_sta as K   # tools/s81/die_sta.py: sta_latency_lines, co_delay (single source of the ETM convention)
    man = json.loads((a.phys / 'manifest.json').read_text())
    arr = {c: read_arr(a.phys / f'arrivals_{c}.tsv') for c in ('ss', 'ff', 'tt') if (a.phys / f'arrivals_{c}.tsv').exists()}
    if 'tt' not in arr or 'ff' not in arr:
        raise SystemExit('need measured arrivals_tt.tsv and arrivals_ff.tsv (TT setup / FF hold)')
    a.out.mkdir(parents=True, exist_ok=True)
    for f in a.kit.iterdir():
        dst = a.out / f.name
        if dst.exists() or f.name.startswith(('latency_', 'sta_')) or f.name == 'clock_physical.json':
            continue
        if f.is_file() and f.stat().st_size > (1 << 24):
            os.symlink(f.resolve(), dst)
        elif f.is_file():
            shutil.copy2(f, dst)
    libs = {}
    for c in ('ss', 'tt', 'ff'):
        paths = [a.lib_root + p if p.startswith('/kit/') and a.lib_root else p
                 for p in (a.kit / f'libs_{c}.txt').read_text().split()]
        paths = [str(a.kit / Path(p).name) if p.startswith('/kit/') and not a.lib_root else p for p in paths]
        libs[c] = {m: (p, 'closed') for m, p in lib_index(paths).items()}
    lat, pin_master, missing, planned_ss = {}, {}, [], 0
    for p, s in man['sinks'].items():
        v = [arr.get('ss', {}).get(p), arr['ff'].get(p), arr['tt'].get(p)]
        if v[1] is None or v[2] is None:
            missing.append(p)
            continue
        if v[0] is None:
            v[0] = v[2] * 1.45   # no SS measurement: flagged estimate (SS is sensitivity only, owner option B)
            planned_ss += 1
        kp = kit_pin(p)
        lat[kp] = v
        pin_master[kp] = s['master']
    if missing:
        raise SystemExit(f'{len(missing)} sinks without measured TT/FF arrival, e.g. {missing[:5]}')
    rec = dict(schema='opentallas.die_clock.kit_physical.v1', kit=str(a.kit), phys=str(a.phys),
               manifest_sha256=sha(a.phys / 'manifest.json'),
               arrivals_sha256={c: sha(a.phys / f'arrivals_{c}.tsv') for c in arr},
               pins=len(lat), ss_estimated_pins=planned_ss,
               rule='pin latency = measured physical arrival (tree trimmed to phi - R); ETM reference compensation unchanged')
    # column roots: ck_col_<i> -> cfifo inst, measured trunk arrival at its ck + ck -> co pass
    col_src = {}
    for c, ci in (('ss', 0), ('ff', 1), ('tt', 2)):
        text, corr = K.sta_latency_lines(lat, pin_master, libs, c, ci)
        (a.out / f'latency_{c}.tcl').write_text(text)
        sta = (a.kit / f'sta_{c}.tcl').read_text()
        names = dict(re.findall(r'create_clock -name (ck_col_\d+) .*?\{(\S+)/co ', sta))

        def repl(m):
            n_ = m.group(2)
            inst = names.get(n_)
            ck = f'{inst}/ck'
            if inst is None or ck not in lat:
                raise SystemExit(f'column clock {n_}: no measured cfifo ck arrival')
            lp = libs[c].get(pin_master[ck], (None,))[0]
            v = lat[ck][ci] + K.co_delay(lp)
            col_src.setdefault(c, {})[n_] = round(v, 1)
            return f'set_clock_latency -source {v:.1f} [get_clocks {n_}]'
        sta2 = re.sub(r'set_clock_latency -source ([\d.]+) \[get_clocks (ck_col_\d+)\]', repl, sta)
        sta2 = sta2.replace('source /kit/latency_', '# DIE-CLOCK measured physical clock (kit_latency.py)\nsource /kit/latency_', 1)
        (a.out / f'sta_{c}.tcl').write_text(sta2)
    by_tree = defaultdict(list)
    for p, s in man['sinks'].items():
        by_tree[s['tree']].append(arr['tt'][p] + s['R'][2])
    rec['flop_arrival_tt'] = {t: dict(n=len(v), min=round(min(v), 1), max=round(max(v), 1), spread=round(max(v) - min(v), 1))
                              for t, v in sorted(by_tree.items())}
    rec['column_source_latency_ps'] = {c: dict(n=len(v), min=min(v.values()), max=max(v.values())) for c, v in col_src.items()}
    (a.out / 'clock_physical.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps({k: v for k, v in rec.items() if k != 'flop_arrival_tt'}))


if __name__ == '__main__':
    main()
