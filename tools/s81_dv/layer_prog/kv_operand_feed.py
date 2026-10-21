"""Assemble real native KV operand-copy words from compiler CAP descriptors.

Descriptors establish a source address, never actual VM residency. This pass
does not read operand payloads, scoreboards or golden outputs. Its native
fragment remains unsealed until producer commits, clock/issuer reservations
and row leases are supplied by the owning programme assembler.
"""
import hashlib
import json
import re

from layer_prog import kv_bank_contract as K

BINDINGS_SHA256 = '5e2de380659740383ab311382803d92b34b8cf49359a3167d6f9aa3c56e6d7ee'
G9_DIE_SHA256 = '00715e1a11cc9681bf5f1d6a70cf5d4a2c9c3a8094730cf26291f9d3e3a4c8ea'
G9_TABLE_SHA256 = '0feb9b8c74476fbfaf0ce7a99dac3b71290a24c9635e6047d1501e6478a677d7'
BASE = 'rtl/dsrom_sys/s81_dv/slice/'
ADDRESS_SOURCES = {
    BASE+'ot_s81sl_cap_rt.sv': 'b4add20455f231ff8597ecf19bb9254ca608efbf0457ac6edeaf96c69e5a9a83',
    BASE+'ot_s81sl_vp.sv': 'd7073948db44727894d838f37b47056749e07890a2ada02ee6fb0f2bd9dc9b15',
    BASE+'ot_s81sl_xrt.sv': 'cfc3feb9b99bf96dada241b4f6323c116e888eddd25d0ad504f5cde0ba170b64',
}
SCHEMAS = {'opentallas.s81.aproj_native_programme.v1',
           'opentallas.s81.aggregate_local_replay.v1',
           'opentallas.s81.selected_local_cap_phase.v1'}


def canonical_sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def capture_readset(programme, rank):
    """Decode the actual CAP32/VP address law, including partial scalar masks."""
    if programme.get('schema') not in SCHEMAS or type(rank) is not int or rank not in range(4):
        raise ValueError('requires current native/aggregate programme descriptor and explicit TP4 rank')
    cap = programme['capture']
    cfg = cap['cfg']
    fields = dict(obase=(0,12),ops=(12,12),np=(24,3),fmt=(27,2),rbase=(29,16),
                  rcnt=(45,11),rsplit=(56,16),lo32=(72,1),hi32=(73,1))
    word = int(cap['cfg_d'], 16)
    if word >> 74 or any(((word >> bit) & ((1 << width)-1)) != cfg[key]
                         for key,(bit,width) in fields.items()):
        raise ValueError('CAP cfg_d differs from actual decoded descriptor')
    if cfg['fmt'] != 2 or cfg['np'] != 0:
        raise ValueError('KV feed supports current one-position fmt2 expanded-BF16 CAP only')
    commands = programme.get('command_descriptors', programme.get('events', []))
    expected_payload=(1 << cap['slice_index']) | (3 << 16) | (word << 26)
    def connected(command):
        payload = int(command['payload186'],16) if 'payload186' in command else (
            (int(command['data1104'],16) >> 21) & ((1<<186)-1)) if 'data1104' in command else -1
        return command.get('target') == 3 and int(command.get('body160','-1'),16) == word and payload == expected_payload
    if not any(connected(c) for c in commands):
        raise ValueError('capture is not connected to a real native target3 command')
    rows = cap['rows']
    base = cfg['rbase'] & 0x3fff
    if len(rows) != cfg['rcnt'] or [r['rank_row'] for r in rows] != list(range(base,base+cfg['rcnt'])):
        raise ValueError('CAP rows are incomplete, duplicated or outside actual rbase/rcnt')
    if [r for f in cap['frames'] for r in f['rows']] != [r['rank_row'] for r in rows]:
        raise ValueError('CAP rows do not match the actual selected frame MAT ownership')
    result=[]
    for row in rows:
        # Addresses below are derived from source, not copied from a prospective
        # ownership map whose leaf/packing assumptions might be stale.
        e = row['rank_row'] - base
        chunk = e >> 6
        wa = cfg['obase'] + 64*(chunk//5) + (e & 63)
        native, lane = wa >> 2, wa & 3
        if native >= 1024:
            raise ValueError('CAP address outside native VP SRAM')
        if row['tensor'] != 'wkv':
            continue
        index = row['golden_output_index'] - 1280  # identity only; no golden values read
        if not (128*rank <= index < 128*(rank+1)) or row['tensor_row'] != index-128*rank:
            raise ValueError('KV output identity does not match the explicit rank quarter')
        if row['rank_row'] != 320 + row['tensor_row']:
            raise ValueError('KV source is not the actual rank-local a_proj wkv rows320..447')
        actual = dict(slice=cap['slice'], sid=cap['slice_index'], leaf=chunk%5,
                      word_address=wa,capture_port=(wa>>2)&1,native128_row=native,word_lane=lane,
                      word_mask4=1 << lane,bit_mask128=f'{((1<<32)-1) << (32*lane):032x}')
        for key in ['leaf','word_address','capture_port','native128_row','word_lane','word_mask4','bit_mask128']:
            if key in row and row[key] != actual[key]:
                raise ValueError('source packet disagrees with CAP/VP address law: '+key)
        result.append(dict(actual,rank=rank,rank_row=row['rank_row'],kv_index=index,
                           cap_descriptor_sha256=canonical_sha(cap),
                           producer_programme_sha256=canonical_sha(programme),
                           value_format='32-bit BF16-expanded (low16 zero), not packed16',
                           actual_resident=False,sram_commit_edge=None,row_lease=None))
    return result


def _payload(sid, target, mask, body):
    return f'{(1<<sid) | (target<<16) | (mask<<21) | (body<<26):047x}'


def _horizontal(die, source, target):
    if source%2 != target%2:
        raise ValueError('feed needs existing explicit tier bridge/transport assembler; no implicit V path')
    names = {v['sid']:k for k,v in die.slices().items()}
    steps=[]
    traced = die.native_lane_routes() if hasattr(die,'native_lane_routes') else None
    step = 2 if target > source else -2
    for a in range(source,target,step):
        b = a+step
        out_pin,in_pin = ('ro_e','ri_w') if step > 0 else ('ro_w','ri_e')
        if traced is not None:
            lanes=[]
            for lane in range(4):
                paths=[p for p in traced if p['source']['instance']==names[a]
                       and p['source']['port']==out_pin and p['source']['lane']==lane
                       and any(d['instance']==names[b] and d['port']==in_pin and d['lane']==lane
                               for d in p['destination']) and p.get('unbound') is None]
                if len(paths)!=1:
                    raise ValueError('actual source station/landing chain missing or ambiguous')
                lanes.append(paths[0])
            steps.append(dict(source_sid=a,destination_sid=b,actual_lane_chains=lanes,
                              clock_phase_qualified=False,age_edges=None))
            continue
        src=die.inst[names[a]]['conns'];dst=die.inst[names[b]]['conns']
        def wires(expression):
            clean=re.sub(r'\s+','',expression).strip('{}')
            return clean.split(',')
        outgoing=wires(src.get(out_pin,''));incoming=wires(dst.get(in_pin,''))
        if len(outgoing)!=4 or outgoing!=incoming:
            raise ValueError('four actual direct lane wires not identical; explicit station/landing chain required')
        steps.append(dict(source_sid=a,destination_sid=b,
            source_instance=names[a],source_pin=out_pin,
            destination_instance=names[b],destination_pin=in_pin,actual_lane_wires=outgoing,
            source_clocks={k:v for k,v in src.items() if k=='clk' or k.startswith('ck_')},
            destination_clocks={k:v for k,v in dst.items() if k=='clk' or k.startswith('ck_')},
            clock_phase_qualified=False,age_edges=None))
    return steps


def assemble(die, programmes, bindings_raw, source_readset):
    """Return a data-free native fragment and exact unmet producer obligations.

    programmes is a list of {rank, programme} using the existing native API.
    die is the current compiler Die, not a fabricated route/residency table.
    bindings_raw is the immutable actual G9 source packet's original bytes.
    This source pass cannot turn prospective CAP descriptors into actual writes.
    """
    if hashlib.sha256(bindings_raw).hexdigest() != BINDINGS_SHA256:
        raise ValueError('wrong actual G9 source binding packet')
    bindings=json.loads(bindings_raw)
    kv=bindings['instances']['s_3N']
    if bindings['die_sha256'] != G9_DIE_SHA256 or bindings['table_sha256'] != G9_TABLE_SHA256:
        raise ValueError('actual G9 die/table identity mismatch')
    if kv['module'] != 'ot_s81sl_slice_kv512' or kv['param_sets'] != {'{}':1}:
        raise ValueError('requires actual unique parameter-free KV512 instance')
    if kv['source_sha256'] != 'e7e7d43950382920837e2fd553e384690338ed6f4343a7cfb83f2ea796137319':
        raise ValueError('selected KV wrapper source changed')
    readset=[]
    for entry in programmes:
        readset += capture_readset(entry['programme'], entry['rank'])
    if len({r['kv_index'] for r in readset}) != len(readset):
        raise ValueError('duplicate KV output ownership across source descriptors')
    missing = set(range(512)) - {r['kv_index'] for r in readset}
    holds=[]
    files=source_readset.get('files_sha256',{})
    if any(files.get(n) != d for n,d in ADDRESS_SOURCES.items()):
        holds.append('actual CAP_RT/VP/XRT source readset missing or changed')
    if sorted(source_readset.get('defines',[])) != sorted(bindings['defines']) or (
        source_readset.get('source_inputs_manifest_sha256') != bindings['source_inputs_manifest_sha256']):
        holds.append('actual seven-define G9 source-input manifest is not bound; historical six-define profile is insufficient')
    if die is None or die.die_sha != G9_DIE_SHA256:
        holds.append('actual G9 compiler Die/link graph not bound')
    if any(e['programme']['capture']['die_sha'] != G9_DIE_SHA256 for e in programmes):
        holds.append('CAP descriptor belongs to a different die; regenerate against actual G9')
    packets=[]
    if not holds:
        if die.inst[K.SLICE]['master'] != 'ot_s81sl_slice_kv512' or die.slices()[K.SLICE]['sid'] != 7:
            raise ValueError('compiler Die KV instance differs from actual source packet')
        for entry in programmes:
            cap=entry['programme']['capture']
            actual_frames=set(die.frames_of(cap['slice']))
            if any(f['frame'] not in actual_frames or die.inst[f['frame']]['master']!=f['master']
                   or die.strap(f['frame'],'lk')!=f['lk'] for f in cap['frames']):
                raise ValueError('CAP frame MAT ownership differs from actual selected Die/frame straps')
        for index in range(0,512,8):
            group = sorted((r for r in readset if index <= r['kv_index'] < index+8),key=lambda r:r['kv_index'])
            if not group:
                continue
            if len(group) != 8 or [r['kv_index'] for r in group] != list(range(index,index+8)):
                holds.append('partial eight-scalar KV group at index'+str(index));continue
            first=group[0]
            if first['slice'] not in die.slices() or die.slices()[first['slice']]['sid'] != first['sid']:
                raise ValueError('CAP source slice/SID differs from actual compiler Die')
            if first['native128_row']%2 or first['word_lane'] or any(
                (r['slice'],r['leaf'],r['native128_row'],r['word_lane'],r['cap_descriptor_sha256']) !=
                (first['slice'],first['leaf'],first['native128_row']+i//4,i%4,first['cap_descriptor_sha256'])
                for i,r in enumerate(group)):
                holds.append('KV group is not a complete native source pair at index'+str(index));continue
            source=first['sid'];target=7;dest=K.OPERAND_BASE+index//4
            try:
                path=_horizontal(die,source,target)
            except ValueError as error:
                holds.append(str(error));continue
            direction=0 if source==target else 1 if target>source else 2
            cfg=direction | (4<<4) | (abs(target//2-source//2)<<7) | ((1<<target)<<12) | (dest<<31)
            if source==target:cfg |= 1<<44
            rd=6 | (first['native128_row']<<4) | (1<<24)
            packets.append(dict(kv_indices=list(range(index,index+8)),source=first,
                destination=dict(slice=K.SLICE,sid=7,leaf=0,rows=[dest,dest+1],mask8=255),
                native_templates=[dict(target=4,payload186=_payload(source,4,0,cfg)),
                                  dict(target=0,payload186=_payload(source,0,1<<first['leaf'],rd))],
                route=path,scheduled_rows=[],issue_edge=None,destination_commit_edge=None,
                requires=['actual source pair word masks/commits and read lease',
                          'fixed CFG/RDOUT issuer slots and actual per-hop clock/landing phase',
                          'exclusive destination rows through KV read completion and service handoff']))
    # The real producer owner explicitly has no CAP write/residency receipt.
    # Neither cfg_d, frame_return_plan nor a scoreboard can satisfy this gate.
    holds += ['actual CAP VM write/commit and source-lifetime record is not supplied by the current programme API',
              'gain/descriptor/cos/sin source residency and finite parameter lifetimes are unbound',
              'fixed source-owned clock/issuer/retirement programme remains unbound']
    return dict(schema='opentallas.s81.kv_operand_feed.v1',status='SOURCE_FRAGMENT_HELD',
        source_binding_sha256=BINDINGS_SHA256,die_sha256=G9_DIE_SHA256,
        source_readset_sha256=canonical_sha(source_readset),selected_defines=bindings['defines'],
        target_source_binding=dict(master=kv['module'],top_params={},
            source_sha256=kv['source_sha256'],die_instance=kv['die_instance'],
            enabled_bank_path='u_s_3N.u_slice.lf[0].u_lf.g_kv.u_kv',
            physical_binding_qualified=False),
        readset=readset,native_pair_fragments=packets,source_only_kv_scalars=len(readset),
        missing_source_kv_indices=sorted(missing),actual_resident_kv_scalars=0,
        actual_completeness_mask512='0'*128,scheduled_rows=[],dispatch=None,
        sealed_programme_held=True,lifetime_qualified=False,runtime_qualified=False,
        kv_contract=K.contract(),holds=holds,
        primitive_age_scope=dict(receipt='results/token_pass/s81_owner_fold_layout_1021/component/publication.json',
            raw_local_RDOUT_CTL_to_VP_sw_pin=29,
            VP_sw_pin_to_SRAM_commit=dict(edges=1,qualification='source composition only'),
            qualification='Pinned RSTOPT/XRT/DL4/VP component only; not an issuer or actual G9 clock/link age'),
        qualification='Native source operand/copy assembly only; no assumed residency, payload, dates or zero-fill')
