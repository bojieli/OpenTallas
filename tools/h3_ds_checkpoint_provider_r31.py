"""Add source-declared zero destinations and released BF16 row views to r30.

Data-only provider: no operator arithmetic and no inferred FP8->BF16 conversion.
The r30 finite addressing, leases, journals and reverse receipts remain in force.
"""
import math
import numpy as np
import h3_ds_checkpoint_provider_r30 as B


class Provider(B.Provider):
    def weight_view(self, name, required, owned, spec):
        if name != 'weight' or required.get('format') != 'bf16':
            return super().weight_view(name, required, owned, spec)
        tensor = required['logical_tensor']
        if not isinstance(tensor, str):
            raise NotImplementedError('accepted expert descriptor required')
        rows = required['row_intervals'][owned['rank']]
        if rows != owned['row_interval']:
            raise ValueError('source BF16 row ownership')
        value, dtype = self.checkpoint.tensor(tensor, rows=rows)
        if dtype != 'BF16':
            raise NotImplementedError('non-BF16 payload needs source conversion/K-view proof: ' + tensor)
        if list(value.shape) != spec['shape'] or value.dtype != B.DTYPES[spec['dtype']]:
            raise ValueError('exact BF16 source row shape/type; no truncation or reshape')
        return value

    def _read_one(self, op, owned, key, bindings, generation, collective=None):
        zeros = {name: value for name, value in bindings.items()
                 if value['kind'] == 'zero_initial_partial_destination'}
        for name, required in zeros.items():
            spec = self.native['templates'][key]['providers'][name]
            if (spec['dtype'] != 'F32' or math.prod(spec['shape']) != required['full_elements']
                    or required['new_version'] not in {w['version'] for w in op['writes']}):
                raise ValueError('source-declared zero destination extent/version/type')
        # Keep all existing source reads/lease registration and errors unchanged.
        result = super()._read_one(op, owned, key,
                                  {n: v for n, v in bindings.items() if n not in zeros},
                                  generation, collective)
        for name, required in zeros.items():
            spec = self.native['templates'][key]['providers'][name]
            value = np.zeros(spec['shape'], dtype=B.DTYPES[spec['dtype']])
            value.flags.writeable = False
            result[name] = dict(field=name, rank=owned['rank'], generation=generation,
                                kind=required['kind'], source_binding=required,
                                data=value, provenance_certified=True,
                                initialization_bytes=value.nbytes,
                                initialization_cost='source-defined software data; native store/service cost remains positive/unmeasured')
        return result


def create_provider(manifest, native_program, bounded_dispatch, residence_homes):
    return Provider(manifest, native_program, bounded_dispatch, residence_homes)
