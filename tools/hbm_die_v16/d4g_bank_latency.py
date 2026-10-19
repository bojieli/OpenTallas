#!/usr/bin/env python3
"""HBM-BANKLAT 10-19: LATENCY class of the d4g functional bind -- every fixed-latency VM bank client's round-trip
parameter must equal the bank contract plus the die lanes on its path (coordinator decision on the VEH-TOPKFIX2 audit
results/rtl/hbm_ds_layer_tput_1018/veh_cuts_1019/topkfix/vm_client_audit.json: per-client LATENCY PARAMETERS + a bind
check; the bank tile is NOT changed).

BANK CONTRACT (edges at the bank's own ports, rq/wq launched on edge n by the producer's last flop):
  read  rq<k> -> rr<k>, pq -> pr               BANK_RD 6  (ot_vms_bank_static n+6)
  write wq<k> -> wq_done<k>, dq/kq/xq/xq2 -> *_done   BANK_WR 3  (commit n+3)
  + PIN 1 when the bank master registers every input pin (hfd_vms_bank_native_q0_faces, ot_pin_regs.tcl), else 0.
LANE LATENCY (die edges added between a client port and the bank port, per direction, per bank):
  hbfd_rly_*  registered station                      +1
  forwarded lane ending in a landing (hbfd_lh0/lh hops + hbfd_land/land0): ceil(N/2) + 1 + E   (d4g_land_plan.py L4,
              N = the landing's station count from its note, E = (K - ceil(N/2)) mod 8 in 1..8 from the K straps the
              die binds -> the latency the netlist will actually have; 'NO_E placeholder' K is reported as such)
REQUIRED ROUND TRIP of a client on bank b:  RT_b = BANK + PIN + lane(rq) + lane(rr).
  SCALAR param (one round trip for the client):
  (1) EQUAL: RT_b must be the same for every bank it reads (the die pads the short lanes: padding per lane reported);
  (2) PARAM: param == ref + (max_b RT_b - ref_rt), ref/ref_rt = the value the RTL header states and the round trip it
      was designed for (rule table RULES below; a param absent from the contract takes the RTL default).
  PER-BANK VECTOR param (contract params value is a list, element b = bank index b = the bank instance's last digit;
  the client captures each bank's answer on its own edge, so no lane padding is needed -- cheaper than padding wide
  data lanes when the spread is large): element b == ref + (RT_b - ref_rt) for every bank b.
Clients behind a SHARE (a request mux in front of a bank group) are checked through the share: the share's own rule
gives its excess over its reference, and the downstream client adds that excess plus its own lanes to the share.
Clients without a fixed capture (fire-and-forget writers) and hub/calendar ports are listed as INFO, not checked.

    d4g_bank_latency.py CONTRACT.json[.gz] [--report R.json]      (standalone; d4g_functional_bind.py imports check())
Output line: BANK_LATENCY PASS|FAIL clients=N checked=C fail=F unequal=U unresolved_landings=L
"""
import argparse, collections, gzip, json, math, re, sys
from pathlib import Path

BANK_PIN = {'hfd_vms_bank_native_q0_faces': 1, 'ot_vms_bank_static': 0, 'hfd_vms_bank_native_q0': 0}
BANK_RD, BANK_WR = 6, 3
READ = {f'rq{k}': f'rr{k}' for k in range(5)}
READ['pq'] = 'pr'
WRITE = {'wq0': 'wq_done0', 'wq1': 'wq_done1', 'dq': 'dq_done', 'kq': 'kq_done', 'xq': 'xq_done', 'xq2': 'xq2_done'}
RELAY = re.compile(r'^hbfd_(rly|lh0?|lnd|land0?)[A-Za-z0-9_]*$')
THRU = {'o': 'i', 'b': 'a'}
FWD = {'i': 'o', 'a': 'b'}

# master -> list of (client request port, kind, param, RTL default, ref value, ref round trip, why)
#   kind rd/wr = direct bank client; 'share' = a request mux whose own param is checked like a client and whose
#   downstream clients (SHARE_PORTS) inherit its excess.
RULES = {
    'ot_hbm_su_static_pgslice_lg': [
        ('lg_rq', 'rd', 'READ_RETURN', 10, 10, BANK_RD, 'ot_hbm_vm_lg_static_bank: near SU 10 = 4 own + bank read 6'),
        ('lg_wq', 'wr', 'WRITE_RETURN', 7, 7, BANK_WR, 'near SU 7 = 4 own + bank commit 3')],
    'ot_hgi_sm_xload_cl2_ctlx': [
        ('rq', 'rd', 'RD_LAT', 6, 6, BANK_RD, 'RD_LAT 6 = ot_vms_bank_static rq->rr n+6, zero die stages; list = per-bank vector '
         '(HBM-BANKLAT-XL: element b = registers rq pin -> bank b -> rr pin; ctl staggers bank b issue by max - l_b)')],
    'ot_hgi_sm_xload_cl2p_ctlx': [
        ('rq', 'rd', 'RD_LAT', 6, 6, BANK_RD, 'cl2p (x_fmt 3) ctlx: same RD_LAT contract as cl2 ctlx; SCALAR only until its '
         'ctl gets the cl2 per-bank stagger')],
    'ot_hbm_idx_vm_query_static_n12': [
        ('vm_rq', 'rd', 'VM_RT_EXTRA', 4, 4, BANK_RD + 2, 'header: VM_RT_EXTRA 4 = 2 shell pins + 2 die edges (1 relay each way)')],
    'ot_hbm_idx_rootctl_static_am': [
        ('vm_rq', 'share', 'VM_RT', 0, 0, BANK_RD, 'rootctl_am VM_RT = edges beyond ot_vms_bank_static n+6 (VEH-TOPKFIX2)')],
    'ot_hbm_idx_rootctl_static_am_pin': [
        ('vm_rq', 'share', 'VM_RT', 1, 0, BANK_RD, 'am_pin = am #(VM_RT 1) for the faces bank pin flop')],
    'ot_hbm_idx_vm_share2_static': [
        ('vm_rq', 'share', 'BANK_RT', 6, 6, BANK_RD, 'REG 0 owner own[BANK_RT]: bank answer at n+1+BANK_RT (own[6] = n+6 bank)')],
    'ot_hbm_idx_vm_share2_static_r': [
        ('vm_rq', 'share', 'BANK_RT', 6, 6, BANK_RD, 'REG 1 (pin-registered leaf): same owner rule behind its own pins')],
    'ot_hgi_dma_back_static_vp4_banks_cp': [
        ('rq', 'rd', 'DRAIN_RT', None, None, BANK_RD, 'drain_rel32 comes from the descriptor (compiler-owned): reported, owner confirms')],
}
# masters whose RTL accepts a per-bank VECTOR (contract list) for the rule's param; a list on any other master FAILS
VECTOR_OK = {('ot_hgi_sm_xload_cl2_ctlx', 'RD_LAT')}
# downstream clients of a share: (share master, share request port) -> (client param, RTL default, ref value, ref lanes, why)
SHARE_PORTS = {
    # n12 VM_RT_EXTRA 4 = 2 shell pins + the registered share's 2 pin flops (index_rq pin, vm_rr leaf pin; n12 header), so
    # its reference has NO die lane to the share (ref lanes 0; HBM-BANKLAT-IDX 10-19: was 2, which under-counted by 2 and
    # disagreed with VEH-TOPKFIX2's n13 at VM_RT 1).
    ('ot_hbm_idx_rootctl_static_am', 'index_rq'): ('VM_RT_EXTRA', 4, 4, 0, 'n12 SW behind the registered share: its 2 pins'),
    ('ot_hbm_idx_rootctl_static_am_pin', 'index_rq'): ('VM_RT_EXTRA', 4, 4, 0, 'n12 SW behind the registered share'),
    ('ot_hbm_idx_rootctl_static_am', 'argmax_rq'): ('VMX', 5, 5, 0, 'argmax r2 VMX 5 behind rootctl_am (argmax_m)'),
    ('ot_hbm_idx_rootctl_static_am_pin', 'argmax_rq'): ('VMX', 5, 5, 0, 'argmax r2 VMX behind rootctl_am_pin'),
    ('ot_hbm_idx_vm_share2_static', 'a_rq'): ('VM_RT', 0, 0, 0, 'face A of a share2 captures n+8 (+VM_RT)'),
    ('ot_hbm_idx_vm_share2_static', 'b_rq'): ('VM_RT', 0, 0, 0, 'face B of a share2 captures n+8 (+VM_RT)'),
    ('ot_hbm_idx_vm_share2_static_r', 'a_rq'): ('VM_RT', 0, 0, 0, 'face A of a share2_r captures n+10 (+VM_RT)'),
    ('ot_hbm_idx_vm_share2_static_r', 'b_rq'): ('VM_RT', 0, 0, 0, 'face B of a share2_r captures n+10 (+VM_RT)'),
}
# per-master overrides of the downstream param name (the n12 reader keeps VM_RT_EXTRA behind a share2 too: the
# combinational share2 face adds no edge, so its 2 reference die edges count as ref lanes). Applied only where the share
# port's own entry names a different param (a share port written for that client keeps its own reference).
DOWN_PARAM = {'ot_hbm_idx_vm_query_static_n12': ('VM_RT_EXTRA', 4, 4, 2)}
INFO_MASTERS = re.compile(r'^(hfd_hgi_vms|hfd_hgi_vm_calendar|hfd_vms_wq2_merge|ot_hbm_svc_vmdel|ot_hgi_coll_kq_share2|'
                          r'ot_hbm_sm_vm_wr_q)')


def load(f):
    return json.load(gzip.open(f, 'rt') if str(f).endswith('.gz') else open(f))


class Graph:
    def __init__(self, c):
        self.I = c['instances']
        self.drv = {}
        self.sinks = collections.defaultdict(list)
        for e in c['edges']:
            si, sp, slo, shi = e['source']; ki, kp, klo, khi = e['sink']
            for b in range(khi - klo):
                self.drv[(ki, kp, klo + b)] = (si, sp, slo + b)
                self.sinks[(si, sp, slo + b)].append((ki, kp, klo + b))

    def m(self, i):
        return self.I.get(i, {}).get('master', '')

    def back(self, i, p, b):
        """walk a consumer bit back to its producer through lane hops; hops listed source -> sink."""
        hops = []
        while True:
            d = self.drv.get((i, p, b))
            if d is None:
                return None, hops
            si, sp, sb = d
            if RELAY.match(self.m(si)) and sp in THRU:
                hops.append(si); i, p, b = si, THRU[sp], sb; continue
            return d, hops[::-1]

    def fwd(self, i, p, b):
        out, stack = [], [(i, p, b, [])]
        while stack:
            i, p, b, hops = stack.pop()
            for ki, kp, kb in self.sinks.get((i, p, b), []):
                if RELAY.match(self.m(ki)) and kp in FWD:
                    stack.append((ki, FWD[kp], kb, hops + [ki]))
                else:
                    out.append(((ki, kp, kb), hops))
        return out

    def lane_latency(self, hops):
        """edges added by the hops (source -> sink order); returns (latency, notes)."""
        lat, half, notes = 0, 0, []
        for h in hops:
            m = self.m(h)
            if m.startswith('hbfd_rly'):
                lat += 1
            elif re.match(r'^hbfd_lh0?_', m):
                half += 1
            elif re.match(r'^hbfd_(land0?|lnd)_', m):
                note = self.I[h].get('note', '')
                mk = re.search(r'\bK (\d+)', note); mn = re.search(r'\bN (\d+)', note)
                n = int(mn.group(1)) if mn else half
                if mk is None:
                    notes.append(f'{h}: landing without K'); lat += math.ceil(n / 2) + 1 + 1
                else:
                    e = (int(mk.group(1)) - math.ceil(n / 2)) % 8 or 8
                    lat += math.ceil(n / 2) + 1 + e
                    if 'NO_E' in note:
                        notes.append(f'{h}: K {mk.group(1)} NO_E placeholder (E {e} derived from K)')
                half = 0
        if half:
            notes.append(f'{half} half-cycle hops without a landing')
            lat += math.ceil(half / 2)
        return lat, notes


def param(I, inst, name, dflt):
    v = I[inst].get('params', {}).get(name)
    return dflt if v is None else int(v)


def check(c):
    """returns (rows, summary).  rows: one per (client inst, request port, kind)."""
    G = Graph(c); I = G.I
    banks = sorted(k for k, v in I.items() if v['master'] in BANK_PIN)
    paths = collections.defaultdict(list)    # (client, port, kind) -> [(bank, rt, lane_rq, lane_rr, notes)]
    for bk in banks:
        pin = BANK_PIN[I[bk]['master']]
        for rq, rr in list(READ.items()) + list(WRITE.items()):
            if rq not in I[bk]['ports']:
                continue
            d, hq = G.back(bk, rq, 0)
            if d is None:
                continue
            kind = 'rd' if rq in READ else 'wr'
            lq, nq = G.lane_latency(hq)
            ret = [(s, h) for s, h in G.fwd(bk, rr, 0) if s[0] == d[0]] if rr in I[bk]['ports'] else []
            if ret:
                lr, nr = G.lane_latency(ret[0][1]); rport = ret[0][0][1]
            else:
                lr, nr, rport = None, [], None
            base = (BANK_RD if kind == 'rd' else BANK_WR) + pin
            paths[(d[0], d[1], kind)].append(dict(bank=bk, bank_port=rq, ret_port=rport, lane_rq=lq, lane_rr=lr,
                                                  rt=None if lr is None else base + lq + lr, pin=pin, notes=nq + nr))
    rows = []
    excess = {}                                  # share inst -> its actual RT excess over ref_rt
    for (ci, cp, kind), ps in sorted(paths.items()):
        m = I[ci]['master']
        rule = next((r for r in RULES.get(m, []) if r[0] == cp and (r[1] == kind or r[1] == 'share')), None)
        rts = sorted({p['rt'] for p in ps if p['rt'] is not None})
        row = dict(client=ci, master=m, port=cp, kind=kind, banks=len(ps), rt=rts,
                   unresolved=sorted({n for p in ps for n in p['notes'] if 'NO_E' in n})[:4],
                   paths=ps, status='INFO', bad=[])
        if rule is None:
            row['why'] = 'fire-and-forget / hub port (not a fixed-capture client)' if INFO_MASTERS.match(m) else \
                'no LATENCY rule for this master'
            if not INFO_MASTERS.match(m) and rts:
                row['status'] = 'FAIL'; row['bad'].append(f'{m}.{cp}: fixed-latency client without a LATENCY rule')
            rows.append(row); continue
        _, _, pname, dflt, ref, ref_rt, why = rule
        row.update(param=pname, why=why)
        if not rts:
            row['status'] = 'FAIL'; row['bad'].append('no return path traced'); rows.append(row); continue
        need = max(rts)
        vec = I[ci].get('params', {}).get(pname)
        if isinstance(vec, list) and (m, pname) not in VECTOR_OK:
            row.update(have=vec, status='FAIL')
            row['bad'].append(f'{ci}.{pname} is a list but {m} has no per-bank vector form (VECTOR_OK)')
            rows.append(row); continue
        if isinstance(vec, list) and ref is not None:
            row.update(have=vec, want=[None] * len(vec))
            for p in ps:
                bi = int(re.sub(r'\D', '', p['bank'][-1]) or 0)
                w = ref + p['rt'] - ref_rt
                if bi < len(vec):
                    row['want'][bi] = w
                if bi >= len(vec) or int(vec[bi]) != w:
                    pad = (f' (budget above the lanes: die pads the {p["bank"]}:{p["bank_port"]} lane +{int(vec[bi]) - w})'
                           if bi < len(vec) and int(vec[bi]) > w else '')
                    row['bad'].append(f'{ci}.{pname}[{bi}] = {vec[bi] if bi < len(vec) else None}, bank {p["bank"]} needs {w}{pad}')
                    if pad:
                        row.setdefault('lane_pads', []).append(f'{p["bank"]}:{p["bank_port"]}+{int(vec[bi]) - w}')
            if rule[1] == 'share':
                excess[ci] = need - ref_rt
            row['status'] = 'FAIL' if row['bad'] else 'PASS'
            rows.append(row); continue
        if len(rts) > 1:
            row['bad'].append(f'unequal round trip across banks {rts}: pad lanes to {need} '
                              f'({", ".join(sorted({p["bank"] + "+" + str(need - p["rt"]) for p in ps if p["rt"] != need}))})')
        if rule[1] == 'share':
            excess[ci] = need - ref_rt
        if ref is None:
            row['status'] = 'INFO'; row['need_rt'] = need; row['why'] += f' (round trip {rts})'
            rows.append(row); continue
        have = param(I, ci, pname, dflt)
        want = ref + need - ref_rt
        row.update(have=have, want=want)
        if have != want:
            if isinstance(have, int) and have > want:
                row['pad_to_param'] = f'die pads every bank lane of {ci} +{have - want} (param budget {have} > lanes {want})'
            row['bad'].append(f'{ci}.{pname} = {have}, bank contract + lanes need {want} '
                              f'(ref {ref} at round trip {ref_rt}; actual {need} = bank {BANK_RD if kind == "rd" else BANK_WR}'
                              f' + pin {ps[0]["pin"]} + lanes)')
        row['status'] = 'FAIL' if row['bad'] else 'PASS'
        rows.append(row)
    # downstream clients of shares
    for si, ex in sorted(excess.items()):
        sm = I[si]['master']
        for (smm, sport), (pname, dflt, ref, ref_lanes, why) in SHARE_PORTS.items():
            if smm != sm or sport not in I[si]['ports']:
                continue
            d, hq = G.back(si, sport, 0)
            if d is None:
                continue
            ci, cp = d[0], d[1]
            cm = I[ci]['master']
            if cm in DOWN_PARAM and DOWN_PARAM[cm][0] != pname:
                pname, dflt, ref, ref_lanes = DOWN_PARAM[cm]
            lq, nq = G.lane_latency(hq)
            rport = {'index_rq': 'index_rr', 'argmax_rq': 'argmax_m', 'a_rq': 'a_rr', 'b_rq': 'b_rr'}[sport]
            ret = [(s, h) for s, h in G.fwd(si, rport, 0) if s[0] == ci]
            lr, nr = G.lane_latency(ret[0][1]) if ret else (None, [])
            row = dict(client=ci, master=cm, port=cp, kind='rd_via_share', share=si, banks=0, param=pname, why=why,
                       unresolved=sorted({n for n in nq + nr if 'NO_E' in n})[:4], status='PASS', bad=[])
            if lr is None:
                row['status'] = 'FAIL'; row['bad'].append(f'no return path {si}.{rport} -> {ci}'); rows.append(row); continue
            have = param(I, ci, pname, dflt)
            want = ref + ex + (lq + lr - ref_lanes)
            row.update(have=have, want=want, lanes=lq + lr, share_excess=ex)
            if have != want:
                row['status'] = 'FAIL'
                if isinstance(have, int) and have > want:
                    row['pad_to_param'] = f'die pads the {ci} <-> {si} lanes +{have - want} (param budget {have})'
                row['bad'].append(f'{ci}.{pname} = {have}, need {want} (ref {ref} + share {si} excess {ex} + lanes '
                                  f'{lq}+{lr} - ref lanes {ref_lanes})')
            rows.append(row)
    fails = [r for r in rows if r['status'] == 'FAIL']
    summ = dict(clients=len(rows), checked=sum(r['status'] in ('PASS', 'FAIL') for r in rows), fail=len(fails),
                unequal=sum(any(b.startswith('unequal') for b in r['bad']) for r in rows),
                unresolved_landings=sum(bool(r['unresolved']) for r in rows))
    return rows, summ


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('contract'); ap.add_argument('--report')
    a = ap.parse_args()
    rows, s = check(load(a.contract))
    for r in rows:
        if r['status'] == 'INFO':
            continue
        tag = f'{r["client"]}.{r["port"]} {r["kind"]}'
        print(f'  {r["status"]:4s} {tag:34s} {r.get("param", "-")}={r.get("have")} want {r.get("want")} rt {r.get("rt", r.get("lanes"))}'
              + ('' if r['status'] == 'PASS' else ' | ' + '; '.join(r['bad'])[:400]))
    ok = s['fail'] == 0
    print(f'BANK_LATENCY {"PASS" if ok else "FAIL"} clients={s["clients"]} checked={s["checked"]} fail={s["fail"]} '
          f'unequal={s["unequal"]} unresolved_landings={s["unresolved_landings"]}')
    if a.report:
        Path(a.report).write_text(json.dumps(dict(schema='opentallas.d4g_bank_latency.v1', contract=str(a.contract),
                                                  verdict='PASS' if ok else 'FAIL', summary=s, rows=rows), indent=1))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
