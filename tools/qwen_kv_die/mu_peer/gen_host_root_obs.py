#!/usr/bin/env python3
"""KV-BIND5-OBS 10-19: the HOST root with its observation window -- qkd_host_root_admission_obs, generated from the MU 1
release root rtl/qwen_sys/mu_qwen_20261018/qkd_host_root_admission_mu.sv (gen_host_root_mu.py; that file is UNCHANGED).

Why: bind v2 on the GEN9 die reports 43 HOST-root outputs OUTPUT_OPEN (class c: CSR / trace observations, admission
certificates, host fault / abort levels) plus dcal adm_done / cal_ready / running / layer and the D2D end's
recovery_cycles.  None has a die consumer by design: they are observations of the HOST.  The real reader is the HOST
itself, over the register path the host already uses (AXI4-Lite through the control packet engine, the ot_host_if
handshake): qkd_host_obs_csr sits on the AXI between the packet master (u_packet.u_axi) and the control CSR slave
(u_control) in qkd_host_control_packet_admission and serves window 0x1800-0x19FF of the CSR's free system region.
  * the 43 outputs leave the root's port list and become internal nets read by the window (their producers are
    unchanged: no tie, no stub, no deleted logic);
  * the five die observations enter as new root inputs obs_dcal_* / obs_d2d_recovery_cycles (die buses from dcal / d2d);
  * the fault-class subset (FLT) is also kept STICKY in the window (a 1-cycle abort / fault pulse stays visible until the
    host clears it); it already terminates inside the root (guard / CSR fault_src), the window adds the host view.
Static schedule: no die calendar edge, no STATUS edge, off every token path (the window is read by the host, a fixed
3 ck_csr edges per word after the AR handshake).  Hard-child impact: NONE of the host cluster's children change ports
(prompt = u_control, tx = u_packet.u_axi keep theirs); the window is one new cluster-level block on the u_axi <-> u_control
AXI wires (host lanes: qkd_hr_cluster glue / a new small hard child).

  gen_host_root_obs.py ROOT [--check]     writes / verifies rtl/qwen_sys/kv_host_obs_20261019/qkd_host_root_admission_obs.sv
  gen_host_root_obs.py ROOT --ext [--check]   the OBSX successor qkd_host_root_admission_obsx.sv (+ host_obs_map_x.json)

KV-FRAMEPINS 10-20 (--ext, die flag OT_KV_HOST_OBSX=1): the five die observations of EXT_PENDING (dcal adm_done /
cal_ready / running / layer, the D2D end's recovery_cycles = 41 b) enter the root as inputs obs_dcal_* /
obs_d2d_recovery_cycles and join the window snapshot above the 1,335 HOST bits (47 words, still inside 0x1900-0x19FF).
Their die buses are kv_oneway relayed buses dcal.dob / dcal.lay / d2d_kv.rcy -> host.odc / odl / odr (kv_static_die
OBSX).  Module names carry the suffix _obsx so the OBS (no-ext) file stays byte-identical for runs that bind it.
"""
import json
import re
import sys
from pathlib import Path

SRC_REL = 'rtl/qwen_sys/mu_qwen_20261018/qkd_host_root_admission_mu.sv'
OUT_REL = 'rtl/qwen_sys/kv_host_obs_20261019/qkd_host_root_admission_obs.sv'
MAP_REL = 'rtl/qwen_sys/kv_host_obs_20261019/host_obs_map.json'
OUTX_REL = 'rtl/qwen_sys/kv_host_obs_20261019/qkd_host_root_admission_obsx.sv'
MAPX_REL = 'rtl/qwen_sys/kv_host_obs_20261019/host_obs_map_x.json'
# bind v2 OUTPUT_OPEN qkd_host_root_admission (GEN9 kvs14r replay, KV-BIND3 pass2_fixed.json, whose per-master list is
# truncated at 40 names: the full set is 43 = + service_status / source_cr / sys_ready): observation outputs
OBS = ['host_admission_open', 'host_deferred', 'package_abort', 'native_pr', 'service_ready', 'service_abort',
       'ingest_permission', 'local_service_epoch', 'service_diag_raw', 'service_status', 'record_tx_v', 'record_fault',
       'program_authorized_footer_v', 'program_authorized_footer64', 'program_auth_v', 'program_expected_pw',
       'program_expected_dw', 'program_auth_epoch', 'program_auth_digest', 'hc', 'seen', 'irq', 'sys_ready',
       'fault_src', 'source_cr', 'available', 'marker_v', 'marker', 'issued', 'landed', 'physical_ack_n',
       'service_faults', 'peer_protocol_fault', 'dispatch_valid', 'dispatched', 'accepted_ranks', 'participant_trace',
       'participant_token', 'participant_pos', 'engine_result_cr', 'program_consensus', 'coordinator_fault',
       'recovery_complete']
# sticky fault-class subset (classification 'host fault/abort/health observation')
FLT = ['package_abort', 'service_abort', 'record_fault', 'peer_protocol_fault', 'coordinator_fault', 'irq', 'seen',
       'service_faults', 'fault_src']
# die observations that will enter the root as inputs (root port, die instance, RTL port, width).  NOT generated yet
# (EXT = [] below): the dcal / d2d die frames expose no pin group for these RTL outputs (bind v2 OUTPUT_OPEN because no
# frame group maps them), so each needs a frame group on its producer (closed bc4 / sfm2 view pins) + a HOST frame group;
# owners KV-DCAL2 (dcal) / KV-D2D (d2d) + KV-GEN9; then set EXT = EXT_PENDING (the window grows by 41 bits, 2 words).
EXT_PENDING = [('obs_dcal_adm_done', 'dcal', 'adm_done', 1), ('obs_dcal_cal_ready', 'dcal', 'cal_ready', 1),
       ('obs_dcal_running', 'dcal', 'running', 1), ('obs_dcal_layer', 'dcal', 'layer', 6),
       ('obs_d2d_recovery_cycles', 'd2d_kv', 'recovery_cycles', 32)]
EXT = []
# KV-FRAMEPINS 10-20: the die groups of the OBSX root (kv_die OT_KV_HOST_OBSX): host group -> root input ports
OBSX_HOST_GROUPS = dict(odc=['obs_dcal_adm_done', 'obs_dcal_cal_ready', 'obs_dcal_running'], odl=['obs_dcal_layer'],
                        odr=['obs_d2d_recovery_cycles'])
AXI_M2S = ['s_awvalid', 's_awaddr', 's_wvalid', 's_wdata', 's_wstrb', 's_bready', 's_arvalid', 's_araddr', 's_rready']
AXI_S2M = ['s_awready', 's_wready', 's_bvalid', 's_bresp', 's_arready', 's_rvalid', 's_rdata', 's_rresp']
AXI_W = dict(s_awaddr=13, s_wdata=32, s_wstrb=4, s_bresp=2, s_araddr=13, s_rdata=32, s_rresp=2)


def module_text(t, name):
    i = t.index(f'module {name} ')
    j = t.index('endmodule', i) + len('endmodule')
    return t[i:j]


def once(s, a, b):
    if s.count(a) != 1:
        raise SystemExit(f'gen_host_root_obs: edit anchor found {s.count(a)} x: {a[:80]!r}')
    return s.replace(a, b)


def split_header(m):
    """(prefix up to the port list '(', port text, rest starting at ');')"""
    k = m.index(')(') + 2           # '#( params )(' ports
    e = m.index('\n);', k)
    return m[:k], m[k:e], m[e:]


def parse_ports(txt):
    txt = re.sub(r'//[^\n]*', '', txt)
    out, cur = [], None
    for part in txt.split(','):
        p = part.strip()
        if not p:
            continue
        mm = re.match(r'(input|output|inout)\s+(wire|reg|logic)?\s*((?:\[[^\]]+\]\s*)?)(\w+)$', p, re.S)
        if mm:
            cur = (mm.group(1), (mm.group(3) or '').replace(' ', ''))
            out.append((cur[0], cur[1], mm.group(4)))
            continue
        mm = re.match(r'(\w+)$', p)
        if not mm or cur is None:
            raise SystemExit(f'gen_host_root_obs: cannot parse port {p!r}')
        out.append((cur[0], cur[1], mm.group(1)))
    return out


def width(rng):
    if not rng:
        return 1
    mm = re.match(r'\[(\d+):(\d+)\]', rng)
    return abs(int(mm.group(1)) - int(mm.group(2))) + 1 if mm else None     # parameter ranges: never an OBS port


def gen(root, ext=False):
    EXT = list(EXT_PENDING) if ext else []
    sfx = 'obsx' if ext else 'obs'
    t = (root / SRC_REL).read_text()
    head = ('`timescale 1ns/1ps\n// GENERATED by tools/qwen_kv_die/mu_peer/gen_host_root_obs.py (KV-BIND5-OBS 10-19'
            + (', --ext KV-FRAMEPINS 10-20' if ext else '') + ') from the '
            f'unchanged {SRC_REL}:\n// the MU 1 HOST root with the HOST observation window qkd_host_obs_csr (see the '
            'generator docstring).  Do not edit.\n')
    # ---- root: drop the observation outputs from the port list, add the die observation inputs
    rm = module_text(t, 'qkd_host_root_admission_mu')
    pre, ports_txt, rest = split_header(rm)
    ports = parse_ports(ports_txt)
    names = {n for _, _, n in ports}
    miss = [o for o in OBS if o not in names]
    if miss:
        raise SystemExit(f'gen_host_root_obs: root has no output {miss}')
    pw = {n: width(r) for d, r, n in ports}
    keep = [(d, r, n) for d, r, n in ports if n not in OBS]
    if any(d != 'output' for d, r, n in ports if n in OBS):
        raise SystemExit('gen_host_root_obs: an OBS name is not an output')
    decl = [f' {d} wire{r} {n}' for d, r, n in keep]
    decl += [f' input wire[{w - 1}:0] {n}' if w > 1 else f' input wire {n}' for n, _, _, w in EXT]
    nb = sum(pw[o] for o in OBS) + sum(w for *_, w in EXT)
    nf = sum(pw[o] for o in FLT)
    body_decl = ''.join(f'\n wire[{pw[o] - 1}:0] {o};' if pw[o] > 1 else f'\n wire {o};' for o in OBS)
    obs_cat = ','.join([n for n, *_ in reversed(EXT)] + list(reversed(OBS)))      # LSB = OBS[0]
    r_name = f'qkd_host_root_admission_{sfx}'
    flt_cat = ','.join(reversed(FLT))
    body_decl += (f'\n // KV-BIND5-OBS: the observation window bus (LSB first = host_obs_map.json order)\n'
                  f' localparam integer OBS_NB={nb},OBS_NF={nf};\n wire[OBS_NB-1:0] obs_bits={{{obs_cat}}};\n'
                  f' wire[OBS_NF-1:0] obs_flt={{{flt_cat}}};\n'
                  f' initial if(MU==0)$fatal(1,"{r_name}: the observation window exists in MU 1 only");')
    r2 = pre.replace('module qkd_host_root_admission_mu ', f'module {r_name} ') + '\n' + \
        ',\n'.join(decl) + rest
    r2 = once(r2, '\n);', '\n);' + body_decl)
    r2 = once(r2, 'qkd_host_rank_services_admission_mu #(.MU(1),',
              f'qkd_host_rank_services_admission_{sfx} #(.MU(1),.OBS_NB(OBS_NB),.OBS_NF(OBS_NF),')
    i = r2.index(f'qkd_host_rank_services_admission_{sfx} #(')
    j = r2.index(')u_rank(', i) + len(')u_rank(')
    r2 = r2[:j] + '.obs_bits(obs_bits),.obs_flt(obs_flt),' + r2[j:]
    # ---- rank services: thread obs_bits / obs_flt to the control packet admission
    rs = module_text(t, 'qkd_host_rank_services_admission_mu')
    rs = once(rs, 'module qkd_host_rank_services_admission_mu #(', f'module qkd_host_rank_services_admission_{sfx} #(parameter integer OBS_NB=1,OBS_NF=1,')
    p_, q_, s_ = split_header(rs)
    rs = p_ + q_.rstrip() + ',\n input wire[OBS_NB-1:0] obs_bits,\n input wire[OBS_NF-1:0] obs_flt' + s_
    rs = once(rs, '\n);', f'\n);\n initial if(MU==0)$fatal(1,"qkd_host_rank_services_admission_{sfx}: MU 1 only");')
    rs = once(rs, 'qkd_host_control_packet_admission_mu #(.MU(1),',
              f'qkd_host_control_packet_admission_{sfx} #(.MU(1),.OBS_NB(OBS_NB),.OBS_NF(OBS_NF),')
    i = rs.index(f'qkd_host_control_packet_admission_{sfx} #(')
    j = rs.index(')u_control(', i) + len(')u_control(')
    rs = rs[:j] + '.obs_bits(obs_bits),.obs_flt(obs_flt),' + rs[j:]
    # ---- control packet admission: the window on the u_packet (AXI master) <-> u_control (CSR slave) wires
    cp = module_text(t, 'qkd_host_control_packet_admission_mu')
    cp = once(cp, 'module qkd_host_control_packet_admission_mu #(', f'module qkd_host_control_packet_admission_{sfx} #(parameter integer OBS_NB=1,OBS_NF=1,')
    p_, q_, s_ = split_header(cp)
    cp = p_ + q_.rstrip() + ',\n input wire[OBS_NB-1:0] obs_bits,\n input wire[OBS_NF-1:0] obs_flt' + s_
    cp = once(cp, '\n);', f'\n);\n initial if(MU==0)$fatal(1,"qkd_host_control_packet_admission_{sfx}: MU 1 only");')
    if ext:
        # KV-P2-RTL 10-23 (owner: no tie-offs / open inputs): the HC broadcast station carries START only by design
        # (pr143 = PW/DW replays locally on fixed cycles on every rank; hc[181:39] bypasses the station, see the
        # assign below and results/rtl/kv_hostp_local_program_1023).  The source composition fed the station a
        # 143-bit constant {143'd0,raw_hc[38:0]}; OBSX instantiates the START-only station (HCW 39) on the 39 bits it
        # consumes.  KV-P3-RTL 10-23: the station's 39-bit command enters the START-only HC transport (u_packet HCW 39
        # -> u_ctrl qkd_host_ctrl_token_service_packet_collected_mu HCW 39, no PW/DW command field) as cmd_hc[38:0];
        # its 39-bit hc is the START slice of the composed hc (was {143'd0,cmd_hc} into the 182-bit transport).
        cp = once(cp, 'wire[181:0]raw_hc,cmd_hc;wire cmd_v,cmd_cr;',
                  'wire[181:0]raw_hc;wire[38:0]cmd_hc;wire cmd_v,cmd_cr;')
        cp = once(cp, 'qkd_host_hc_station #(.MUT(HC_MUT))u_hc(', 'qkd_host_hc_station #(.MUT(HC_MUT),.HCW(39))u_hc(')
        cp = once(cp, ".raw_hc({143'd0,raw_hc[38:0]})", '.raw_hc(raw_hc[38:0])')
        cp = once(cp, 'wire[181:0]transport_hc;', 'wire[38:0]transport_hc;')
        cp = once(cp, 'qkd_host_packet_bundle_admission_mu #(.MU(1),', 'qkd_host_packet_bundle_admission_mu #(.MU(1),.HCW(39),')
    g = cp.index('begin:g_mu')
    st = cp.index('qkd_host_packet_bundle_admission_mu #(', g)     # the u_packet statement
    k = cp.index(')u_packet(', st)
    e = cp.index('end endgenerate', k)
    inst = cp[k:e]
    for s in AXI_M2S + AXI_S2M:
        inst = once(inst, f'.{s}({s})', f'.{s}(u_{s})')
    wires = ''.join(f'wire [{AXI_W[s] - 1}:0] u_{s};\n' if s in AXI_W else f'wire  u_{s};\n' for s in AXI_M2S + AXI_S2M)
    conn = ','.join([f'.u_{s[2:]}(u_{s})' for s in AXI_M2S + AXI_S2M] + [f'.d_{s[2:]}({s})' for s in AXI_M2S + AXI_S2M])
    win = ('// KV-BIND5-OBS: HOST observation window between the packet AXI master and the CSR slave\n'
           'qkd_host_obs_csr #(.NB(OBS_NB),.NF(OBS_NF)) u_obs(.clk(ck_csr),.rst_n(host_rst_n),.obs(obs_bits),'
           f'.flt(obs_flt),{conn});\n')
    cp = cp[:st] + '// KV-BIND5-OBS: packet-side AXI (u_packet master -> u_obs)\n' + wires + cp[st:k] + inst + win + cp[e:]
    text = head + cp + '\n' + rs + '\n' + r2 + '\n'
    omap = []
    lo = 0
    for o in OBS:
        omap.append(dict(name=o, lsb=lo, width=pw[o]))
        lo += pw[o]
    for n, inst_, port, w in EXT:
        omap.append(dict(name=n, lsb=lo, width=w, die_source=f'{inst_}.{port}'))
        lo += w
    fmap, lo = [], nb
    for o in FLT:
        fmap.append(dict(name=o, lsb=lo, width=pw[o], sticky=True))
        lo += pw[o]
    m = dict(schema='opentallas.kv_host_obs_map.v1', window='0x1800-0x19FF (CSR system region)', NB=nb, NF=nf,
             words=(nb + nf + 31) // 32, word_base='0x1900', obs=omap, flt=fmap,
             ext=[dict(port=n, source=f'{i}.{p}', width=w) for n, i, p, w in EXT],
             ext_pending=[dict(port=n, source=f'{i}.{p}', width=w) for n, i, p, w in EXT_PENDING if not EXT])
    return text, json.dumps(m, indent=1) + '\n'


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith('-') else Path(__file__).resolve().parents[3]
    ext = '--ext' in sys.argv
    text, mp = gen(root, ext)
    out, mo = (root / OUTX_REL, root / MAPX_REL) if ext else (root / OUT_REL, root / MAP_REL)
    if '--check' in sys.argv:
        ok = out.exists() and out.read_text() == text and mo.exists() and mo.read_text() == mp
        print('gen_host_root_obs: ' + ('UP TO DATE' if ok else 'STALE'))
        sys.exit(0 if ok else 1)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
    mo.write_text(mp)
    print(f'gen_host_root_obs: wrote {out.relative_to(root)} ({json.loads(mp)["NB"]} obs + {json.loads(mp)["NF"]} sticky bits, '
          f'{json.loads(mp)["words"]} words)')


if __name__ == '__main__':
    main()
