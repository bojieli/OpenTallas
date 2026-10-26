#!/usr/bin/env python3
"""Opt-in actual-source v1.5 composition. Incomplete compiler joins fail closed.

A compiler join has exact instances, parameters, source hashes and input-port
connections. Connections name an actual output port, a permitted off-die port,
or a declared physical identity strap. This module never writes black boxes,
port aliases, implicit parameters, zero-filled operands, or reference results.
Physical adoption is separate and is deliberately unavailable here.
"""
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import kv_qkh_safe32 as QKH32

from kv_elastic_boundary import _source, WRITER_LINK_MAP, WRITER_PROGRAMME_MAP
from static_pc_path_sources import SOURCES as PC_SOURCES
ROOT = Path(__file__).resolve().parents[2]


def d2d_txdp_k():
    """QLB-KV 10-18 (QXF-LINK 6ef1a097f F4): qkd_d2d_static TXDP is a REQUIRED parameter (no default; a zero byte does not
    elaborate).  The KV die's vector = D2D_TXDP_K of the committed calendar image; OT_KV_D2D_TXDP_K=0x... overrides it with the
    vector layer_compile.py derives for THIS die (kv_relay_check.sh gates bound == compiled)."""
    import os
    ov = os.environ.get('OT_KV_D2D_TXDP_K')
    if ov:
        v = int(ov, 0)
    else:
        img = 'rtl/qwen_sys/d2d_static_20261015/d2d_cal_image.svh'
        mm = re.search(r"localparam\s*\[31:0\]\s*D2D_TXDP_K\s*=\s*32'h([0-9a-fA-F_]+)\s*;", (ROOT / img).read_text())
        if not mm:
            raise SystemExit(f'kv_static: D2D_TXDP_K not found in {img} (QXF-LINK: TXDP is required, no default)')
        v = int(mm.group(1).replace('_', ''), 16)
    if any(((v >> (8 * k)) & 0xff) == 0 for k in range(4)):
        raise SystemExit(f'kv_static: D2D_TXDP_K {v:#010x} has a zero port byte (D2D_TXDP_NOT_COMPILED)')
    return v


def d2d_ntx_k():
    """KV-PLAN5 10-18: qkd_d2d_static KV-die TX lane count (S-QTIES QC-12, RTL parameter NTX).  3 = the dead port-3 TX lane
    removed, the CLOSED view qkd_d2d_static_r7t-r7t-28642e9aa (TT +22.73 / FF +10.31) is built at NTX = 3; OT_KV_D2D_NTX
    overrides (4 = the r7q port-3-tied-idle build)."""
    import os
    n = int(os.environ.get('OT_KV_D2D_NTX', '3'))
    if n not in (3, 4):
        raise SystemExit(f'kv_static: OT_KV_D2D_NTX={n} (qkd_d2d_static builds 3 or 4 TX lanes)')
    return n


S = 'rtl/qwen_sys/static_kv_20261014/'
E = 'rtl/qwen_sys/static_embedding_20261014/'
# KVJ-C2 2026-10-17: the per-PC parent is the embedding successor qkd_static_kv_pc_path_emb (unchanged pc_path + the
# es merge child qkd_static_kv_pc_es_merge); its extra RTL dependencies
PC_EMB_EXTRA = [E + 'qkd_embedding_static_map.sv', E + 'qkd_static_kv_pc_es_merge.sv', E + 'qkd_static_kv_pc_path_emb.sv',
                # KVJ-C3 2026-10-17: the per-PC parent successor qkd_static_kv_pc_path_fan adds the chain station
                E + 'qkd_kv_pc_chain_station.sv',
                # KV-PLAN-CI 2026-10-17 (coordinator decision 3): the ci-less successors (no legacy controller word ci on
                # the static die; lockstep-equal to the originals with ci idle, tools/qwen_kv_die/kvplan_ci_nc_gate.sh)
                S + 'qkd_ctrl_pc_nc.sv', S + 'qkd_static_kv_pc_path_nc.sv', E + 'qkd_static_kv_pc_path_fan_nc.sv']


def pc_emb_sources():
    return list(PC_SOURCES) + (PC_EMB_EXTRA if ROLES.get('pc_path', ('',))[0].startswith(E) else [])
# the embedding token path's RTL dependencies beyond the instance sources (join4 instantiates the unchanged join)
EMB_SOURCES = [E + 'qkd_embedding_static_join.sv', E + 'qkd_embedding_static_join4.sv']   # join4_cal -> join4 -> join
STACK_NAMES = ('WS', 'WN', 'ES', 'EN')
# Name, actual source/module, exact required full-die population. The pc parent
# elaborates into four real masters; it is not an inherited physical frame.
ROLES = {
    'phase_launch': (S+'qkd_static_kv_phase_launch.sv', 'qkd_static_kv_phase_launch', 32),
    'layer_programme': (S+'qkd_static_kv_layer_programme.sv', 'qkd_static_kv_layer_programme', 1),
    'attention_programme': ('rtl/qwen_sys/split_20261014/qkd_native_attention_programme.sv', 'qkd_native_attention_programme', 1),
    'ownership': (S+'qkd_static_kv_ownership.sv', 'qkd_static_kv_ownership_calendar', 1),
    'drain_guard': (S+'qkd_static_kv_ownership.sv', 'qkd_static_kv_drain_guard4', 32),
    # KVJ-C3 2026-10-17: pc_path_emb + the static PC chain station (writer lane -> PC fan-out tap, embedding slot player)
    # KV-PLAN-CI 2026-10-17: ... without the legacy controller word ci (qkd_static_kv_pc_path_fan minus ci)
    'pc_path': (E+'qkd_static_kv_pc_path_fan_nc.sv', 'qkd_static_kv_pc_path_fan_nc', 128),
    'landing': (S+'qkd_static_kv_landing_seg.sv', 'qkd_static_kv_landing_seg', 32),
    'landing_calendar': (S+'qkd_kv_landing_cal.sv', 'qkd_kv_landing_cal', 32),
    'front_calendar': (S+'qkd_kv_front_cal.sv', 'qkd_kv_front_cal', 32),
    'k_issuer': (S+'qkd_static_k_issuer.sv', 'qkd_static_k_issuer', 32),
    'vport': (S+'qkd_pv16_vport.sv', 'qkd_pv16_vport', 16),
    'ectla': ('rtl/qwen_sys/split_20261014/qkd_ectl_a_tp8_epoch_direct.sv', 'qkd_ectl_a_tp8_epoch_direct', 32),
    'writer': ('rtl/physical/ot_qkd_kv_static_writer_native.sv', 'qkd_kv_static_writer_native', 1),
    'writer_programme': (S+'qkd_kv_native_programme.sv', 'qkd_kv_native_programme', 1),
    'link': ('rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv', 'qkd_d2d_static', 1),
    # KVJ-C2 2026-10-17 (D2): boot-only embedding gateway, the 4 per-stack return trains (head + 31 hops each), the
    # 4-train join and the embedding row transmitter beside the d2d KV end
    'embgw': (E+'qkd_embgw_boot.sv', 'qkd_embgw_boot', 1),
    'emb_return_head': (E+'qkd_embedding_static_return_head.sv', 'qkd_embedding_static_return_head', 4),
    'emb_return_hop': (E+'qkd_embedding_static_return_hop.sv', 'qkd_embedding_static_return_hop', 124),
    # KVJ-C3: join4 + its compiled beat_slot calendar (qkd_embedding_static_join4_cal)
    'emb_join': (E+'qkd_embedding_static_join4_cal.sv', 'qkd_embedding_static_join4_cal', 1),
    'row_tx': (E+'qkd_embedding_row_tx.sv', 'qkd_embedding_row_tx', 1),
    # KVJ-C3 2026-10-17: root of the four per-stack static PC chains, beside the writer and the d2d KV end
    'es_fan_root': (S+'qkd_kv_es_fan_root.sv', 'qkd_kv_es_fan_root', 1),
}
# MU-ADOPT-KV 10-19 (Qwen ROM 4 users, R6; OT_KV_MU=1, default off: every existing design point is unchanged): the per-user
# KV row 64 + layer + 256*user (user = the stage's TAG epoch[1:0]).  Write side: the writer role binds the drop-in wrapper
# qkd_kv_static_writer_native_mu (closed writer + qkd_kv_mu_wrow, glue of the RTL-only parent kvs_ctl); read side: every
# pc_path gets MU=1 (the inline qkd_kv_mu_rrow map in qkd_static_kv_pc_path_nc).  Tile file suffix '_mu'.
MU = __import__('os').environ.get('OT_KV_MU', '0') == '1'
MU_DEPS = ['rtl/physical/ot_qkd_kv_static_writer_native.sv', 'rtl/qwen_sys/mu_qwen_20261018/qkd_kv_mu_rowoff.sv',
           # MU-KV-BOOT 10-19: the multi-context layer programme / boot dispatcher wrappers instantiate the originals
           S + 'qkd_static_kv_layer_programme.sv', S + 'qkd_static_kv_boot_dispatch.sv']
if MU:
    ROLES['writer'] = ('rtl/qwen_sys/mu_qwen_20261018/qkd_kv_static_writer_native_mu.sv', 'qkd_kv_static_writer_native_mu', 1)
    # MU-KV-BOOT 10-19 (hroot README section 3): 4 token contexts (user = authority_epoch[1:0]) on the one boot-loaded
    # stage table + the compiled GAP[4][36] block (boot image MU form, kv_static_boot_join.BOOT_MU dispatcher)
    ROLES['layer_programme'] = ('rtl/qwen_sys/mu_qwen_20261018/qkd_static_kv_layer_programme_mu.sv',
                                'qkd_static_kv_layer_programme_mu', 1)
    # MU-KV-PROG 10-19: the ownership calendar is the one lprg consumer in qkd_kvs_ctl with per-TOKEN state (a go while its
    # window is active faults); its _mu successor re-arms the window per user token start (results/rtl/mu_qwen_1018/kvprog)
    ROLES['ownership'] = ('rtl/qwen_sys/mu_qwen_20261018/qkd_static_kv_ownership_calendar_mu.sv', 'qkd_static_kv_ownership_calendar_mu', 1)
    MU_DEPS.append(S + 'qkd_static_kv_ownership.sv')
# return-train beat record (qkd_embedding_static_return_head / _hop capture_record, unpacked by join4), MSB first
EMB_RECORD = (('emb_beat_epoch', 16), ('emb_beat_scale', 1), ('emb_beat_half', 1), ('emb_beat_word', 6),
              ('emb_beat_token', 18), ('emb_beat_data', 256))
# TAG59 = {epoch16, stage6, token18, position13, segment6}: the request epoch of the RESULT
TAG59_EPOCH_LO = 43
IDENT = re.compile(r'^[A-Za-z_]\w*$')
# Clock entries of the per-PC wires-only parent qkd_static_kv_pc_path (lead 2026-10-16 option A): every hard child
# clock pin has its own parent port, and the die clock tree delivers each one as a SEPARATE entry (phi - R_i, R_i =
# entry wire + that child's routed insertion), never a tie to a shared net inside the parent.  pll_hbm / pll_hbm_port /
# pll_hbm_ecc are the hardened controller cluster's core / port / ECC HBM entries (same HBM clock, three entries).
PC_PATH_CLOCK_ENTRIES = {'pll_hbm': 'hbm', 'pll_hbm_port': 'hbm', 'pll_hbm_ecc': 'hbm', 'pll_hbm_cdc': 'hbm', 'pll_hbm_obs': 'hbm', 'cal_hck': 'hbm',
                         'front_hck': 'hbm', 'return_hck': 'hbm', 'ck': 'core', 'return_ck': 'core'}


def pc_path_clock_entries(ins, specs, tops):
    """One die clock-tree entry per pc_path clock port, each fed by a whole external clock (fail closed)."""
    out = []
    for n, i in ins.items():
        if i.get('role') != 'pc_path':
            continue
        for p, dom in PC_PATH_CLOCK_ENTRIES.items():
            if p not in specs[n]:
                continue
            items = i['inputs'].get(p)
            if (not isinstance(items, list) or len(items) != 1 or 'external' not in items[0]
                    or tops.get(items[0]['external'], {}).get('kind') != 'clock' or specs[n][p]['width'] != 1
                    or items[0].get('width') != 1):
                raise ValueError(f'{n}.{p}: a pc_path clock entry must be one whole external die clock (separate entry)')
            out.append(dict(instance=n, port=p, domain=dom, source=items[0]['external']))
    return out


def identifier(name):
    if not isinstance(name, str) or not IDENT.fullmatch(name):
        raise ValueError(f'invalid Verilog identifier {name!r}')
    return name


def source(path, module, root=ROOT):
    p = Path(path)
    if p.is_absolute() or '..' in p.parts or not p.parts or p.parts[0] != 'rtl' or 'test' in p.parts:
        raise ValueError(f'source must be repository RTL: {path}')
    spec = _source(root, path, module)
    txt = (root/path).read_text()
    clean = re.sub(r'/\*.*?\*/|//[^\n]*', '', txt, flags=re.S)
    m = re.search(r'\bmodule\s+'+re.escape(module)+r'\b(.*?);', clean, re.S)
    body = clean[m.end():].split('endmodule', 1)[0]
    if re.search(r'\b(?:blackbox|DPI|real|shortreal)\b|\$readmem', body, re.I):
        raise ValueError(f'modeled/externally injected internal producer refused: {module}')
    header = m.group(1)
    pm = re.match(r'\s*#\s*\((.*?)\)\s*\(', header, re.S)
    spec['parameters'] = re.findall(r'\b(\w+)\s*=', pm.group(1)) if pm else []
    return spec


def integer_expr(expr, params):
    """Only integer arithmetic; never evaluate arbitrary compiler/source text."""
    expr = expr.replace('$clog2', 'clog2')
    tree = ast.parse(expr, mode='eval')
    def walk(n):
        if isinstance(n, ast.Constant) and type(n.value) is int: return n.value
        if isinstance(n, ast.Name) and n.id in params: return params[n.id]
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id=='clog2' and len(n.args)==1 and not n.keywords:
            x=walk(n.args[0])
            if x<1: raise ValueError('clog2 argument must be positive')
            return (x-1).bit_length()
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub,ast.UAdd)):
            return -walk(n.operand) if isinstance(n.op, ast.USub) else walk(n.operand)
        if isinstance(n, ast.BinOp):
            a,b=walk(n.left),walk(n.right)
            ops={ast.Add:lambda:a+b,ast.Sub:lambda:a-b,ast.Mult:lambda:a*b,
                 ast.Div:lambda:a//b,ast.FloorDiv:lambda:a//b,ast.LShift:lambda:a<<b,
                 ast.RShift:lambda:a>>b}
            if type(n.op) in ops:return ops[type(n.op)]()
        raise ValueError(f'unsupported width expression {expr!r}')
    return walk(tree.body)


def ports(spec, params):
    if set(params)!=set(spec['parameters']) or any(type(v) is not int for v in params.values()):
        raise ValueError(f'{spec["module"]}: supply every parameter explicitly: {spec["parameters"]}')
    out={}
    for p in spec['ports']:
        if p['direction']=='inout':raise ValueError('digital inout requires an explicit PHY boundary adapter')
        if p['range']:
            hi,lo=p['range'].split(':')
            hi,lo=integer_expr(hi,params),integer_expr(lo,params)
            if lo!=0 or hi<lo:raise ValueError(f'unsupported port range {p}')
            width=hi+1
        else:width=1
        out[p['name']]=dict(direction=p['direction'],width=width)
    return out


def requirements(root=ROOT):
    result={}
    for role,(path,module,count) in ROLES.items():
        try: spec=source(path,module,root)
        except FileNotFoundError:
            result[role]=dict(source=path,module=module,count=count,status='MISSING_SOURCE')
            continue
        result[role]=dict(spec,count=count,status='SOURCE_ONLY_UNJOINED')
        if role=='writer_programme':
            result[role]['required_parameters']=dict(MUT=0,VMAP=1)
            if 'VMAP' not in spec['parameters']:result[role]['status']='SOURCE_PARAMETER_SUCCESSOR_REQUIRED'
    return dict(schema='opentallas.qwen_kv_static.requirements.v1',roles=result,
                native_qualified=False,physical_qualified=False,
                required=['actual on-chip sequencer/boot/config/epoch producers',
                          'independent writer/link programme expectations',
                          'HOST write/completion/fault/drain connections',
                          'full source-pinned static compiler programme and operation ports',
                          'actual die placement/pins/clock delivery/relays and native physical qualification'])


def validate_native_edges(ins):
    """Critical ABI edges cannot be satisfied by an unrelated same-width bus."""
    def edge(i,p,role,port):
        items=i['inputs'][p]
        if len(items)!=1 or 'instance' not in items[0]:
            raise ValueError(f'{i["name"]}.{p}: direct actual {role} output required')
        item=items[0];src=ins[item['instance']]
        if src['role']!=role or item['port']!=port or item['lo']!=0:
            raise ValueError(f'{i["name"]}.{p}: wrong native producer; expected {role}.{port}')
        return src
    byrole={role:[i for i in ins.values() if i['role']==role] for role in ROLES}
    # Synthetic unit fixtures have no writer; production population enforces it.
    for i in byrole.get('writer_programme',[]):
        if i.get('parameters',{}).get('VMAP')!=1:raise ValueError('v1.5 independent writer programme requires actual VMAP1 source/parameter')
    for i in byrole.get('writer',[]):
        if i['parameters']['VMAP']!=1:raise ValueError('v1.5 writer requires VMAP1')
        for p,sp in WRITER_LINK_MAP.items():edge(i,p,'link',sp)
        for p,sp in WRITER_PROGRAMME_MAP.items():edge(i,p,'writer_programme',sp)
    for i in byrole.get('link',[]):
        edge(i,'kvn_compiled_identity','writer_programme','compiled_identity')
        edge(i,'kvn_compiled_generation','writer_programme','compiled_generation')
    seen_a=set()
    for i in byrole.get('k_issuer',[]):
        a=edge(i,'rq','ectla','rq');seen_a.add(a['name'])
        if a['parameters']['STATIC_QK']!=1 or a['parameters']['ROW_RETURN_LAT']!=i['parameters']['RESPONSE_LAT']+7:
            raise ValueError('ECTL requires STATIC_QK1 and actual bridge/segment ROW_RETURN_LAT=L+7')
        if edge(a,'rs','k_issuer','rs')['name']!=i['name']:raise ValueError('ECTL/issuer response peer mismatch')
        landing_peer=None
        for p in ('rsp_valid','rsp_data','rsp_t','rsp_v','rsp_epoch','rsp_layer'):
            land=edge(i,p,'landing',p)
            if landing_peer is not None and landing_peer!=land['name']:raise ValueError('split landing response peer')
            landing_peer=land['name']
            # Both request and return belong to this physical landing group.
            for lp,sp in [('req_valid','req_valid'),('req_t','req_t'),('req_v','req_v'),('req_epoch','req_epoch'),('req_layer','req_layer')]:
                if edge(land,lp,'k_issuer',sp)['name']!=i['name']:
                    raise ValueError('landing request/response peer mismatch')
    if len(seen_a)!=len(byrole.get('k_issuer',[])):
        raise ValueError('each static K issuer needs its own actual ECTL A')


def compile_graph(graph, root=ROOT):
    if graph.get('schema')!='opentallas.qwen_kv_static.join.v1':raise ValueError('static compiler join schema required')
    image=graph['compiler_image']
    if image.get('schedule')!='fixed_cycle' or image.get('normal_backpressure') is not False:
        raise ValueError('fixed compiler cycles with no normal backpressure required')
    # Source files and compiled production image are independent immutable inputs.
    if not isinstance(image.get('programme'),dict):raise ValueError('actual compiled production programme missing; incomplete template cannot emit')
    for item in [image['programme']]+image['compiler_sources']:
        path=Path(item['path'])
        if path.is_absolute() or '..' in path.parts:raise ValueError('repository compiler/image path required')
        if hashlib.sha256((root/path).read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError(f'stale compiler/image source: {path}')
    programme=json.loads((root/image['programme']['path']).read_text())
    if programme.get('schema')!='opentallas.qwen_kv_static.programme.v1':
        raise ValueError('unsupported production programme kind/schema; actual emitted instruction enumeration required')
    if programme.get('operations')!=image['operations'] or programme.get('emitted_instruction_count')!=len(image['operations']):
        raise ValueError('operation coverage differs from pinned emitted production programme')
    if not image['compiler_sources']:raise ValueError('actual compiler sources required')
    pinned={}
    for item in graph['source_files']:
        path=Path(item['path'])
        if path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0]!='rtl' or 'test' in path.parts:
            raise ValueError('only actual repository RTL dependencies allowed')
        if hashlib.sha256((root/path).read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError(f'stale RTL dependency: {path}')
        pinned[str(path)]=item['sha256']
    tops={};ins={};specs={};counts=Counter()
    for p in graph['external_inputs']:
        n=identifier(p['name']);w=p['width']
        if n in tops or type(w) is not int or w<1:raise ValueError('duplicate/invalid boundary port')
        if p['kind'] not in ('clock','reset','analog_phy'):
            raise ValueError(f'on-chip operand/control cannot be external stimulus: {n}')
        tops[n]=p
    for i in graph['instances']:
        n=identifier(i['name']);mod=identifier(i['module'])
        if n in ins:raise ValueError(f'duplicate instance {n}')
        spec=source(i['source'],mod,root)
        if i['sha256']!=spec['sha256'] or pinned.get(i['source'])!=spec['sha256']:
            raise ValueError(f'stale/unlisted instance source: {n}')
        role=i.get('role')
        if role in ROLES:
            path,module,_=ROLES[role]
            if (i['source'],mod)!=(path,module):raise ValueError(f'wrong actual source for {role}')
            counts[role]+=1
        elif role!='producer':raise ValueError(f'unknown role {role}')
        pp=ports(spec,i['parameters']);specs[n]=pp;ins[n]=i
        if set(i['inputs'])!={p for p,v in pp.items() if v['direction']=='input'}:
            raise ValueError(f'{n}: all exact input ports must be connected')
        if role=='k_issuer' and (i['parameters']['RESPONSE_LAT']<1 or i['parameters']['MUT']!=0):
            raise ValueError(f'{n}: actual positive response latency and production MUT0 required')
        if role in ('landing','front_calendar','landing_calendar','writer','writer_programme','ownership','drain_guard','layer_programme','attention_programme','phase_launch',
                    'embgw','emb_return_head','emb_join','row_tx','es_fan_root') and i['parameters'].get('MUT')!=0:
            raise ValueError(f'{n}: production MUT0 required')
    if counts!=Counter({k:v[2] for k,v in ROLES.items()}):raise ValueError(f'full die actual source census mismatch: {dict(counts)}')
    validate_native_edges(ins)
    if any(i['role']=='pc_path' for i in ins.values()):
        for path in pc_emb_sources():
            if path not in pinned:raise ValueError(f'missing actual per-PC dependency: {path}')
    outs={}
    phy_output_ports={'po','fdi_tx_v','fdi_tx_flit','phy_rst_n','fwd_epoch','fwd_link_rst_n'}
    for p in graph['external_outputs']:
        n=identifier(p['name'])
        if n in tops or n in outs or p['kind']!='analog_phy':raise ValueError('invalid external output boundary')
        sn,sp=p['instance'],p['port']
        if sp not in phy_output_ports or specs[sn][sp]['direction']!='output':
            raise ValueError('on-chip result cannot be exported as an unimplemented consumer')
        if type(p['lo']) is not int or type(p['width']) is not int or p['lo']<0 or p['width']<1 or p['lo']+p['width']>specs[sn][sp]['width']:
            raise ValueError('invalid external PHY output slice')
        outs[n]=p
    if not outs:raise ValueError('actual PHY output boundary required')
    decls=[f'  input wire [{p["width"]-1}:0] {n}' for n,p in tops.items()]
    decls += [f'  output wire [{p["width"]-1}:0] {n}' for n,p in outs.items()]
    lines=['module qkd_die (',',\n'.join(decls),');'];edges=[];used=set()
    def wire(n,p):return f'n_{n}__{p}'
    for n,pp in specs.items():
        for p,v in pp.items():
            if v['direction']=='output':lines.append(f'  wire [{v["width"]-1}:0] {wire(n,p)};')
    def connection(n,p,items):
        if not isinstance(items,list) or not items:raise ValueError(f'{n}.{p}: missing real producer')
        terms=[];total=0
        for item in items:
            if 'strap' in item:
                # KVJ-F 10-17 (coordinator 0da (d)): the ECTL cfg is a FUNCTIONAL config word, boot-loaded through
                # qkd_kv_die_cfg (kv_static_kvjf_join.die_cfg_join), never a strap
                if p not in ('pc','cfg_stack','cfg_group'):raise ValueError(f'nonidentity constant operand refused: {n}.{p}')
                w=item['width'];val=item['strap']
                if type(w) is not int or type(val) is not int or w<1 or not 0<=val<2**w:raise ValueError('invalid identity strap')
                terms.append(f"{w}'d{val}");total+=w;continue
            lo=item['lo'];w=item['width']
            if type(lo) is not int or type(w) is not int or lo<0 or w<1:raise ValueError('invalid source slice')
            if 'external' in item:
                src=item['external'];v=tops[src];term=src;src_width=v['width']
                if v['kind']=='analog_phy' and p not in ('pi','fdi_tx_up','fdi_rx_v','fdi_rx_flit'):
                    raise ValueError(f'on-chip operand cannot be supplied by a PHY model: {n}.{p}')
                if v['kind'] in ('clock','reset') and not re.search(r'(?:ck|clk|hbm|rst|rsi|hrst)',p):
                    raise ValueError(f'clock/reset cannot supply operand {n}.{p}')
            else:
                sn,sp=item['instance'],item['port'];v=specs[sn][sp]
                if v['direction']!='output':raise ValueError(f'{sn}.{sp} is not an actual output')
                term=wire(sn,sp);src_width=v['width'];used.add((sn,sp))
                edges.append(dict(producer=f'{sn}.{sp}',consumer=f'{n}.{p}',lo=lo,width=w))
            if lo+w>src_width:raise ValueError('source slice exceeds actual port')
            terms.append(f'{term}[{lo+w-1}:{lo}]');total+=w
        if total!=specs[n][p]['width']:raise ValueError(f'{n}.{p}: {total} connected bits, expected {specs[n][p]["width"]}')
        return terms[0] if len(terms)==1 else '{'+', '.join(terms)+'}'
    for n,i in ins.items():
        pp=specs[n];cs=[]
        for p,v in pp.items():cs.append(f'.{p}({connection(n,p,i["inputs"][p]) if v["direction"]=="input" else wire(n,p)})')
        par=i['parameters'];pv=' #('+', '.join(f'.{k}({v})' for k,v in par.items())+')' if par else ''
        lines.append(f'  {i["module"]}{pv} {n} ('+', '.join(cs)+');')
    for n,p in outs.items():
        sn,sp=p['instance'],p['port'];lo,w=p['lo'],p['width']
        lines.append(f'  assign {n} = {wire(sn,sp)}[{lo+w-1}:{lo}];');used.add((sn,sp))
    for n,pp in specs.items():
        for p,v in pp.items():
            if v['direction']=='output' and ('fault' in p or p=='fo') and (n,p) not in used:
                raise ValueError(f'unconnected native fault observation: {n}.{p}')
    # Require an explicit source-bound input AND output port for every emitted
    # operation; an operation name/count or precomputed answer is not coverage.
    clock_entries=pc_path_clock_entries(ins,specs,tops)
    operations=image['operations']
    if not operations:raise ValueError('empty programme operation map')
    opids=set()
    for op in operations:
        if op.get('kind') not in ('hbm_command','k_row','v_row','kv_write','link_transfer','embedding_row','head_compute','barrier','host_transfer'):
            raise ValueError(f'unsupported emitted operation kind {op.get("kind")}')
        if op['id'] in opids:raise ValueError('duplicate emitted operation')
        opids.add(op['id'])
        if type(op['cycle']) is not int or op['cycle']<0:raise ValueError('operation needs fixed cycle')
        for key,direction in [('operands','input'),('results','output')]:
            if not op[key]:raise ValueError(f'{op["id"]}: missing actual {key}')
            for ep in op[key]:
                n,p=ep['instance'],ep['port']
                if specs[n][p]['direction']!=direction:raise ValueError('operation actual-port direction mismatch')
                if direction=='output' and (n,p) not in used:raise ValueError('operation result disconnected from native consumer')
    lines+=['endmodule','']
    return '\n'.join(lines),dict(schema='opentallas.qwen_kv_static.bind.v1',status='CONNECTED_SOURCE_GRAPH_ONLY',coverage_scope='static_KV_subsystem_source_graph_not_full_native_die',
        source_hashes={n:i['sha256'] for n,i in ins.items()},dependency_hashes=pinned,counts=dict(counts),edges=edges,
        emitted_operations=len(operations),clock_entries=clock_entries,native_qualified=False,physical_qualified=False,
        compiler_image=image)


def emit(graph_path,out,root=ROOT):
    text,report=compile_graph(json.loads(Path(graph_path).read_text()),root)
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    (out/'kv_die.v').write_text(text)
    (out/'static_bind.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'sources.f').write_text('\n'.join(report['dependency_hashes'])+'\n')
    return report


D2D_CAL_IMAGE = 'rtl/qwen_sys/d2d_static_20261015/d2d_cal_image.svh'


def compiled_txdp(name='D2D_TXDP_K', root=ROOT):
    """QXF-LINK (6ef1a097f): TXDP is a REQUIRED qkd/qfd_d2d_static parameter (no default; PR=1 with a zero byte does not
    elaborate). The die binds the compiler's value from the committed calendar image, never a literal."""
    m = re.search(r'localparam\s*\[31:0\]\s*' + name + r"\s*=\s*32'h([0-9a-fA-F]{8})\s*;", (root / D2D_CAL_IMAGE).read_text())
    if not m:
        raise ValueError(f'{D2D_CAL_IMAGE}: no {name} (compile it: tools/qwen_split/d2d_cal_image_production.sh)')
    v = int(m.group(1), 16)
    if any(((v >> (8 * b)) & 0xff) == 0 for b in range(4)):
        raise ValueError(f'{name} = {v:#010x}: a zero TX port byte is uncompiled')
    return v


def template(root=ROOT):
    """Populate proven ABI joins; leave every unimplemented producer as null.

    This is engineering input for the compiler integration owner, never a die
    netlist. Unknown measured latencies are null, not guessed physical values.
    """
    core_clock = __import__('os').environ.get('OT_KV_CONTROLLER_CORE', '0') == '1'
    params={
        'layer_programme':dict(MUT=0,**({'MU':1} if MU else {})),'attention_programme':dict(MUT=0,LAND=1 if __import__('os').environ.get('OT_KV_ATTN_LAND','0')=='1' else 0,RETIRE_STATIC=0),
        'phase_launch':dict(PH0=None,SAFE_LOW_U=None,SAFE_HIGH_U=None,META_HOLD_CORE=None,MUT=0,**({'SAME_CLOCK':1} if core_clock else {})),
        'ownership':dict(MUT=0,**({'MU':1} if MU else {})),'drain_guard':dict(MUT=0),
        'pc_path':dict(MU=1 if MU else 0,**({'CORE_CLOCK':1} if core_clock else {})),'landing':dict(MUT=0,HOP_MUT=0),
        'landing_calendar':dict(MUT=0,PH0=0,**({'SAME_CLOCK':1} if core_clock else {})),'front_calendar':dict(MUT=0),
        'k_issuer':dict(RESPONSE_LAT=None,MUT=0),
        'vport':dict(MUT=0,DQ=None,RT=None),
        'ectla':dict(STATIC_QK=1,QK_ISSUE_AGE=34,ROW_RETURN_LAT=None,HXK=QKH32.capture_hxk()),
        'writer':dict(MUT=0,VMAP=1,**({'MU':1} if MU else {})),'writer_programme':dict(MUT=0,VMAP=1),
        'link':dict(MUT=0,NL=2,NTX=d2d_ntx_k(),PR=1,TXDP=d2d_txdp_k() if root == ROOT else compiled_txdp(root=root)),
        'embgw':dict(MUT=0),'emb_return_head':dict(MUT=0),'emb_return_hop':{},'emb_join':dict(MUT=0,NATIVE32=1 if __import__('os').environ.get('OT_KV_EMB_N32','0')=='1' else 0,PIPE_JOIN=1 if __import__('os').environ.get('OT_KV_EMB_PJ','0')=='1' else 0),'row_tx':dict(MUT=0),
        'es_fan_root':dict(MUT=0),
    }
    instances=[];lookup={};specs={}
    def add(name,role):
        path,module,_=ROLES[role];sp=source(path,module,root);specs[name]=sp
        i=dict(name=name,role=role,source=path,module=module,sha256=sp['sha256'],
            parameters=params[role].copy(),inputs={p['name']:None for p in sp['ports'] if p['direction']=='input'})
        instances.append(i);lookup[name]=i;return i
    def width(n,p):
        sp=next(p0 for p0 in specs[n]['ports'] if p0['name']==p)
        if sp['range']:
            hi,lo=sp['range'].split(':');return integer_expr(hi,lookup[n]['parameters'])-integer_expr(lo,lookup[n]['parameters'])+1
        return 1
    def ep(n,p,lo=0,w=None):return dict(instance=n,port=p,lo=lo,width=width(n,p) if w is None else w)
    def join(dst,p,src,sp,lo=0,w=None):lookup[dst]['inputs'][p]=[ep(src,sp,lo,w)]
    def strap(dst,p,v,w):lookup[dst]['inputs'][p]=[dict(strap=v,width=w)]
    add('layer_programme','layer_programme');add('attention_programme','attention_programme')
    add('ownership','ownership');add('wrn','writer');add('wprg','writer_programme');add('d2d','link')
    for p,sp in [('start','writer_start'),('stage','stage'),('epoch','epoch'),('token','token'),('generation','generation')]:join('wprg',p,'layer_programme',sp)
    join('wprg','position','layer_programme','position',0,13)
    for p,sp in [('issue','attention_issue'),('run','attention_run'),('authority_valid','active'),('authority_epoch','epoch'),
                 ('authority_token','token'),('authority_position','position'),('authority_stage','stage')]:join('attention_programme',p,'layer_programme',sp)
    for p,sp in [('rx_event','att_rx_v'),('rx_payload','rx_payload'),('tx_slot','att_tx_slot'),('tx_slot_kind','att_tx_kind'),('tx_slot_beat','att_tx_beat')]:join('attention_programme',p,'d2d',sp)
    join('d2d','att_tx_v','attention_programme','tx_valid');join('d2d','att_tx_payload','attention_programme','tx_payload')
    for p,sp in WRITER_LINK_MAP.items():join('wrn',p,'d2d',sp)
    for p,sp in WRITER_PROGRAMME_MAP.items():join('wrn',p,'wprg',sp)
    join('d2d','kvn_compiled_identity','wprg','compiled_identity')
    join('d2d','kvn_compiled_generation','wprg','compiled_generation')
    order=(4,5,0,1,2,3,6,7)
    for stack,st in enumerate(('WS','WN','ES','EN')):
        for lane in range(4):add(f'vport_{st}_{lane}','vport')
        for g in range(8):
            land=f'slg_{st}_{g}';lc=f'lcal_{st}_{g}';fc=f'fcal_{st}_{g}';ki=f'ki_{st}_{g}';a=f'ectl_a_{st}_{g}';guard=f'drain_{st}_{g}';bridge=f'phase_{st}_{g}'
            for name,role in [(land,'landing'),(lc,'landing_calendar'),(fc,'front_calendar'),(ki,'k_issuer'),(a,'ectla'),(guard,'drain_guard'),(bridge,'phase_launch')]:add(name,role)
            for p,sp in [('ctrl_go','ctrl_go'),('kgo','kgo'),('vgo','vgo'),('ctx_t','ctx_t'),('epoch','epoch'),('layer','layer')]:join(bridge,p,'layer_programme',sp)
            for p in ('kgo_h','vgo_h'):join(fc,p,bridge,p)
            join(fc,'ctx_t',bridge,'ctx_t_h')
            for p,sp in [('kgo','kgo'),('vgo','vgo'),('ctx_t','ctx_t'),('epoch','epoch'),('layer','layer')]:join(lc,p,'layer_programme',sp)
            for p,sp in [('kgo','kgo'),('epoch','epoch'),('layer','layer')]:join(ki,p,'layer_programme',sp)
            # ectla cfg: placeholder identity value, REPLACED by kv_static_kvjf_join.die_cfg_join (boot-loaded die cfg);
            # compile_graph refuses it as a strap
            strap(land,'cfg_stack',stack,2);strap(land,'cfg_group',g,3);strap(a,'cfg',(g<<2)|stack,5)
            join(ki,'rq',a,'rq');join(a,'rs',ki,'rs')
            for p in ('req_valid','req_t','req_v','req_epoch','req_layer'):join(land,p,ki,p)
            for p in ('rsp_valid','rsp_data','rsp_t','rsp_v','rsp_epoch','rsp_layer'):join(ki,p,land,p)
            for p,sp in [('arm','arm'),('epoch','l_epoch'),('layer','l_layer'),('expected_put','l_put'),('expected_sector','l_sector')]:join(land,p,lc,sp)
            vport=f'vport_{st}_{g//2}';parity=g%2
            join(land,'vreq_valid',vport,f'vq{parity}_valid');join(land,'vreq_t',vport,f'vq{parity}_t')
            for p,sp in [('valid','rsp_valid'),('vflag','rsp_v'),('t','rsp_t'),('epoch','rsp_epoch'),('d','rsp_data')]:join(vport,f'in{parity}_{p}',land,sp)
            pcs=[]
            for q in range(4):
                pc=4*order.index(g)+q;n=f'pc_{st}_{pc}';add(n,'pc_path');pcs.append(n)
                strap(n,'pc',pc,5);strap(n,'cfg_stack',stack,2)
                for p,sp in [('cal_go','ctrl_go_h'),('cal_epoch','epoch_h'),('cal_layer','layer_h')]:join(n,p,bridge,sp)
                for p,sp,lo,w in [('expected_put','r_put',q,1),('expected_sector','r_sector',10*q,10),('expected_epoch','r_epoch',0,16),('expected_layer','r_layer',0,6)]:join(n,p,lc,sp,lo,w)
                join(n,'front_blk_go',fc,'blk_go',q,1)
            for p,sp in [('actual_valid','actual_valid'),('actual_sector','actual_sector'),('actual_epoch','actual_epoch'),('actual_layer','actual_layer'),('actual_data','actual_data')]:
                lookup[land]['inputs'][p]=[ep(n,sp) for n in reversed(pcs)]
            for p,sp in [('ctrl_idle_core','idle_core'),('ring_idle_core','return_idle_core'),
                         ('ctrl_idle_hbm','idle_hbm'),('front_idle_hbm','front_idle_hbm'),('ring_idle_hbm','return_idle_hbm'),
                         ('ctrl_fault_core','drain_fault_core'),('ctrl_completion_fault_core','completion_fault'),
                         ('ring_fault_core','return_fault_core'),('ctrl_fault_hbm','drain_fault_hbm'),
                         ('ctrl_output_fault_hbm','fo'),('ctrl_calendar_fault_hbm','cal_fault_hbm'),
                         ('ring_fault_hbm','return_fault_hbm'),('front_fault_overflow_hbm','front_fault_overflow_hbm'),
                         ('front_fault_go_hbm','front_fault_go_hbm'),('front_hold_hbm','front_hold')]:
                lookup[guard]['inputs'][p]=[ep(n,sp) for n in reversed(pcs)]
            lookup[guard]['inputs']['ctrl_intake_fault_core']=[ep(n,'er',260,1) for n in reversed(pcs)]
    # KVJ-C2: the embedding token path.  Every PC's es-merge endpoint returns its beat into the station at its own
    # physical slot of the stack's return train (slot 0 = the train head at the far strip end, slot 31 = the root);
    # the four roots meet in join4 beside the d2d KV end, whose word face feeds the row transmitter on d2d port 2.
    # The token start is the d2d end's kind-15 RESULT: fill_begin / fill_token / fill_epoch and the 128 PCs' token /
    # epoch (KVJ-C3: the PCs' token / epoch ride the static PC chain).  emb_boot_ready = the boot-only gateway's emb_ready
    # (est[0]).  KVJ-C3: the compiled slots (per-PC issue / word / half / scale / return slot, the 128 station capture /
    # transfer slots, the join beat slot) are played by the PC chain stations and join4_cal (kvjc3_pc_chain.py calendar).
    add('embgw','embgw');add('emb_join','emb_join');add('emb_tx','row_tx')
    join('emb_tx','fill_begin','d2d','engine_result_v');join('emb_tx','fill_token','d2d','engine_result_token')
    join('emb_tx','fill_epoch','d2d','engine_result_tag',TAG59_EPOCH_LO,16)
    for p in ('word_v','word_data','word_token','word_index','word_scale','word_epoch'):join('emb_tx',p,'emb_join',p)
    join('emb_tx','emb_tx_slot','d2d','emb_tx_slot')
    join('d2d','emb_tx_v','emb_tx','emb_tx_v');join('d2d','emb_tx_payload','emb_tx','emb_tx_payload')
    # KVJ-C3: the root of the four static PC chains (tools/qwen_kv_die/kvjc3_pc_chain.py ages).  Writer lane words and
    # the independent expected descriptor ride the chain to each PC's station (the writer's es / dest / expected faces);
    # the token-run start (the d2d kind-15 RESULT) rides it to every PC's embedding slot player; join4_cal plays the
    # join beat_slot from the same start.  Boot cfg of the root and join4_cal (the calendar constants, kvjc3 boot_words)
    # stay null: no dispatcher target yet (KVJ-A successor + KVJ-E image).
    add('fanr','es_fan_root')
    for p in ('es','dest_pc','dest_stack','identity','generation','expected_valid','expected_pc','expected_stack',
              'expected_identity','expected_generation','expected_address'):join('fanr',p,'wrn',p)
    join('fanr','emb_start','d2d','engine_result_v');join('fanr','emb_token','d2d','engine_result_token')
    join('fanr','emb_epoch','d2d','engine_result_tag',TAG59_EPOCH_LO,16)
    join('emb_join','start','d2d','engine_result_v')
    for s,st in enumerate(STACK_NAMES):
        prev=None
        join(f'pc_{st}_31','chain_i','fanr',f'd{s}')
        for slot in range(31):join(f'pc_{st}_{slot}','chain_i',f'pc_{st}_{slot+1}','chain_o')
        for slot in range(32):
            n=f'embr_{st}_{slot}';add(n,'emb_return_head' if slot==0 else 'emb_return_hop');pc=f'pc_{st}_{slot}'
            join(pc,'emb_boot_ready','embgw','est',0,1)
            join(n,'capture_slot',pc,'emb_capture_slot');join(n,'transfer_slot',pc,'emb_transfer_slot')
            join(n,'capture_v',pc,'emb_beat_v')
            lookup[n]['inputs']['capture_record']=[ep(pc,p_) for p_,_ in EMB_RECORD]
            if prev:join(n,'upi',prev,'upo')
            prev=n
        join('emb_join',f'up{s}',prev,'upo')
    guard_names=[f'drain_{st}_{g}' for st in ('WS','WN','ES','EN') for g in range(8)]
    lookup['ownership']['inputs']['group_drained']=[ep(n,'drained') for n in reversed(guard_names)]
    lookup['ownership']['inputs']['group_fault']=[ep(n,'fault') for n in reversed(guard_names)]
    dep_paths=set(pc_emb_sources())|set(EMB_SOURCES)|{i['source'] for i in instances}
    deps=[dict(path=p,sha256=hashlib.sha256((root/p).read_bytes()).hexdigest()) for p in sorted(dep_paths)]
    graph=dict(schema='opentallas.qwen_kv_static.join.v1',
        status='INCOMPLETE_TEMPLATE_NOT_EMITTABLE',source_files=deps,
        compiler_image=dict(schedule='fixed_cycle',normal_backpressure=False,programme=None,compiler_sources=[],operations=[]),
        external_inputs=[],external_outputs=[],instances=instances)
    gaps=dict(schema='opentallas.qwen_kv_static.open_joins.v1',
        instance_count=len(instances),unbound_inputs={i['name']:[p for p,v in i['inputs'].items() if v is None] for i in instances if any(v is None for v in i['inputs'].values())},
        source_parameter_gaps={i['name']:dict(required=sorted(i['parameters']),supported=specs[i['name']]['parameters']) for i in instances if set(i['parameters'])!=set(specs[i['name']]['parameters'])},
        unpriced_parameters={i['name']:[p for p,v in i['parameters'].items() if v is None] for i in instances if any(v is None for v in i['parameters'].values())},
        missing=['embedding token-run calendar boot image (KVJ-C3 RTL + kvjc3_pc_chain.py constants): no boot dispatcher target for the root / join4_cal cfg',
                 'actual sequencer/boot/config/metadata producers and reset/clock source graph',
                 'actual writer delivery/expectation/context routing and HOST/embedding interfaces',
                 'actual ECTL B/C/native head/PV/collective and producer/result graph',
                 'domain-safe native fault/completion/drain joins',
                 'complete RTL dependency closure and actual emitted production instruction manifest',
                 'physical homes/pins/clock delivery/relays/native TT FF DRC qualification'],
        native_qualified=False,physical_qualified=False)
    return graph,gaps


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--graph',type=Path);ap.add_argument('--template',action='store_true');a=ap.parse_args()
    if a.graph:emit(a.graph,a.out)
    elif a.template:
        a.out.mkdir(parents=True,exist_ok=True);g,gaps=template()
        (a.out/'static_join.template.json').write_text(json.dumps(g,indent=2)+'\n')
        (a.out/'static_open_joins.json').write_text(json.dumps(gaps,indent=2)+'\n')
    else:
        a.out.mkdir(parents=True,exist_ok=True)
        (a.out/'static_requirements.json').write_text(json.dumps(requirements(),indent=2)+'\n')
if __name__=='__main__':main()
