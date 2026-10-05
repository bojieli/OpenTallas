"""L20 literal ME weight callbacks for the existing native BF field.

Reads released bytes through the unchanged matrix codec. No dot, activation,
clock, output publication, allocation change, or alternative reduction tree.
"""
import argparse
import hashlib
import json
import socket
from pathlib import Path
import dsrom_s82_payload_interface as API
from dsrom_s82_native_word_server import serve_connection

OPERATIONS = {
    'L20.I24': ('compressor.wkv', 5120, 128, 2, 27918, 46464),
    'L20.I30': ('indexer.wk', 512, 128, 2, 5890, 93728),
    'L20.I42': ('indexer.weights_proj', 5120, 32, 2, 6426, 46464),
    'L20.I68': ('wo_a.group0', 4096, 1024, 0, 5154, 74272),
    'L20.I69': ('wo_a.group1', 4096, 1024, 0, 5218, 78368),
    'L20.I86': ('gate', 5120, 96, 2, 22846, 46464),
}

def require(ok, message):
    if not ok:
        raise ValueError(message)

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

class ReleasedMeMatrixWords:
    def __init__(self, execution, source, node, rank, *, fragment=0, raw_provider=None):
        require(node in OPERATIONS, 'only six literal L20 ME weight operations')
        require(type(rank) is int and 0 <= rank < 4, 'TP4 rank')
        require(source.root.resolve().name == API.SNAPSHOT, 'released checkpoint revision')
        alias, K, rows, split, obase, xbase = OPERATIONS[node]
        instruction = execution.source.nodes[node]['instruction']
        expected = dict(unit=1, me_k=K >> split, me_split=split, me_nout=rows,
                        me_round=1, me_wsrc=0, me_oen=1, me_obase=obase,
                        me_xbase=xbase, me_ks=8, me_ots=8, me_ojs=1)
        require(all(instruction.get(k) == v for k,v in expected.items()) and
                instruction.get('me_amax', 0) == 0, 'literal ME source dimensions/control')
        resolved = execution.source.resolve(node, rank)
        dispatch = execution.dispatch(node, rank)
        matrices = resolved['fragments']
        require(dispatch['source_dispatch_bound'] and
                len(matrices) == len(dispatch['fragments']), 'canonical dispatch')
        offsets = [(0,768),(768,256)] if node in ('L20.I68','L20.I69') else [(0,rows)]
        require(len(matrices) == len(offsets), 'complete ordered fragments')
        for f, selected, (offset, count) in zip(matrices, dispatch['fragments'], offsets):
            m = f['matrix']
            require(m.get('original_alias', m['alias']) == alias and m['layer'] == 20 and
                    m['K'] == K and m['rows'] == count and m.get('row_offset',0) == offset and
                    m['format'] == 'bf16' and m['stage'] == 37 and m['compiled_NP'] == 2417,
                    'canonical matrix geometry/order')
            require(selected['source_matrix_sha256'] == digest(m) and
                    selected['rank'] == rank and selected['stage'] == m['stage'],
                    'selected fragment identity')
            conversion = 'FP8+UE8M0->BF16_RNE' if alias.startswith('wo_a.') else 'native'
            require(m['conversion'] == conversion, 'existing weight codec required')
        require(type(fragment) is int and 0 <= fragment < len(matrices), 'selected fragment')
        self.matrix = matrices[fragment]['matrix']
        self.selected = dispatch['fragments'][fragment]
        for name, dtype in [(self.matrix['tensor'], self.matrix['source_dtype'])] + (
                [(self.matrix['source_scale_tensor'], 'F8_E8M0')]
                if alias.startswith('wo_a.') else []):
            _,_, spec = source.descriptor(name)
            require(spec['dtype'] == dtype, 'released weight/scale dtype')
        self.source, self.rank = source, rank
        self.raw_provider = raw_provider
        if raw_provider is not None:
            require(raw_provider.source_matrix_sha256 == digest(self.matrix) and
                    raw_provider.rank == rank and callable(raw_provider.raw_chunk),
                    'Goodall raw source identity')
        self.pairs = tuple(sorted({p[1] for p in self.matrix['plans']}))
        self.source_matrix_sha256 = digest(self.matrix)

    def read(self, stage, rank, macro, physical_row):
        require(all(type(v) is int for v in (stage,rank,macro,physical_row)), 'integer address')
        require(stage == self.matrix['stage'] and rank == self.rank and
                0 <= macro < 4*2417 and macro//4 in self.pairs and 0 <= physical_row < 4096,
                'unowned selected ME source address')
        # The canonical inverse decoder rejects padding and ambiguous owners;
        # its weight codec alone supplies native BF16 or released FP8 conversion.
        require(self.matrix['conversion'] == 'native', 'native FP8 decoder required; host conversion forbidden')
        word = API.matrix_word(self.matrix,self.source,rank,macro,physical_row)
        require(type(word) is int and 0 <= word < 1 << 274, 'native word width')
        return word

    def raw_decoder_word(self, stage, rank, macro, physical_row):
        """Sixteen raw code/UE8 pairs, lanes mapped by canonical BF word slots.

        This is not a BF16 ROM word: native decode completion is required before
        the existing BF pair may read the expanded word. No host FP arithmetic.
        """
        require(all(type(v) is int for v in (stage,rank,macro,physical_row)), 'integer address')
        require(stage == self.matrix['stage'] and rank == self.rank and
                0 <= macro < 4*2417 and macro//4 in self.pairs and 0 <= physical_row < 4096,
                'unowned selected ME source address')
        if self.matrix['conversion'] == 'native':
            return self.read(stage,rank,macro,physical_row)
        raw=0
        for row,k,bit,width in API.word_coordinates(self.matrix,rank,macro,physical_row):
            require(width == 16 and bit % 16 == 0, 'canonical BF lane')
            home=API.M.physical_address(self.matrix,rank,row,k)
            sr,sc=home['source_row'],home['source_col']
            if self.raw_provider is None:
                code=self.source.element(self.matrix['tensor'],sr,sc)
                scale=self.source.element(self.matrix['source_scale_tensor'],sr//32,sc//32)
            else:
                chunk=self.raw_provider.raw_chunk(row,k,1)
                require(chunk['source_matrix_sha256'] == self.source_matrix_sha256 and
                        chunk['source_row'] == sr and chunk['source_col'] == sc and
                        chunk['dtype'] == 'F8_E4M3' and len(chunk['codes']) == 1 and
                        len(chunk['scales']) == 1, 'Goodall raw chunk identity/extent')
                code=chunk['codes'][0]
                scale_row=chunk['scales'][0]
                require((scale_row['row'],scale_row['col']) == (sr//32,sc//32),
                        'addressed UE8 scale identity')
                scale=scale_row['bits']
            require(type(code) is int and 0 <= code < 256 and
                    type(scale) is int and 0 <= scale < 256, 'released raw bytes')
            raw |= (code | scale << 8) << bit
        return raw

    def word_requests(self, pair):
        """Exact bank,row prefill requests for ONE borrowed runtime pair."""
        require(type(pair) is int and pair in self.pairs, 'owned canonical pair')
        requests=set()
        for _,p,_,count,_,start,words in self.matrix['plans']:
            if p != pair:
                continue
            for logical in range(start,start+count*words):
                for mb in range(2):
                    request=(2*mb+logical%2,logical//2)
                    require(request not in requests, 'overlapping native word ownership')
                    require(API.word_coordinates(self.matrix,self.rank,4*pair+request[0],request[1]),
                            'empty native word owner')
                    requests.add(request)
        return tuple(sorted(requests))

    __call__ = read

    def receipt(self):
        return dict(stage=37,rank=self.rank,source_matrix_sha256=self.source_matrix_sha256,
                    alias=self.matrix['alias'],K=self.matrix['K'],rows=self.matrix['rows'],
                    row_offset=self.matrix.get('row_offset',0),pairs=list(self.pairs),
                    conversion=self.matrix['conversion'], checkpoint_revision=API.SNAPSHOT,
                    native_image_word_count_by_pair={p:2*sum(x[3]*x[6] for x in self.matrix['plans'] if x[1]==p) for p in self.pairs},
                    native_arithmetic='existing PB/cut/SUM/retn/root only',
                    private_cut=False, native_execution_qualified=False)

def main():
    from dsrom_s81_execution_binding import CanonicalS81Execution
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fd',type=int,required=True)
    p.add_argument('--owner',type=Path,required=True)
    p.add_argument('--checkpoint',type=Path,required=True)
    p.add_argument('--node',choices=OPERATIONS,required=True)
    p.add_argument('--rank',type=int,required=True)
    p.add_argument('--fragment',type=int,default=0)
    a=p.parse_args()
    source=API.Checkpoint(a.checkpoint)
    try:
        execution=CanonicalS81Execution(a.owner)
        # Current main Goodall fa280 successor supplies the raw source API;
        # its constructor/dispatch reads no activations and does no conversion.
        from dsrom_s81_qe_native_word_bridge import ReleasedQeOperationWords
        raw=ReleasedQeOperationWords(execution,source,a.node,a.rank,fragment=a.fragment)
        provider=ReleasedMeMatrixWords(execution,source,a.node,a.rank,
                                      fragment=a.fragment,raw_provider=raw)
        with socket.socket(fileno=a.fd) as connection:
            return 0 if serve_connection(connection,provider.raw_decoder_word) else 1
    finally:
        source.close()

if __name__ == '__main__':
    raise SystemExit(main())
