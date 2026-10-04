"""Native QE callback bridge: canonical selected field QE/ME -> released raw words.

Private inherited connection, same existing wire codec; no filesystem socket,
allocator, images, activations, output oracle or numerical execution.
"""
import argparse
import hashlib
import json
import re
import socket
from pathlib import Path
import dsrom_s82_payload_interface as API
from dsrom_s82_native_word_server import serve_connection


def require(ok, message):
    if not ok:
        raise ValueError(message)


class ReleasedQeOperationWords:
    def __init__(self, execution, source, node, rank, *, fragment=0, expert_ids=None):
        require(re.fullmatch(r'L\d+\.I\d+', node) is not None, 'actual source node required')
        require(type(rank) is int and 0 <= rank < 4, 'TP4 rank')
        require(source.root.resolve().name == API.SNAPSHOT, 'released checkpoint required')
        instruction = execution.source.nodes[node]['instruction']
        unit = instruction['unit']
        qe = unit == 3 and instruction['qe_mode'] == 0
        me = unit == 1 and instruction['me_wsrc'] == 0
        require(qe or me, 'only source-weight mode0 QE or weight-source ME')
        slot = execution.source.bindings[node]['selector_slot']
        if slot is not None:
            require(expert_ids is not None, 'actual captured six EIDs required; no catalogue/default expert')
        else:
            require(expert_ids is None, 'unexpected expert selection for static source')
        # IDs come from the caller's accepted native EID publication and lease.
        # SourceExecution validates six distinct ascending IDs; never enumerate
        # the catalogue or select an expert without the supplied capture.
        kw = {} if expert_ids is None else {'expert_ids': expert_ids}
        resolved = execution.source.resolve(node, rank, **kw)
        dispatch = execution.dispatch(node, rank, **kw)
        require(dispatch['source_dispatch_bound'], 'canonical selected dispatch required')
        matrices = resolved['fragments']
        require(type(fragment) is int and 0 <= fragment < len(matrices), 'selected fragment')
        require(len(matrices) == len(dispatch['fragments']), 'dispatch fragment coverage')
        rows = instruction['qe_nout'] if qe else instruction['me_nout']
        K = instruction['qe_nb']*32 if qe else instruction['me_k']*(1 << instruction.get('me_split',0))
        require(sum(f['matrix']['rows'] for f in matrices) == rows and
                all(f['matrix']['K'] == K for f in matrices), 'full literal source dimensions')
        self.matrix = matrices[fragment]['matrix']
        self.selected = dispatch['fragments'][fragment]
        digest = hashlib.sha256(json.dumps(self.matrix, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        require(self.selected['source_matrix_sha256'] == digest and self.selected['rank'] == rank and
                self.selected['stage'] == self.matrix['stage'], 'selected matrix identity')
        fmt, conversion = self.matrix['format'], self.matrix['conversion']
        require(self.matrix['compiled_NP'] == 2417 and fmt in ('fp4','fp8','bf16'),
                'source S81 codec required')
        require(conversion in ('native','FP8+UE8M0->BF16_RNE'), 'unsupported source conversion')
        if qe:
            require(conversion == 'native' and fmt == ('fp4' if instruction.get('qe_fp4',0) else 'fp8'),
                    'literal QE format mismatch')
        else:
            require(fmt == 'bf16', 'native ME format required')
        dtype = 'F8_E4M3' if conversion != 'native' or fmt == 'fp8' else ('I8' if fmt == 'fp4' else 'BF16')
        _, _, descriptor = source.descriptor(self.matrix['tensor'])
        require(descriptor['dtype'] == dtype, 'released native code dtype')
        scale = self.matrix['source_scale_tensor']
        if dtype != 'BF16':
            require(scale is not None, 'released scale source missing')
            _, _, descriptor = source.descriptor(scale)
            require(descriptor['dtype'] == 'F8_E8M0',
                    'released source scale dtype')
        self.expert_ids = None if expert_ids is None else tuple(expert_ids)
        self.source, self.rank = source, rank
        self.pairs = tuple(sorted({p[1] for p in self.matrix['plans']}))
        self.source_matrix_sha256 = digest

    def read(self, stage, rank, macro, physical_row):
        require(all(type(v) is int for v in (stage, rank, macro, physical_row)), 'integer address')
        require(stage == self.matrix['stage'] and rank == self.rank and
                0 <= macro < 4*2417 and macro//4 in self.pairs and 0 <= physical_row < 4096,
                'request outside selected QE source')
        require(self.matrix['conversion'] == 'native',
                'native source transform required; use raw_chunk, no host BF16 conversion')
        word = API.matrix_word(self.matrix, self.source, rank, macro, physical_row)
        require(type(word) is int and 0 <= word < 1 << 274, 'native word width')
        return word

    def raw_chunk(self, row, k, count):
        """Retained raw codes/BF16 and addressed scales, no dequantization.

        The native consumer applies the declared conversion/rounding. Coordinates
        are local to the selected fragment, not a guessed global tensor slice.
        """
        require(all(type(v) is int for v in (row,k,count)) and
                0 <= row < self.matrix['rows'] and 1 <= count <= 32 and
                0 <= k and k+count <= self.matrix['K'], 'raw source chunk bounds')
        homes = [API.M.physical_address(self.matrix,self.rank,row,k+j) for j in range(count)]
        sr, sk = homes[0]['source_row'], homes[0]['source_col']
        require(all(h['source_row']==sr and h['source_col']==sk+j for j,h in enumerate(homes)),
                'raw chunk crosses source slice')
        dtype = self.source.descriptor(self.matrix['tensor'])[2]['dtype']
        if dtype == 'I8':
            offset, end = sk//2, (sk+count+1)//2
            codes = self.source.raw(self.matrix['tensor'], sr*self.source.descriptor(self.matrix['tensor'])[2]['shape'][1]+offset, end-offset)
            first_nibble = sk % 2
        else:
            width = 2 if dtype == 'BF16' else 1
            cols = self.source.descriptor(self.matrix['tensor'])[2]['shape'][1]
            codes = self.source.raw(self.matrix['tensor'], (sr*cols+sk)*width, count*width)
            first_nibble = None
        scales = []
        if self.matrix['source_scale_tensor'] is not None:
            seen = set()
            for h in homes:
                scale_row = sr if dtype == 'I8' else sr//32
                scale_col = h['source_col']//32
                if (scale_row,scale_col) not in seen:
                    seen.add((scale_row,scale_col))
                    scales.append(dict(row=scale_row,col=scale_col,
                        bits=self.source.element(self.matrix['source_scale_tensor'],scale_row,scale_col)))
        return dict(source_matrix_sha256=self.source_matrix_sha256,selected=self.selected,
                    source_tensor=self.matrix['tensor'],source_row=sr,source_col=sk,count=count,
                    source_homes=homes,source_scale_tensor=self.matrix['source_scale_tensor'],
                    captured_expert_ids=self.expert_ids,
                    dtype=dtype,codes=codes,first_nibble=first_nibble,scales=scales,
                    conversion=self.matrix['conversion'],native_arithmetic_required=True)

    __call__ = read


def main():
    from dsrom_s81_execution_binding import CanonicalS81Execution
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fd', type=int, required=True)
    p.add_argument('--owner', type=Path, required=True)
    p.add_argument('--checkpoint', type=Path, required=True)
    p.add_argument('--node', required=True)
    p.add_argument('--rank', type=int, required=True)
    p.add_argument('--fragment', type=int, default=0)
    p.add_argument('--expert-ids', default='')
    a = p.parse_args()
    expert_ids = [int(x) for x in a.expert_ids.split(',')] if a.expert_ids else None
    source = API.Checkpoint(a.checkpoint)
    try:
        provider = ReleasedQeOperationWords(CanonicalS81Execution(a.owner), source,
                                             a.node, a.rank, fragment=a.fragment, expert_ids=expert_ids)
        with socket.socket(fileno=a.fd) as connection:
            return 0 if serve_connection(connection, provider) else 1
    finally:
        source.close()

if __name__ == '__main__':
    raise SystemExit(main())
