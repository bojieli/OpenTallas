#!/usr/bin/env python3
"""TOK-HBM-1: compile the current four-role FUSED calendar + START authority from BOUND latencies (one rule).

Input 1 (--jobs): the jobs.json receipt of a first fused_job217_emit.py pass WITHOUT --calendar (status MISSING; it
  lists every exact native FUSED record: image_offset, op, fields.nm1, and the image sha256).
Input 2 (--bound): the bound-latency file of the CURRENT die plan/bind (die owner). Every number carries provenance;
  a leg without cycles is MISSING and nothing executable is produced (fail closed, never a default):
    {"source_plan_commit": "<40 hex>", "plan_sha256": "...",
     "legs": {<name>: {"cycles": int, "source": "lane ids / bind report"}},
     "rtl":  {<name>: {"value": int, "source": "file:line"}}}
  legs  : reset_SW reset_SE reset_NW reset_NE reset_root   (die reset source release -> role reset pin, wavefront)
          host_to_provider     (host leaf write -> provider load port)
          provider_to_root     (provider job_v -> root capture input, excl. the 1-edge dispatch)
          root_to_provider     (root done -> provider rd_done, excl. the 2-edge status check)
          down_NW down_NE      (root command out -> farthest leaf of that role, incl. n4)
          up_NW up_NE          (farthest leaf -> root t5 input, incl. n4, before the t5 pad)
  rtl   : rr (VM read return, ot_hnx_fused_hub RR), reset_release_edges (reset_contract 2+HOLD),
          reset_sync_stages (delivered_reset pipe), host_write_interval (host ABI edges per write)
Input 3 (--service): measured root service cycles per (op, n) from a component bench (root capture -> root done):
    {"source": "...", "cycles": {"HC_PRE/1": int, "HC_POST/6": int, ...}}
  OR (TOK-HBM-2) a composed segments file (schema opentallas.hbm.fused_service_segments.v1, results/tok_hbm_2_1028/
  service_segments.json): measured root/lane/tnode segment constants; service = composed_service() per record from wsc
  and the bound station round trip (the bound file must say legs_exclude_tree_nodes: true; wsc then adds node edges).
  A selected physical shell is opt-in service.tnode.external_face_shell = {levels, input_cycles, output_cycles, source};
  levels counts serial external n1..n4 nodes, never total instance count or internal root t5.
Optional (--ready): per-record operand-ready edges from the layer calendar {image_offset: cycle}; without it the
  scope is FUSED-only (records back-to-back) and the receipt says so.

THE ONE RULE (every constant is a sum of bound legs + RTL contract constants; nothing is hand-set):
  boot_release_offsets[r] = reset_release_edges + reset_r + reset_sync_stages          (r in SW SE NW NE root)
  rt_r  = down_r + up_r                          (role round trip root -> farthest leaf -> root, pads aligned)
  wsc   = max(rt_r) + rr + 8                     (the tree form of ot_hnx_fused_eng WSC = 2*RL + RR + 8)
  pk5   = |rt_NW - rt_NE|; pb5 = 1 iff rt_NE < rt_NW (t5 pads its EARLIER child: a = NW, b = NE)
  node pads below t5 (n1..n4 per hub) follow the same rule per node from the plan's internal mu_tree stations
  (--plan: hub_tree_pads(); 1 edge per internal station register)
  preload: host writes = 1 + 16*count + 1 (fused_host_boot_emit), complete = host0 + writes*interval + host_to_provider
  commit = preload_complete + (8 cfg256 + f28 + f2c)*interval;  START = max(commit + 1, max(boot) + 6 + pad_warm)
  launch_i = max(prev_deadline + 4, START + 3, ready_i); root_capture = launch + 1 + provider_to_root
  root_done = root_capture + service(op, n); deadline = root_done + 2 + root_to_provider
  F30 launch (START authority) is issued at START - 3 (hostleaf_to_provider_start_cycles of fused_host_boot_emit).
"""
import argparse, hashlib, json, re, sys
from pathlib import Path

ROLES = {'NWq0': 'SW', 'NEq0': 'SE', 'NWq1': 'NW', 'NEq1': 'NE'}   # canonical four-role VMS map (TOK-HBM 10-27)
LEGS = ['reset_SW', 'reset_SE', 'reset_NW', 'reset_NE', 'reset_root', 'host_to_provider', 'provider_to_root',
        'root_to_provider', 'down_NW', 'down_NE', 'up_NW', 'up_NE']
RTL = ['rr', 'reset_release_edges', 'reset_sync_stages', 'host_write_interval']
PAD_WARM = 32           # ot_hnx_fused_pad depth 0..32: full warm before START (fused_job217_emit requires >= 32)
FETCH, START_EDGES, STATUS = 2, 1, 2   # actual provider contract (fused_job217_emit checks these exact values)


SEG_SCHEMA = 'opentallas.hbm.fused_service_segments.v1'



def tnode_roundtrips(tnode):
    """Measured bare node edges plus explicitly selected physical face shells.

    Four external n1..n4 levels get the new shell; t5 is inside the root core.
    The selected level count is required, never inferred from instance count.
    No optional field preserves the component-only measurement byte for byte.
    """
    extra = tnode.get('external_face_shell')
    delta = 0
    if extra is not None:
        if (not isinstance(extra, dict) or not extra.get('source') or
                any(type(extra.get(k)) is not int or extra[k] < 0
                    for k in ('levels', 'input_cycles', 'output_cycles')) or
                extra['levels'] > tnode['levels']):
            raise ValueError('explicit selected tnode face-shell levels/ages/source required')
        # A path crosses the input and output face once down and once up.
        delta = 2 * extra['levels'] * (extra['input_cycles'] + extra['output_cycles'])
    return (tnode['levels'] * (tnode['down'] + tnode['up_scalar']) + delta,
            tnode['levels'] * (tnode['down'] + tnode['up_chunk']) + delta)


def composed_service(seg, op, n, rgap, wsc, rt_max):
    """TOK-HBM-2: root capture -> root done COMPOSED from measured component segments (root wrapper bench + one-lane /
    one-tnode bench, results/tok_hbm_2_1028) and the bound station round trip rt_max = max_r(down_r + up_r) (station /
    lane registers only; tree-node edges come from the measured tnode constants). Static calendar, so:
      go     = wsc + nsc + go_const + min(n, 2) * nbt                      (root: capture -> GO on its command bus)
      row II = pre_row_ii / post 100, + rgap per row (affine in rgap: measured at rgap 0 / 4 / 12)
      HC_POST: go + rt_s + post_go_to_fin(n) + fin_to_done                  (rt_s = L (node_down + node_up_scalar) + rt_max)
      HC_PRE : go + rt_c + cs_last(n) + pre_sum_to_r + rt_s + pre_r_to_fin + fin_to_done   (rt_c with node_up_chunk)
    PRE x-slot rule (lane KX slots): for n > KX the r round trip rt_c + pre_sum_to_r must be <= the measured limit at
    the record's rgap (limit + KX rgap), else the lane FAULTs (no service; the compiler must raise rgap). Returns (cycles, problem)."""
    r, l, t = seg['root'], seg['lane'], seg['tnode']
    if not 0 <= rgap <= 255:
        return None, f'{op}/{n}: rgap {rgap} outside the 8-bit job field'
    post = op == 'HC_POST'; nbt = 5 if post else 1; nsc = 3 * n if post else n
    go = wsc + nsc + r['go_const'] + min(n, 2) * nbt
    node_s, node_c = tnode_roundtrips(t)
    rt_s = node_s + rt_max
    rt_c = node_c + rt_max
    if post:
        return (go + rt_s + l['post_go_to_fin_const'] + l['post_go_to_fin_per_row'] * n + rgap * (n - 1)
                + r['fin_to_done']), None
    rd = rt_c + r['pre_sum_to_r']; lim = l['pre_r_return_max'] + l['kx'] * rgap
    if n > l['kx'] and rd > lim:
        return None, (f"HC_PRE/{n}: r round trip {rd} > x-slot limit {lim} at rgap {rgap} "
                      f"(lane FAULT; the compiler must raise rgap to >= {-(-(rd - l['pre_r_return_max']) // l['kx'])})")
    cs = l['pre_go_to_cs_last_const'] + (l['pre_row_ii'] + rgap) * (n - 1)
    return go + rt_c + cs + r['pre_sum_to_r'] + rt_s + l['pre_r_to_fin'] + r['fin_to_done'], None


def compile_calendar(jobs, bound, service, ready=None, schedule_rgap=False):
    missing = []
    legs = bound.get('legs', {}); rtl = bound.get('rtl', {})
    L = {}
    for k in LEGS:
        v = legs.get(k, {})
        if not isinstance(v.get('cycles'), int) or v['cycles'] < 0 or not v.get('source'):
            missing.append(f'bound leg {k}: cycles + source from the current bind/plan')
        else:
            L[k] = v['cycles']
    for k in RTL:
        v = rtl.get(k, {})
        if not isinstance(v.get('value'), int) or v['value'] < 0 or not v.get('source'):
            missing.append(f'rtl constant {k}: value + source')
        else:
            L[k] = v['value']
    spc = bound.get('source_plan_commit', '')
    if not re.fullmatch('[0-9a-f]{40}', spc or ''):
        missing.append('source_plan_commit: exact 40-hex plan commit')
    js = jobs.get('jobs', [])
    if not js:
        missing.append('no native FUSED jobs in the jobs receipt')
    if jobs.get('rejected'):
        missing.append('jobs receipt has rejected records')
    seg = (service or {}).get('schema') == SEG_SCHEMA
    svc = (service or {}).get('cycles', {})
    if not (service or {}).get('source'):
        missing.append('root service table source (measured component bench)')
    if seg and bound.get('legs_exclude_tree_nodes') is not True:
        missing.append('segments mode needs bound legs_exclude_tree_nodes: true (station/lane registers only)')
    for j in ([] if seg else js):
        key = f"{j['op']}/{j['fields']['nm1'] + 1}"
        if not isinstance(svc.get(key), int) or svc[key] <= 0:
            missing.append(f'root service cycles for {key}')
    missing = sorted(set(missing))
    if missing:
        return None, missing
    boot = {r: L['reset_release_edges'] + L['reset_' + r] + L['reset_sync_stages'] for r in ('SW', 'SE', 'NW', 'NE', 'root')}
    rt = {r: L['down_' + r] + L['up_' + r] for r in ('NW', 'NE')}
    tn = service['tnode'] if seg else None
    node_s, node_c = tnode_roundtrips(tn) if seg else (0, 0)
    wsc = max(rt.values()) + node_s + L['rr'] + 8
    pk5 = abs(rt['NW'] - rt['NE']); pb5 = int(rt['NE'] < rt['NW'])
    if wsc > 255: missing.append(f'wsc {wsc} > 255 (8-bit strap): the tree round trip does not fit')
    if pk5 > 32: missing.append(f'pk5 {pk5} > 32 (pad depth): NW/NE round trips differ by more than the t5 pad')
    n = len(js); iv = L['host_write_interval']
    if iv < 1: missing.append('host_write_interval must be >= 1 edge')
    host0 = max(boot.values())
    preload = host0 + (1 + 16 * n + 1) * iv + L['host_to_provider']
    commit = preload + (8 + 2) * iv
    start = max(commit + 1, max(boot.values()) + 6 + PAD_WARM)
    recs = []; prev = -1
    for j in sorted(js, key=lambda x: x['image_offset']):
        rdy = int((ready or {}).get(str(j['image_offset']), 0))
        launch = max(prev + 1, start + 3, rdy)
        cap = launch + 1 + L['provider_to_root']
        rgap = j['fields'].get('rgap', 0)
        original_rgap = rgap
        if schedule_rgap and seg and j['op'] != 'HC_POST' and j['fields']['nm1'] + 1 > service['lane']['kx']:
            # The lane retains KX rows until the root's r return. Raise spacing only;
            # addresses, arithmetic and row order stay byte-for-byte from the image.
            rd = node_c + max(rt.values()) + service['root']['pre_sum_to_r']
            needed = max(0, -(-(rd - service['lane']['pre_r_return_max']) // service['lane']['kx']))
            rgap = max(rgap, needed)
        if seg:
            sv, why = composed_service(service, j['op'], j['fields']['nm1'] + 1, rgap, wsc,
                                       max(rt.values()))
            if why:
                missing.append(why); continue
        else:
            sv = svc[f"{j['op']}/{j['fields']['nm1'] + 1}"]
        done = cap + sv
        dl = done + 2 + L['root_to_provider']
        recs.append(dict(image_offset=j['image_offset'], op=j['op'], ready_cycle=rdy, launch_cycle=launch,
                         root_capture_cycle=cap, root_done_cycle=done, completion_cycle=dl))
        if rgap != original_rgap:
            recs[-1]['rgap_override'] = dict(value=rgap, original=original_rgap, source_job217=j['job217'],
                                           reason='bound root return exceeds KX retained-row window',
                                           added_service_cycles=(rgap - original_rgap) * j['fields']['nm1'])
        prev = dl + 3
    if recs and recs[-1]['completion_cycle'] - start >= 1 << 32: missing.append('calendar exceeds 32-bit deadline')
    if missing:
        return None, missing
    cal = dict(schema='opentallas.hbm.four_role_fused_calendar.v1', source_plan_commit=spc,
               plan_sha256=bound.get('plan_sha256'), programme_image_sha256=jobs['image_sha256'], roles=dict(ROLES),
               boot_release_offsets=boot, root_config=dict(wsc=wsc, pk5=pk5, pb5=pb5),
               root_ingress_cycles=L['provider_to_root'], root_status_return_cycles=L['root_to_provider'],
               controller_fetch_cycles=FETCH, controller_start_cycles=START_EDGES, controller_status_check_cycles=STATUS,
               provider_start_cycle=start, provider_preload_complete_cycle=preload, provider_cfg_commit_cycle=commit,
               pad_warm_cycles=PAD_WARM, records=recs,
               start_authority=dict(f30_launch_cycle=start - 3, host_write_start_cycle=host0,
                                    rule='F30 only after all five delivered resets + 6 + pad warm and the cfg commit'),
               scope='LAYER_CALENDAR_READY' if ready else 'FUSED_ONLY_BACK_TO_BACK (no layer operand-ready edges)',
               derivation=dict(legs={k: L[k] for k in LEGS}, rtl={k: L[k] for k in RTL},
                               bound_sources={k: legs[k]['source'] for k in LEGS}, service_source=service['source']))
    if seg and 'external_face_shell' in tn:
        cal['derivation']['tnode_external_face_shell'] = dict(tn['external_face_shell'])
    return cal, []


def hub_tree_pads(plan, hubs=(('q_hub_nw', 'NW'), ('q_hub_ne', 'NE')), top='u_mu_fused_n4'):
    """Per-hub FUSED tree below t5 from the plan's internal mu_tree stations (1 edge per station register).
    Returns {role: {round_trip_regs, pads: {node: [k, pb]}}}: k aligns each node's children on down+up (one rule)."""
    out = {}
    for pt, role in hubs:
        up, dn, kids = {}, {}, {}
        for s in plan['partition_types'][pt]['internal_stations']:
            if not s['conn'].startswith('mu_tree:'):
                continue
            a, b = s['conn'].split(':', 1)[1].split('|'); inst, port = a.rsplit('.', 1); n = len(s['regs_um'])
            if port == 'uo':
                up[(inst, b)] = n
            else:
                dn[(b, inst)] = n; kids.setdefault(inst, {})[port] = b
        pads = {}

        def rt(x):
            if x not in kids:
                return 0
            ra, rb = (rt(kids[x][p]) + dn[(kids[x][p], x)] + up[(kids[x][p], x)] for p in ('da', 'db'))
            pads[x] = [abs(ra - rb), int(rb < ra)]
            return max(ra, rb)
        r = rt(top)
        out[role] = dict(round_trip_regs=r, pads=dict(sorted(pads.items())), legs=len(up) + len(dn))
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--jobs', type=Path, required=True); p.add_argument('--bound', type=Path, required=True)
    p.add_argument('--service', type=Path, required=True); p.add_argument('--ready', type=Path)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--schedule-rgap', action='store_true', help='raise PRE row spacing from bound KX return window; emitter needs --calendar-rgap')
    p.add_argument('--plan', type=Path, help='die_plan.json: also write <out>.hub_tree.json (per-node pad straps)')
    a = p.parse_args(argv)
    if a.plan:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        ht = hub_tree_pads(json.loads(a.plan.read_text()))
        a.out.with_suffix('.hub_tree.json').write_text(json.dumps(dict(
            plan_sha256=hashlib.sha256(a.plan.read_bytes()).hexdigest(), hubs=ht), indent=2) + '\n')
        print(json.dumps({r: v['round_trip_regs'] for r, v in ht.items()}))
    ld = lambda f: json.loads(f.read_text()) if f and f.exists() else {}
    cal, missing = compile_calendar(ld(a.jobs), ld(a.bound), ld(a.service), ld(a.ready) if a.ready else None, schedule_rgap=a.schedule_rgap)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    if missing:
        a.out.with_suffix('.MISSING.json').write_text(json.dumps(dict(status='MISSING', missing=missing), indent=2) + '\n')
        if a.out.exists(): a.out.unlink()
        print(json.dumps(dict(status='MISSING', n=len(missing), missing=missing[:12])))
        return 2
    a.out.write_text(json.dumps(cal, indent=2) + '\n')
    print(json.dumps(dict(status='CALENDAR', records=len(cal['records']), start=cal['provider_start_cycle'],
                          root_config=cal['root_config'], boot=cal['boot_release_offsets'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
