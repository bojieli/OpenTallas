#!/usr/bin/env python3
"""Future default-off host dynamic-KV dispatch; original producer is unedited.

Pass --vectorized-dynamic-kv to opt in after the focused exactness gate. All
other arguments, static CUDA matvec, KV codecs, source images and source-order
execution belong to the unchanged existing runner. Never hotpatch a live run.
"""
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--vectorized-dynamic-kv', action='store_true')
    options, rest = parser.parse_known_args()
    import qwen_rom_dspark_oracle_gpu_w12 as original
    if options.vectorized_dynamic_kv:
        from hdc_dynamic_kv_vectorized import me_dynamic_kv

        class VectorizedDynamicKvDieMachine(original.GpuDieMachine):
            def me(self, f, dyn):
                if f['me_wsrc']:
                    return me_dynamic_kv(self, f, dyn)
                return super().me(f, dyn)

        original.GpuDieMachine = VectorizedDynamicKvDieMachine
    sys.argv = [sys.argv[0], *rest]
    return original.main()


if __name__ == '__main__':
    main()
