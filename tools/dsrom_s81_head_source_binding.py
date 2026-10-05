#!/usr/bin/env python3
"""Additive S81 released-head source compiler and bounded raw-byte provider.

No allocator, image builder, FP arithmetic, host argmax or numerical callbacks.
Programs are literal native ISA; enrollment requires concrete native consumers.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import hdc_isa_v41 as ISA
from dsrom_checkpoint import Checkpoint

CANONICAL = ROOT / 'results/uarch/dsrom_s81_head12_partition_20261004/canonical'
DEMAND = ROOT / 'results/uarch/dsrom_native_weight_address_join_20261002/inputs/demand-r5.json.gz'
TP, ROWS, K = 4, 32320, 5120
SHAPES = {'head.weight': [TP * ROWS, K], 'norm.weight': [K]}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def word(instruction):
    return ISA.encode(full_shape=True, **instruction)


class HeadSourceBinding:
    def __init__(self, canonical=CANONICAL, demand=DEMAND):
        self.canonical, self.demand = Path(canonical), Path(demand)
        inv = json.loads((self.canonical / 'inventory.json').read_text())
        require((inv['stages'], inv['TP'], inv['pairs_per_rank_die'], inv['BF_dual_pairs'],
                 inv['rows'], inv['macros_per_pair'], inv['ROM_ECC']) ==
                (81, 4, 2417, 519, 4096, 4, False), 'not accepted S81 geometry')
        self.layout = inv['dedicated_storage']
        self.head_dies = self.layout['head_dies']
        self.pairs_per_die = self.layout['head_storage_pairs_per_die_ceiling']
        self.partition = self.layout.get('head_storage_partition', 'contiguous')
        require(self.head_dies == inv['head_dies'] and type(self.pairs_per_die) is int,
                'inventory/storage head topology mismatch')
        if self.partition == 'global_pair_round_robin':
            ds = self.layout['dspark_storage']
            total = self.layout['head_storage_total_pairs']
            require(self.head_dies == 12 and ds['pair_start'] == 5051 and
                    ds['bytes'] == 7932874632 and ds['tensor_count'] == 2401 and
                    ds['pairs'] == (ds['bytes']+524287)//524288 and
                    total == 5051+ds['pairs'] and self.pairs_per_die == (total+11)//12,
                    'selected 12-head drafter partition mismatch')
        else:
            require(self.partition == 'contiguous' and self.head_dies == 8 and
                    self.pairs_per_die == (5051+7)//8, 'historical head topology mismatch')
        self.tensors = {x['tensor']: x for x in self.layout['global_tensors']}
        for name, start, pairs, shape in [('embed.weight', 0, 2525, [129280, 5120]),
                                         ('head.weight', 2525, 2525, SHAPES['head.weight']),
                                         ('norm.weight', 5050, 1, SHAPES['norm.weight'])]:
            x = self.tensors[name]
            elements = shape[0] * (shape[1] if len(shape) == 2 else 1)
            require((x['pair_start'], x['pairs'], x['shape'], x['elements'], x['words'],
                     x['word_data_bits'], x['secded_bits']) ==
                    (start, pairs, shape, elements, elements // 16, 256, 0),
                    'released global allocation mismatch: ' + name)
        with gzip.open(self.demand, 'rt') as f:
            nodes = json.load(f)['nodes']
        self.nodes = sorted((n for n in nodes if n.get('scope') == 'head' and
                             n.get('kind') == 'instruction'), key=lambda n: n['instruction_index'])
        require([n['id'] for n in self.nodes] == [f'Lhead.I{i}' for i in range(7)],
                'missing/duplicate literal head instructions')
        for n in self.nodes:
            require(hashlib.sha256(word(n['instruction']).to_bytes(256, 'little')).hexdigest() ==
                    n['template_word_sha256'], 'literal source ISA mismatch: ' + n['id'])
        self.services = {n['id']: n for n in nodes if n.get('scope') == 'head' and
                         n.get('kind') != 'instruction'}
        require({'Lhead.fence', 'global_argmax'} <= self.services.keys(), 'missing actual head consumers')

    @staticmethod
    def global_id(rank, row):
        require(type(rank) is int and 0 <= rank < TP and type(row) is int and
                0 <= row < ROWS, 'rank/local head row out of range')
        return rank * ROWS + row

    def address(self, tensor, row, col=0):
        require(tensor in SHAPES, 'only released head/norm provider enrolled')
        shape = SHAPES[tensor]
        require(type(row) is int and 0 <= row < shape[0] and type(col) is int and
                0 <= col < (shape[1] if len(shape) == 2 else 1), 'head tensor coordinate')
        idx = row * (shape[1] if len(shape) == 2 else 1) + col
        w, lane = divmod(idx, 16)
        gp = self.tensors[tensor]['pair_start'] + w // 16384
        if self.partition == 'global_pair_round_robin':
            pair, die = divmod(gp, self.head_dies)
        else:
            die, pair = divmod(gp, self.pairs_per_die)
        mb, logical = divmod(w % 16384, 8192)
        require(die < self.head_dies and pair < self.pairs_per_die, 'head storage capacity exceeded')
        return dict(tensor=tensor, element=idx, byte_offset=idx * 2,
                    provider_class='head_storage', die_namespace='dedicated_head_storage',
                    die=die, pair=pair, global_pair=gp, partition=self.partition, mb=mb, parity=logical % 2, physical_row=logical // 2,
                    bit_range=[lane * 16, (lane + 1) * 16], word_bits=256,
                    physical_macros_per_pair=4, physical_macro_depth=4096,
                    transport_ABI_qualified=False)

    def head_address(self, rank, row, col):
        return self.address('head.weight', self.global_id(rank, row), col)

    def model(self):
        # Existing dedicated-head chunk8/1024-tree contract, not legacy ME recurrence.
        return dict(schema='dsrom.s81.head.source-model.v1', ranks=4, head_storage_dies=self.head_dies,
                    head_storage_partition=self.partition,
                    head_storage_pairs_per_die=self.pairs_per_die,
                    rows_per_rank=ROWS, K=K, MACs_per_rank=ROWS*K,
                    weight_read_bytes_per_rank=ROWS*K*2, raw_weight_words_per_rank=ROWS*K//16,
                    logits_bytes_per_rank=ROWS*4, BF16_activation_bytes_per_rank=K*2,
                    norm_gamma_bytes=K*2, norm_CROM_output_bits_per_element=64,
                    native_BF_word_useful_bits=256, native_BF_container_bits=274,
                    uncached_native_BF_word_raw_reads=8, uncached_native_BF_word_read_bytes=256,
                    buffered_128K_group_reuse_requires_actual_consumer_storage=True,
                    chunk8_leaves=640, padded_leaf_slots=1024, grains=[[0,4096],[4096,5120]],
                    grain_leaves=[512,128], extra_merge_FP32_adds_per_row=3,
                    conditional_LAT3_tail_edges=9, serial_clock_GHz=0.9,
                    conditional_tail_ns=10, tail_excludes_CDC_and_delivery=True,
                    root_slot_bits=86, conservative_unmatched_bits_per_rank=ROWS*86,
                    actual_unmatched_slots=None, rank_argmax_pair_bits=64,
                    global_argmax_input_bits=256, global_argmax_output_bits=64,
                    global_id_bits=17, replica_count=4,
                    MACs_per_cycle=None, bytes_per_cycle=None, bits_per_cycle=None,
                    tracks_needed=None, channel_capacity=None, mux_fanout_cost=None,
                    compute_area_mm2=None, compute_slot_fit=None, whole_token_latency_ns=None,
                    hardware_admission=False, legacy_sequential_accumulator_admitted=False,
                    costs_already_in_dedicated_storage=True)

    def compile(self, *, opt_in=False, entry14, pc_base=0):
        require(opt_in, 'head source enrollment is opt-in')
        require(type(entry14) is int and 0 <= entry14 < 16384 and type(pc_base) is int and
                0 <= pc_base <= 16384-7, 'native entry/PC namespace out of range')
        instructions = [dict(source_node=n['id'], source_pc=pc_base+i,
                             literal_fields=n['instruction'], template_sha256=n['template_word_sha256'],
                             word_hex=f'{word(n["instruction"]):0512x}')
                        for i, n in enumerate(self.nodes)]
        return dict(schema='dsrom.s81.head.source-program.v1', entry14=entry14,
                    instructions=instructions, producer_pc14=pc_base+5, end_pc14=pc_base+6,
                    actual_terminal_offer=False, literal_source_node='Lhead.I6',
                    ranks=[dict(rank=r, rows=ROWS, global_id_base=r*ROWS,
                                input_XN=[46464,51584], logits=[30428,62748],
                                weight_first=self.head_address(r,0,0),
                                weight_last=self.head_address(r,ROWS-1,K-1)) for r in range(TP)],
                    source_inputs={'H':'L39 actual H[4,5120] published version',
                                   'PF':'L39 actual PF[4] published version'},
                    provider_word_mapping=dict(raw_storage='16 contiguous BF16 values per256bit word',
                        native_BF='Kcol=h*128+lane*8+b, lane0..15; h0..39,b0..7',
                        chunk8='Kcol=chunk*8+j, chunk0..639,j0..7',
                        padded_native_274_bits='high18 bits zero; ROM ECC disabled'),
                    norm_provider={'tensor':'norm.weight', 'CLO_base':0, 'words':K,
                                   'conversion':'BF16 bits <<16 in CROM low32; high32=0',
                                   'first':self.address('norm.weight',0),
                                   'last':self.address('norm.weight',K-1)},
                    output_lease_requirement='XN retained until last K read; logits span aliases XN, '
                        'so native consumer must capture/protect all5120 inputs before overlapping writes',
                    consumer_services=self.services, arithmetic=dict(
                        leaf='FP32 sequential eight products from +0, native round points',
                        tree='640 leaves padded1024; preserve FP32 tree at every level',
                        output='unrounded FP32 source me_round0/oen1/amax1 unchanged',
                        argmax='actual native rank/global service; never host select/reindex'),
                    runtime_qualified=False, model=self.model(),
                    input_pins={'canonical_inventory_sha256':sha(self.canonical/'inventory.json'),
                                'literal_demand_sha256':sha(self.demand)})

    def emit(self, out, *, opt_in=False, entry14, pc_base=0):
        program = self.compile(opt_in=opt_in, entry14=entry14, pc_base=pc_base)
        out = Path(out)
        out.mkdir(parents=True, exist_ok=False)
        (out/'head_program.json').write_text(json.dumps(program, indent=2, sort_keys=True)+'\n')
        (out/'head_prog.hex').write_text(''.join(n['word_hex']+'\n' for n in program['instructions']))
        return program


class ReleasedHeadByteProvider:
    """Read exact BF16 source bytes with bounded pread, not a numerical oracle.

    Reads at most32 bytes per request, independent of checkpoint/image size.
    Physical home references accompany every source request for enrollment.
    """
    def __init__(self, binding, snapshot):
        self.binding = binding
        # Reuse the released-checkpoint reader already used by actual S81 input.
        self.owns_source = not isinstance(snapshot, Checkpoint)
        self.source = Checkpoint(snapshot) if self.owns_source else snapshot
        self.closed = False
        try:
            for name, shape in SHAPES.items():
                fd, base, spec = self.source.descriptor(name)
                size = shape[0]*(shape[1] if len(shape)==2 else 1)*2
                begin, end = spec['data_offsets']
                require(spec['dtype']=='BF16' and spec['shape']==shape and
                        type(begin) is int and type(end) is int and 0<=begin and end-begin==size and
                        base+end <= os.fstat(fd).st_size,
                        'released head header/extent mismatch')
        except Exception:
            self.close()
            raise

    def close(self):
        if not self.closed and self.owns_source:
            self.source.close()
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _read(self, tensor, element, count):
        require(not self.closed and tensor in SHAPES and 1<=count<=16 and 0<=element,
                'closed/out-of-range byte provider')
        return self.source.raw(tensor,element*2,count*2)

    def read(self, tensor, die, macro, row):
        """Actual dedicated-storage request ->32B, identical raw read semantics.

        macro is LOCAL to its head-storage die, never a layer field ID.
        Reject padding and a request aliasing embed/norm instead of head.
        """
        require(tensor in SHAPES and all(type(v) is int for v in (die,macro,row)) and
                0<=die<self.binding.head_dies and
                0<=macro<self.binding.pairs_per_die*4 and 0<=row<4096,
                'head physical request outside selected storage')
        pair,leaf=divmod(macro,4)
        gp=(pair*self.binding.head_dies+die if
            self.binding.partition=='global_pair_round_robin' else die*self.binding.pairs_per_die+pair)
        w=(gp-self.binding.tensors[tensor]['pair_start'])*16384+(leaf//2)*8192+row*2+leaf%2
        require(0<=w<self.binding.tensors[tensor]['words'],
                'physical request outside source tensor/padding')
        return self._read(tensor,w*16,16)

    def chunk8(self, rank, row, chunk):
        require(type(chunk) is int and 0<=chunk<640, 'chunk8 coordinate')
        home=self.binding.head_address(rank,row,chunk*8)
        raw=self._read('head.weight',home['element'],8)
        return dict(rank=rank, local_row=row, global_id=self.binding.global_id(rank,row),
                    chunk=chunk, K_begin=chunk*8, home=home, payload=raw,
                    bf16_bits=list(struct.unpack('<8H',raw)),
                    source='head.weight', native_arithmetic_required=True)

    def raw_word(self, rank, row, word_index):
        require(type(word_index) is int and 0<=word_index<320, 'raw head word coordinate')
        home=self.binding.head_address(rank,row,word_index*16)
        return home, self._read('head.weight',home['element'],16)

    def native_bf_word(self, rank, row, h, b):
        """Exact existing BF274 lane codec, with real raw-storage gather homes.

        This is packing/movement only. Eight actual32B reads are charged; no
        invented buffered cache or zero-cost raw-to-field address equivalence.
        """
        require(type(h) is int and 0<=h<40 and type(b) is int and 0<=b<8,
                'native BF group/step coordinate')
        raw=[];homes=[]
        for j in range(8):
            home,payload=self.raw_word(rank,row,h*8+j)
            homes.append(home);raw.extend(struct.unpack('<16H',payload))
        payload=sum(raw[lane*8+b]<<(lane*16) for lane in range(16))
        return dict(rank=rank,local_row=row,global_id=self.binding.global_id(rank,row),
                    h=h,b=b,word274=payload,source_homes=homes,
                    source_read_bytes=256,source_useful_bytes=32)

    def norm_crom(self, col):
        home=self.binding.address('norm.weight',col)
        bits=struct.unpack('<H',self._read('norm.weight',col,1))[0]
        return dict(index=col, home=home, raw_bf16=bits, word64=bits<<16)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',required=True)
    p.add_argument('--entry14',type=int,required=True)
    p.add_argument('--pc-base',type=int,default=0)
    p.add_argument('--opt-in',action='store_true')
    a=p.parse_args()
    HeadSourceBinding().emit(a.out,opt_in=a.opt_in,entry14=a.entry14,pc_base=a.pc_base)


if __name__=='__main__':
    main()
