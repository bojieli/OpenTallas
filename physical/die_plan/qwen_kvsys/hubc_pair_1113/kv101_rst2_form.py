#!/usr/bin/env python3
"""KV-101/PVFIN private nested-reset form for kv3_hub_C (DO_NOT_COUNT, unsigned, no POR adoption).

Input: the native3 logical form (bare fixed-i1 pair qkd_pv_fin_s2x8_pin_i1 bound as ONE leaf `pvfin`, two plan hard
cores pvfin_lo / pvfin_hi nested at u_bound.u_pvfin.u_pair.g_sl[0/1].u_sl).
Output: the same form with
  * the qualified parent donor selected (source 4675ca42cc,
    rtl/qwen_sys/split_20261014/qkd_pv_fin_s8_pin_physical_model.sv, sha256 checked against the receipt):
    pair qkd_pv_fin_s2x8_pin_i1_rst2 over the FIXED public master qkd_pv_fin_s8_pin (OT_RST_LAND2 + __ot_pr_core).
    The donor REPLACES the staged qkd_pv_fin_s8_pin.sv (never both); hard-core verilog_params are omitted (the public
    master has none; the fixed profile is checked against the receipt instead);
  * the nesting declared to the binder with the existing sub-core mechanism (asbuilt.sub_core_leaf
    {pvfin: pvfin}, hard cores sub_core_parent=pvfin, sub_core_leaf_pin=rst_n): both plan reset targets
    pvfin_lo.rst_n / pvfin_hi.rst_n land on the one bound pair leaf port, which fans out to the two nested slices
    inside the donor.  bind.py keeps both targets and requires their taps to share release depth and START role.
Nothing is dropped: both core_resets rows, taps, depth and the +2 CPC rule stay.
"""
import argparse, copy, hashlib, json, os, pathlib, re, shutil
P = pathlib.Path
OLD = 'qkd_pv_fin_s2x8_pin_i1'
NEW = 'qkd_pv_fin_s2x8_pin_i1_rst2'
LEAF_MASTER = 'qkd_pv_fin_s8_pin'
ROOT = 'u_bound.u_pvfin.u_pair'
DONOR_SHA = '9b7d02d5816224f94d5eddcc1f48c957a643a7e3d0ca109fdb04c10c1ceb0522'
PROFILE = {'ADD_LAT': 7, 'MUL_LAT': 6, 'SKEW': 1, 'MUT': 0, 'NL': 8, 'IN_STAGE': 1}
OLD_PIN = 'physical/die_plan/qwen_kvsys/hubc_pair_1113/source/qkd_pv_fin_s8_pin.sv'


def sha(p):
    return hashlib.sha256(P(p).read_bytes()).hexdigest()


def check_donor(text, receipt):
    if receipt['selected_parent_pair'] != NEW or receipt['physical_master'] != LEAF_MASTER:
        raise ValueError('receipt does not select the rst2 pair over the fixed public master')
    if receipt['params'] != PROFILE or receipt['reset_landing_stages'] != 2 or receipt['data_CPC_delta'] != 2:
        raise ValueError('receipt profile / reset landing / CPC changed')
    head = re.search(r'module\s+' + LEAF_MASTER + r'\s*(#?)\s*\(', text)
    if not head or head.group(1):
        raise ValueError('public qkd_pv_fin_s8_pin must exist and carry no parameters')
    if len(re.findall(r'^\s*module\s+' + LEAF_MASTER + r'\b', text, re.M)) != 1:
        raise ValueError('donor must define qkd_pv_fin_s8_pin exactly once')
    body = text.split('module ' + LEAF_MASTER + ' ', 1)[1].split('endmodule', 1)[0]
    if body.count('__ot_rl') < 4 or '.rst_n(rst_n__ot_rl1)' not in body:
        raise ValueError('public master must land rst_n in two stages before the core')
    pr = text.split('module ' + NEW, 1)[1].split('endmodule', 1)[0]
    if 'begin:g_sl' not in pr or not re.search(LEAF_MASTER + r'\s+u_sl\s*\(\s*\.ck\(ck\),\s*\.rst_n\(rst_n\)', pr):
        raise ValueError('rst2 pair must instantiate the fixed master as g_sl[*].u_sl with the pair rst_n')
    if 'module ' + OLD + ' ' in text or 'module ' + OLD + '\n' in text:
        raise ValueError('donor must not also define the old pair')


def form(plan, ab, receipt, donor_rel, core_rel, tsv_rel, donor_text, bound_text):
    p, a = copy.deepcopy(plan), copy.deepcopy(ab)
    check_donor(donor_text, receipt)
    heads = re.findall(OLD + r"\s+#\((.*?)\)\s+u_pvfin\s*\(", bound_text)
    if len(heads) != 1:
        raise ValueError('expected one bound pvfin pair instance')
    if dict(re.findall(r"\.(\w+)\(([^()]*)\)", heads[0])) != {'ADD_LAT': '7', 'MUL_LAT': '6', 'MUT': '0', 'SKEW': '1'}:
        raise ValueError('bound pvfin parameters differ from the rst2 guard')
    t = p['partition_types']['kv3_hub_C']
    content = [c for c in t['contents'] if c['inst'] == 'pvfin']
    if len(content) != 1 or content[0]['module'] != OLD:
        raise ValueError('expected native3 pvfin content selecting the bare pair')
    rows = [h for h in t.get('hard_cores', []) if h['inst'] in ('pvfin_lo', 'pvfin_hi')]
    if sorted(h['inst'] for h in rows) != ['pvfin_hi', 'pvfin_lo']:
        raise ValueError('two nested pvfin hard cores required')
    for h in rows:
        k = 0 if h['inst'] == 'pvfin_lo' else 1
        if h['physical_inst'] != f'{ROOT}.g_sl[{k}].u_sl' or h['physical_master'] != LEAF_MASTER:
            raise ValueError(f"{h['inst']}: nested physical path/master changed")
        if h.get('verilog_params') != PROFILE:
            raise ValueError(f"{h['inst']}: native3 profile differs from the receipt")
        if h.get('sub_core_parent') or h.get('reset_from_master'):
            raise ValueError(f"{h['inst']}: already carries a reset binding form")
        del h['verilog_params']                       # public fixed master: no parameters (profile = receipt)
        h['sub_core_parent'] = 'pvfin'
        h['sub_core_leaf_pin'] = 'rst_n'
        h['note'] = h.get('note', '') + (' | KV-101/PVFIN: nested in bound leaf pvfin (rst2 donor 4675ca42cc); '
                                          'reset = pair rst_n -> OT_RST_LAND2 per slice; DO_NOT_COUNT')
    content[0]['module'] = NEW
    content[0]['note'] = ('Selected qualified rst2 pair (4675ca42cc) over fixed qkd_pv_fin_s8_pin; two nested hard '
                          'children; +2 output cycles; DO_NOT_COUNT')
    for k in ('files', 'prefer'):
        lst = a.setdefault(k, [])
        if OLD_PIN not in lst:
            raise ValueError(f'{k}: staged old pin source not found')
        lst[lst.index(OLD_PIN)] = donor_rel          # replace, never both
        if core_rel not in lst:
            raise ValueError(f'{k}: qkd_pv_fin_s8 core source missing')
    subs = [s for s in a.get('substitute_inst', []) if s.get('inst') == 'pvfin']
    if len(subs) != 1 or subs[0]['module'] != OLD:
        raise ValueError('expected one pvfin substitute of the bare pair')
    subs[0]['module'] = NEW
    subs[0]['reason'] = ('PRIVATE qualified rst2 pair (4675ca42cc): fixed IN_STAGE1 + PIN stage + OT_RST_LAND2 per '
                         'slice; exact same ports; +2 output cycles')
    cpc = [c for c in a.get('core_pin_cycles', []) if c.get('inst') == 'pvfin']
    if len(cpc) != 1:
        raise ValueError('expected one pvfin core_pin_cycles row')
    cpc[0]['module'] = NEW
    cpc[0]['tsv'] = tsv_rel
    scl = a.setdefault('sub_core_leaf', {})
    if 'pvfin' in scl:
        raise ValueError('sub_core_leaf pvfin already declared')
    scl['pvfin'] = 'pvfin'
    a['sub_core_leaf_note'] = (a.get('sub_core_leaf_note', '') + ' KV-101/PVFIN 11-13: kv3_hub_C pvfin_lo/hi are '
                               'nested in the one bound pair leaf pvfin (u_pair.g_sl[0/1].u_sl); one leaf rst_n feeds '
                               'both slices.').strip()
    a['pvfin_reset_receipt'] = dict(source_commit='4675ca42ccabaa272f17fa1caafd7bd74916465d', donor=donor_rel,
                                    donor_sha256=DONOR_SHA, routed_eq='PENDING')
    return p, a


def main():
    q = argparse.ArgumentParser(description=__doc__)
    for n in ('src', 'out', 'repo', 'receipt', 'donor', 'core', 'bound'):
        q.add_argument('--' + n, required=True)
    x = q.parse_args()
    src, out, repo = P(x.src), P(x.out), P(x.repo).resolve()
    if sha(x.donor) != DONOR_SHA:
        raise ValueError('donor bytes differ from the receipt')
    receipt = json.loads(P(x.receipt).read_text())
    if receipt['sources'][0]['sha256'] != DONOR_SHA:
        raise ValueError('receipt source sha mismatch')
    out.mkdir(parents=True, exist_ok=False)
    own = {'plan_c.json', 'asbuilt_vN.json', 'core_pin_cycles.tsv'}
    for e in src.iterdir():                          # hard links: no file of the input is written
        if e.name in own:
            continue
        (shutil.copytree(e, out / e.name, copy_function=os.link) if e.is_dir() else os.link(e, out / e.name))
    tsv = out / 'core_pin_cycles.tsv'
    old_tsv = (src / 'core_pin_cycles.tsv').read_text()
    tsv.write_text(old_tsv)                          # same +2 CPC rule (reset landing adds no data cycle)
    ab = json.loads((src / 'asbuilt_vN.json').read_text())
    if (src.resolve() / ab['base']).resolve() == repo:
        pass
    ab['base'] = os.path.relpath(repo, out.resolve())
    rel = lambda f: str(P(f).resolve().relative_to(repo))
    p, a = form(json.loads((src / 'plan_c.json').read_text()), ab, receipt, rel(x.donor), rel(x.core), rel(tsv),
                P(x.donor).read_text(), P(x.bound).read_text())
    (out / 'plan_c.json').write_text(json.dumps(p, indent=1) + '\n')
    (out / 'asbuilt_vN.json').write_text(json.dumps(a, indent=1) + '\n')
    print('PRIVATE rst2 nested-reset form written; no geometry, bind or physical qualification')


if __name__ == '__main__':
    main()
