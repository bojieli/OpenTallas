"""Canonical released placement and physical-owner authority boundary.

Static addresses are never runtime grants. Native handlers own publication and
retirement; this component validates their RF/VM source placement. No checkpoint
bytes, generated ready values, generation truncation, or local-stage fallback.
"""
from dataclasses import dataclass
from collections import defaultdict
import hashlib
import gzip
import json
from pathlib import Path
from tools.h4_qwen_released_provider_delivery import PROGRAM_SHA, validate_program
from tools.gpu_sys.canonical_qwen_transport import TransportError


def uint(value, width, name):
    if type(value) is not int or not 0 <= value < 1 << width:
        raise TransportError(name + ' aperture')
    return value


@dataclass(frozen=True)
class RFHome:
    version: str
    rank: int
    sm: int
    first: int
    end: int
    words: int
    birth: int
    retire: int
    consumers: tuple

    def key(self, local_word):
        uint(local_word, 32, 'local word')
        if local_word >= self.words:
            raise TransportError('word outside compiled home')
        return ('RF', self.rank, self.sm, self.first + local_word // 128), local_word % 128


class SourcePlacement:
    """Compile ALL released homes/extents, retaining exact rank-relative bytes.

    The r17 four-stack stripe has 128 PC locations PER rank. A separate admitted
    provider translation is mandatory to connect it to a 128-PC enclosing top.
    We return rank/stack/PC, never rank-modulo or a truncated global PC.
    """
    def __init__(self, native):
        validate_program(native)
        if len(native['operations']) != 1737:
            raise TransportError('released operation census')
        self.pin = dict(native['provider_binding_pin'])
        binding = native['provider_binding']
        self.rf = {}; self.extents = {}; self.spill = {}; self.control = {}
        versions = {v['version']: v for v in native['operands']} if isinstance(native['operands'], list) else native['operands']
        self.version_ids = {v: i for i, v in enumerate(sorted(versions))}
        for a in binding['allocation']:
            rank = uint(a['rank'], 1, 'rank'); previous = 0
            for e in a['extents']:
                base = uint(e['base'], 34, 'extent base'); size = e['bytes']
                if type(size) is not int or size <= 0 or base + size > 1 << 34 or base < previous:
                    raise TransportError('extent overlap or end aperture')
                previous = base + size
                key = (rank, e['name'])
                if key in self.extents: raise TransportError('duplicate extent')
                self.extents[key] = (base, size)
        slots = defaultdict(list)
        for h in binding['version_homes']:
            rank = uint(h['rank'], 1, 'rank'); sm = uint(h['SM'], 5, 'SM')
            key = (h['version'], rank, sm)
            if key in self.rf or key in self.spill: raise TransportError('duplicate home')
            v = versions[h['version']]
            if v['birth_pc'] != h['birth_pc'] or tuple(v['consumers']) != tuple(h['consumers']):
                raise TransportError('source lifetime differs from compiled recipe')
            home = h['home']
            if home['class'] == 'RF':
                first, end = home['slot_first'], home['slot_first'] + home['vectors']
                if not 32 <= first < end <= 512 or h['word_count'] > (end-first)*128:
                    raise TransportError('RF workspace/capacity collision')
                record = RFHome(h['version'],rank,sm,first,end,h['word_count'],h['birth_pc'],h['retire_pc'],tuple(h['consumers']))
                self.rf[key] = record
                for slot in range(first,end): slots[rank,sm,slot].append(record)
            else:
                base, end = home['global_byte_base'], home['byte_end_exclusive']
                lo,size = self.extents[rank,'activation_scratch']
                if not lo+sm*1048576 <= base < end <= lo+(sm+1)*1048576:
                    raise TransportError('spill escaped exact SM reservation')
                self.spill[key] = dict(h)
        for key, occupants in slots.items():
            order = sorted(occupants,key=lambda h:h.birth)
            for earlier,later in zip(order,order[1:]):
                if earlier.retire >= later.birth:
                    raise TransportError('RF live-version overlap')
        self.rf_slots = tuple(sorted(slots))
        for h in binding['control_homes']:
            self.control[h['version'],h['rank']] = dict(h)
        covered = {k[0] for k in self.rf} | {k[0] for k in self.spill} | {k[0] for k in self.control}
        if covered != set(versions): raise TransportError('incomplete canonical version ownership')

    @classmethod
    def released(cls, source_root=None):
        if source_root is None:
            # This tracked metadata is byte/canonical-identity checked by cls;
            # no private released worktree or trained-byte payload is required.
            root=Path(__file__).resolve().parents[2]
            path=root/'results/uarch/h3_qwen_complete_native_20261002/tiled_r1/Qwen_tiled.json.gz'
            with gzip.open(path,'rt') as f:return cls(json.load(f))
        from tools.gpu_sys.canonical_qwen_backend import load_originals
        _, byte_module = load_originals(source_root)
        return cls(byte_module.native())  # metadata only; no TrainedByteBackend

    def validate_rf(self, request, write):
        if request['program_sha256'] != PROGRAM_SHA: raise TransportError('program identity')
        key = request['source_key']
        if not isinstance(key,list) or len(key)!=4 or key[0]!='RF': raise TransportError('RF source key')
        _,rank,sm,slot = key
        uint(rank,1,'rank'); uint(sm,5,'SM'); uint(slot,9,'RF slot')
        h = self.rf.get((request['version'],rank,sm))
        if h is None or not h.first <= slot < h.end or request['lease'] != 'value:'+h.version:
            raise TransportError('RF key/version/lease not compiled home')
        pc = request['source_PC']
        if type(pc) is not int or not 0 <= pc < 1737 or (write is True and h.birth not in (-1,pc)) or (write is False and pc not in h.consumers):
            raise TransportError('source producer/consumer PC')
        return h

    def aperture(self,rank,name):
        uint(rank,1,'rank')
        try: return self.extents[rank,name]
        except KeyError as exc: raise TransportError('unknown compiled extent') from exc

    def kv_bases(self,layer,rank):
        if type(layer) is not int or not 0 <= layer < 36: raise TransportError('layer aperture')
        return tuple(self.aperture(rank,f'L{layer}.{kind}')[0] for kind in ('K','V'))

    @staticmethod
    def stripe(rank,byte):
        uint(rank,1,'rank'); uint(byte,34,'rank-relative byte')
        local = (byte//512)*128 + byte%128; sector = local//32
        uint(sector,31,'stack-local sector')
        row=sector>>15
        return dict(rank=rank,stack=(byte//128)%4,PC=((sector>>2)^(sector>>7)^(sector>>12))&31,
                    bank=((((sector>>12)^(row>>2))&7)<<2)|((sector^row)&3),
                    stack_local_byte=local,rank_byte=byte,byte_in_sector=local%32)

    def locate_word(self, version, rank, word):
        """Exact 256-word distributed block recipe; no payload materialisation."""
        uint(rank,1,'rank'); uint(word,32,'global word')
        sm=(word//256)%32
        local=(word//8192)*256+word%256
        key=(version,rank,sm)
        if key in self.rf:
            source_key,lane=self.rf[key].key(local)
            return dict(source_key=list(source_key),lane=lane,SM_instance=rank*32+sm)
        h=self.spill.get(key)
        if h is None or local>=h['word_count']: raise TransportError('word outside compiled version')
        byte=h['home']['global_byte_base']+4*local
        return dict(source_key=['HBM',rank,sm,byte//512*512],rank_byte=byte,
                    byte_in_page=byte%512,provider=self.stripe(rank,byte))

    def owner_model(self):
        # One direct-index row for each actually used RF seat, not 512 credits or
        # a new data store. Full session and native owner remain held physically.
        fields=dict(valid=1,published=1,session=64,version=11,owner=46)
        rows=len(self.rf_slots); bits=rows*sum(fields.values())
        by_sm=[sum(1 for rank,sm,slot in self.rf_slots if rank*32+sm==i) for i in range(64)]
        return dict(schema='canonical-qwen-source-owner-model-r1',rows=rows,rows_per_SM=by_sm,row_fields=fields,
                    raw_lease_bits=bits,prospective_sealed_words=rows*3,
                    prospective_sealed_bits=rows*3*72,seal_payload_bits_per_word=41,
                    seal_binding="actual SM6 in codec PC7, actual RFslot9, kind0/1/2; zero padding enforced",
                    rf_mirrored_payload_bits=4096,rf_read_bits=8192,
                    query_ports_per_SM=1,RF_SM_replicas=64,version_count=len(self.version_ids),
                    slot_select_bits=9,sm_select_bits=6,owner_bits=46,AW=34,CTAG=32,GEN=4,NC=6,
                    prospective_lookup_edges=2,prospective_issue_edges=1,
                    protection_bits=rows*(216-123),area_mm2=None,SS_FF_timing_admitted=False,
                    hardware_build_admitted=False,
                    remaining=['loaded three-word codec/query mux, held query state and clock cost',
                               'physical positive consumer/reverse retirement inputs',
                               'explicit r17 rank/four-stack to enclosing128PC provider translation'])


class PhysicalRFSourceAuthority:
    """Fail-closed factory boundary until the modeled allocator is enrolled.

    Static placement cannot turn callback functions or Python ready/clean maps
    into a physical owner. The native source-owner RTL/port contract is pending;
    keeping this explicit refusal prevents accidental full-factory enrollment.
    """
    def __init__(self,pins,placement,allocator):
        raise TransportError('physical source-owner allocator not yet enrolled; static placement is not a grant')


def freeze(output, source_root=None):
    """Reproducible metadata-only compilation, not a runtime owner receipt."""
    p=SourcePlacement.released(source_root)
    artifact=dict(schema='canonical-qwen-source-placement-r1',program_sha256=PROGRAM_SHA,
        source_commit='870c5fe581b768df28dd2998b2d0aecc24510c23',provider_pin=p.pin,
        operation_count=1737,version_count=len(p.version_ids),RF_home_count=len(p.rf),
        spill_home_count=len(p.spill),extent_count=len(p.extents),
        RF_homes=[dict(version=h.version,rank=h.rank,SM=h.sm,first=h.first,end=h.end,
                      words=h.words,birth=h.birth,retire=h.retire,consumers=list(h.consumers))
                  for _,h in sorted(p.rf.items())],
        spill_homes=[h for _,h in sorted(p.spill.items())],
        control_homes=[h for _,h in sorted(p.control.items())],
        extents=[dict(rank=k[0],name=k[1],base=v[0],bytes=v[1]) for k,v in sorted(p.extents.items())],
        version_ids=p.version_ids,owner_model=p.owner_model(),
        runtime_factory_ready=False,physical_ownership_qualified=False,
        provider_translation=dict(recipe_rank_count=2,stacks_per_rank=4,PCs_per_stack=32,
                                  enclosing_PC_count=128,qualified=False))
    # Explicit one artifact and deterministic bytes; never update old evidence.
    raw=(json.dumps(artifact,sort_keys=True,separators=(',',':'))+'\n').encode()
    out=Path(output);out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('xb') as f:f.write(gzip.compress(raw,mtime=0) if out.suffix=='.gz' else raw)
    return hashlib.sha256(raw).hexdigest()


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True)
    parser.add_argument('--released-source-root')
    args=parser.parse_args()
    print(freeze(args.out,args.released_source_root))
