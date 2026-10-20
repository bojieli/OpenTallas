"""Source-derived complete FFN transport model; no unqualified calendar admission.

Current RD has neither a tier-crossing receiver nor a local loopback.  The
candidate below uses existing landed V bridges with an explicit typed RD
row-pair receiver extension and bounded SRAM staging. It is a model for owner
choice, never an assertion that those paths exist in RTL.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from dv_layer_compile import Die, ctl_path
from layer_prog.final_ffn import transfers, broadcasts, verify_moves
from layer_prog.lower_vpx import send_cfg, _vp

ROOT = HERE.parents[2]
SCRATCH = 480
SOURCE_PATHS = [
    'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xr.sv',
    'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv',
    'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv',
    'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap.sv',
    'results/arch/s81_dv_1016/bind9/die.v.gz',
    'results/arch/s81_dv_1016/p4l/plan.json',
    'results/arch/s81_dv_1016/landing/p4l/land_plan.json',
    'tools/s81_dv/layer_prog/final_ffn.py',
    'tools/s81_dv/layer_prog/xs_place.py',
    'tools/s81_dv/layer_prog/lower_vpx.py',
]

def source_pins(root):
    return {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in SOURCE_PATHS}


def verify_source(root, pins):
    if pins != source_pins(root):
        raise ValueError('stale final FFN transport source')


def pack(records):
    """Pack only exact contiguous source AND destination pairs, at most four."""
    result = []
    for m in records:
        if result:
            prev = result[-1][-1]
            same = all(m[k] == prev[k] for k in
                       ('rank', 'expert', 'source_sid', 'source_leaf', 'sid', 'leaf'))
            contiguous = all(m[k] == prev[k] + 2 for k in ('source_row', 'row'))
            if len(result[-1]) < 4 and same and contiguous:
                result[-1].append(m)
                continue
        result.append([m])
    return result


def v_pair(row, leaf, data):
    """PROPOSED 273-bit partner-only V ABI, never a currently supported beat."""
    if row not in range(0,1024,2) or leaf not in range(5) or not 0<=data<2**256:
        raise ValueError('invalid typed V row-pair')
    return 1 | (4<<1) | (leaf<<4) | (row<<7) | (data<<17)


def unpack_v_pair(word):
    if word>>273 or word&15 != 9:
        raise ValueError('invalid typed V row-pair header')
    row,leaf=(word>>7)&1023,(word>>4)&7
    if row%2 or leaf>=5:
        raise ValueError('invalid typed V row-pair destination')
    return row,leaf,word>>17


class Network:
    def __init__(self, die):
        self.die = die
        self.sid = {v['sid']: k for k, v in die.slices().items()}
        if set(self.sid) != set(range(16)):
            raise ValueError('expected actual sixteen uniquely strapped slices')

    def horizontal(self, source, destination):
        if source % 2 != destination % 2:
            raise ValueError('RD cannot cross tiers on an E/W line')
        c, dst = source // 2, destination // 2
        step = 1 if dst > c else -1
        result = []
        while c != dst:
            a, b = self.sid[2*c + source%2], self.sid[2*(c+step) + source%2]
            links = [(k, v) for k, v in self.die.links.items()
                     if any(x == (a, 'ro_e' if step == 1 else 'ro_w') for x in v['src'])
                     and any(x == (b, 'ri_w' if step == 1 else 'ri_e') for x in v['dst'])]
            if len(links) != 4:
                raise ValueError('missing full four-lane RD path')
            result.append(dict(source=2*c+source%2, destination=2*(c+step)+source%2,
                               lanes=sorted(k for k, _ in links),
                               age_edges=max(v['age_edges'] for _, v in links),
                               landed=all(v['landing'] is not None for _, v in links)))
            c += step
        return result

    def bridges(self, tier):
        result = []
        for col in range(8):
            a, b = self.sid[2*col+tier], self.sid[2*col+1-tier]
            links = [(k,v) for k,v in self.die.links.items()
                     if (a,'vo') in v['src'] and (b,'vi') in v['dst'] and v['landing']]
            if len(links) == 1:
                k,v = links[0]
                result.append((col,k,v))
        return result

    def route(self, source, destination, source_rank, destination_rank, leaf, source_row, row, pairs):
        """Complete proposed path; a submove = actual RDOUT + XR config.

        Each V crossing first stages into existing VP SRAM rows480..487, then
        re-reads the packet; no opaque full-die path or phantom direct V at the
        GUNIT/host/bank columns. One packet is globally in flight in the safe
        reference calendar, so one scratch slot is sufficient on every leaf.
        """
        if source_rank != destination_rank:
            raise ValueError('use explicit end-link leg for off-die transport')
        if source%2 == destination%2:
            return [dict(kind='local_copy_candidate' if source == destination else 'horizontal',
                         rank=source_rank, source=source, destination=destination,
                         source_row=source_row,row=row,leaf=leaf,pairs=pairs,
                         path=self.horizontal(source,destination))]
        choices = self.bridges(source%2)
        if not choices:
            raise ValueError('no actual landed V bridge')
        col,link,L = min(choices, key=lambda z:(abs(source//2-z[0])+abs(destination//2-z[0]), z[0]))
        a,b = 2*col+source%2, 2*col+destination%2
        legs=[]
        if source != a:
            legs.append(dict(kind='horizontal',rank=source_rank,source=source,destination=a,
                             source_row=source_row,row=SCRATCH,leaf=leaf,pairs=pairs,
                             path=self.horizontal(source,a)))
        legs.append(dict(kind='typed_v_pair_candidate',rank=source_rank,source=a,destination=b,
                         source_row=SCRATCH if source != a else source_row,
                         row=row if destination == b else SCRATCH,leaf=leaf,pairs=pairs,
                         path=[dict(lanes=[link],age_edges=L['age_edges'],landed=True)]))
        if destination != b:
            legs.append(dict(kind='horizontal',rank=source_rank,source=b,destination=destination,
                             source_row=SCRATCH,row=row,leaf=leaf,pairs=pairs,
                             path=self.horizontal(b,destination)))
        return legs


def model(root):
    die = Die(root)
    network = Network(die)
    moves=[m for rank in range(4) for m in transfers(rank)]
    verify_moves(moves)
    packets=pack(moves)
    local=[]
    for index,p in enumerate(packets):
        a=p[0]
        legs=network.route(a['source_sid'],a['sid'],a['rank'],a['rank'],a['leaf'],
                           a['source_row'],a['row'],len(p))
        # First RDOUT source leaf differs from the destination leaf, as in the
        # real capture map. Subsequent staging reads use the destination leaf.
        legs[0]['source_leaf']=a['source_leaf']
        for leg in legs[1:]: leg['source_leaf']=a['leaf']
        local.append(dict(packet=index,pairs=len(p),members=p,legs=legs))
    peers=[]
    for index,b in enumerate(broadcasts()):
        src,dst=b['source_rank'],b['destination_rank']
        delta=(dst-src)%4
        # Source-qualified LEGS topology: ES→WS +1, WS→ES -1,
        # EN→WN +2. Both +/-1 links use S, +2 uses N.
        end_source,end_destination = {1:(14,0),3:(0,14),2:(15,1)}[delta]
        outbound=network.route(b['source_sid'],end_source,src,src,b['leaf'],b['source_row'],SCRATCH,4)
        inbound=network.route(end_destination,b['sid'],dst,dst,b['leaf'],SCRATCH,b['row'],4)
        for leg in outbound+inbound: leg['source_leaf']=b['leaf']
        link=dict(kind='end_link',source_rank=src,destination_rank=dst,source=end_source,
                  destination=end_destination,source_leaf=b['leaf'],leaf=b['leaf'],
                  source_row=SCRATCH,row=SCRATCH,pairs=4,
                  timing_contract=None,arrival_age=None,
                  obligation='actual lane root/phase, host traffic and source-pinned fixed link age')
        peers.append(dict(packet=index,beat=b['beat'],legs=outbound+[link]+inbound))
    legs=[l for p in local+peers for l in p['legs']]
    # Literal candidate CTL words expose the exact encoding seam. Bit44 is a
    # NEW default-off local-delivery proposal, not an existing supported bit.
    for leg in legs:
        kind=leg['kind']
        if kind=='local_copy_candidate':
            direction,hops,is_local='E',1,True
        elif kind=='typed_v_pair_candidate':
            direction,hops,is_local='V',1,False
        elif kind=='end_link':
            direction,hops,is_local=('W' if leg['source']==0 else 'E'),1,False
        else:
            direction='E' if leg['destination']>leg['source'] else 'W'
            hops,is_local=abs(leg['destination']//2-leg['source']//2),False
        config=send_cfg(direction,4,hops,1<<leg['destination'],leg['leaf'],leg['row'],leg['pairs'])
        if is_local: config=(config & ~15) | (1<<44)
        leg['ctl']=dict(config_target=4,config_body=f'{config:040x}',
                        rdout_target=0,rdout_leaf_mask=1<<leg['source_leaf'],
                        rdout_body=f"{_vp(6,a0=leg['source_row'],n=leg['pairs']):040x}",
                        new_local_bit44=is_local,
                        source_issue_age=None,destination_write_age=None)
    counts=Counter(l['kind'] for l in legs)
    horizontal=Counter(f'rank{l["rank"]}/{k}' for l in legs if l['kind']=='horizontal' for h in l['path'] for k in h['lanes'])
    v=Counter(f'rank{l["rank"]}/{k}' for l in legs if l['kind']=='typed_v_pair_candidate' for h in l['path'] for k in h['lanes'])
    vpairs=Counter()
    for leg in legs:
        if leg['kind']=='typed_v_pair_candidate':
            for h in leg['path']:
                for lane in h['lanes']: vpairs[f'rank{leg["rank"]}/{lane}']+=leg['pairs']
    read_pairs=Counter()
    read_ports,write_ports=Counter(),Counter()
    for leg in legs:
        read_pairs[leg['kind']]+=leg['pairs']
        sr=leg.get('rank',leg.get('source_rank'))
        dr=leg.get('rank',leg.get('destination_rank'))
        read_ports[f'rank{sr}/sid{leg["source"]}/leaf{leg["source_leaf"]}']+=leg['pairs']
        write_ports[f'rank{dr}/sid{leg["destination"]}/leaf{leg["leaf"]}']+=leg['pairs']
    # Every read command and every config gets a distinct host template. Job
    # packing/reload is deliberately not hidden inside a per-packet estimate.
    end_links=Counter(f'rank{l["source_rank"]}/sid{l["source"]}' for l in legs if l['kind']=='end_link')
    lane_rate=(456/596)*(1023/1024)
    external_floor=math.ceil(max(end_links.values())/lane_rate)
    controls=2*len(legs)+80+320
    rank_controls=Counter({r:100 for r in range(4)})
    for leg in legs: rank_controls[leg.get('rank',leg.get('source_rank'))]+=2
    return dict(schema='opentallas.s81.final_ffn_transport.model.v1',admitted=False,
                die_sha256=die.die_sha,source_pins=source_pins(root),timing_contract=die.timing_contract,
                counts=dict(local_pairs=len(moves),local_packets=len(local),
                            packed_pairs=dict(Counter(len(p) for p in packets)),
                            local_payload_bytes=len(moves)*32,peer_packets=len(peers),peer_payload_bytes=len(peers)*128,
                            submoves=dict(counts),ctl_templates_before_dedup=controls,
                            control_words_by_rank=dict(rank_controls),
                            minimum_128row_jobs_before_dedup=sum((n+125)//126 for n in rank_controls.values()),
                            horizontal_276bit_lane_slots=dict(sorted(horizontal.items())),
                            rejected_full_serializer_v_fragment_slots={k:4*n for k,n in sorted(v.items())},
                            v_276bit_pair_slots=dict(sorted(vpairs.items())),
                            sram_256bit_read_and_write_pairs=dict(read_pairs),
                            sram_read_pair_slots=dict(sorted(read_ports.items())),
                            sram_write_pair_slots=dict(sorted(write_ports.items())),
                            busiest_read_port_pair_slots=max(read_ports.values()),
                            busiest_write_port_pair_slots=max(write_ports.values()),
                            end_link_552bit_flits=2*len(peers),
                            end_link_full_beats=dict(sorted(end_links.items())),
                            legacy_link_capacity_beats_per_cycle=lane_rate,
                            bandwidth_only_end_link_cycles=external_floor),
                storage=dict(scratch_rows=[SCRATCH,SCRATCH+8],scratch_bits_per_used_leaf=1024,
                             scratch_uses_existing_vp_sram=True,extra_sram_macros=0,
                             rejected_full_serializer_total_bits=1104*16*4,
                             pair_stream_new_payload_ff=0,
                             pair_stream_reuses_lo_sel_ci_r_vo_iv_dl_vb_rdat=True,
                             control_distribution_lower_bound_ff_per_slice=45,
                             control_distribution_lower_bound_total_ff=45*16*4,
                             existing_v_assembly_untouched=True,
                             global_inflight_packets=1,
                             leases_required=['capture128..240 through last RDOUT',
                                              'assembled320..432 through VS13 last read',
                                              'combined448..464 through every peer RDOUT and own POST',
                                              'scratch480..488 for every stage read/write',
                                              'pre1008 and post1009 through all320 POST completions']),
                ages=dict(vs13_pin_edges=75,post_pin_edges=63,actual_peer_post_arrival=None,
                          expression='POST_final = last qualified peer RD write + CTL-to-VP pin age + 63',
                          candidate_v_extension_edges=None,
                          pair_stream_rate_pairs_per_cycle=1,
                          bandwidth_only_cycle_lower_bound=max(max(vpairs.values()),max(horizontal.values()),
                                                              max(read_ports.values()),max(write_ports.values()),external_floor),
                          serialized_reference_pair_slots=sum(read_pairs.values()),
                          full_token_added_cycles=None,
                          reason='new local/V pair mechanism, XR2 send/receive and external link need real source-bound replay'),
                ctl_paths={str(sid):ctl_path(die,inst) for sid,inst in sorted(network.sid.items())},
                current_source_blockers=dict(cross_tier_pairs=sum(m['source_sid']%2!=m['sid']%2 for m in moves),
                                             same_slice_pairs=sum(m['source_sid']==m['sid'] for m in moves),
                                             peer_link_fixed_age_qualified=False),
                local=local,peers=peers)


def admit(record,binding):
    """Never convert the architecture proposal to a production calendar."""
    if record.get('source_pins') != binding.get('source_pins'):
        raise ValueError('unbound source pins')
    if not binding.get('reservations'):
        raise ValueError('unreserved final FFN calendars')
    if not binding.get('leases'):
        raise ValueError('unbound VPX lifetimes')
    # No current source contract implements the typed/local mechanism. Supplying
    # arbitrary cycles or a positive checker flag cannot manufacture one.
    raise ValueError('current source lacks typed V RD/local-copy and qualified peer POST arrival contracts')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=ROOT)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    result=model(a.root)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=1)+'\n')
    print(json.dumps(dict(local_pairs=result['counts']['local_pairs'],local_packets=result['counts']['local_packets'],
                          peer_packets=result['counts']['peer_packets'],submoves=result['counts']['submoves'],
                          blockers=result['current_source_blockers'],admitted=False)))

if __name__=='__main__': main()
