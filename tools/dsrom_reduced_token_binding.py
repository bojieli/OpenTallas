#!/usr/bin/env python3
"""Read the existing reduced-system compiler output without running preparation.

Caller feedback supplies generated input tokens. Cached expected outputs are
comparison data only. This is a source lookup, not context-restore completion,
write visibility, a stage allocator, or an S82 program compiler.
"""
import argparse
import json
import re
from pathlib import Path


def words(path, width):
    out = []
    for line in path.read_text().splitlines():
        line = line.split('//', 1)[0].strip()
        if not line:
            continue
        for token in line.split():
            if not re.fullmatch('[0-9a-fA-F]+', token):
                raise ValueError(f'non-dense hex image: {path}')
            value = int(token, 16)
            if value >= 1 << width:
                raise ValueError(f'word exceeds {width} bits: {path}')
            out.append(value)
    return tuple(out)


class CachedReducedTokenBinding:
    """Prepared sys_* token and program lookup for the actual caller adapter."""

    NPMAX, SMAX = 8, 16  # tb_dsrom_system / hdc_program_v41_array contract

    def __init__(self, scratch, name):
        if not re.fullmatch(r'sys_[a-z0-9_]+', name):
            raise ValueError('invalid reduced configuration name')
        scratch = Path(scratch)
        self.prep = json.loads((scratch / f'prep_{name}.json').read_text())
        if self.prep['config_name'] != name:
            raise ValueError('prepared configuration name mismatch')
        c = self.prep['config']
        self.users, self.plen, self.ngen = c['users'], c['plen'], c['ngen']
        self.steps = self.plen + self.ngen - 1
        if not (1 <= self.users <= 8 and 1 <= self.plen <= self.NPMAX
                and self.ngen >= 1 and self.steps <= self.SMAX):
            raise ValueError('unsupported reduced token extent')
        self.prompts = self.prep['golden_prompts']
        self.generated = self.prep['golden_generated']
        self.npr = len(self.prompts)
        if not self.npr or len(self.generated) != self.npr:
            raise ValueError('missing cached comparison sequences')
        if not self.prep['isa_pipeline'] or not all(
            r['logits_bit_exact_every_step'] and r['argmax_and_value_every_step']
            for r in self.prep['isa_pipeline']
        ):
            raise ValueError('prepared ISA pipeline is not exact')
        self.img = scratch / f'cfg_{name}'
        self.prompt_words = words(self.img / 'prompts.hex', 16)
        self.expect_words = words(self.img / 'expect_tokens.hex', 16)
        if (len(self.prompt_words) != self.npr * self.NPMAX
                or len(self.expect_words) != self.npr * self.SMAX):
            raise ValueError('cached token image extent mismatch')
        for p, (prompt, generated) in enumerate(zip(self.prompts, self.generated)):
            if len(prompt) != self.plen or len(generated) != self.ngen:
                raise ValueError('cached sequence extent mismatch')
            if list(self.prompt_words[p*self.NPMAX:p*self.NPMAX+self.plen]) != prompt:
                raise ValueError('prompt image differs from prepared source')
            start = p*self.SMAX + self.plen - 1
            if list(self.expect_words[start:start+self.ngen]) != generated:
                raise ValueError('expected generated image differs from cached sequence')
        svh = (scratch / f'svh_{name}.svh').read_text()
        nodes = re.search(r'\bNODES\s*=\s*(\d+)', svh)
        npr = re.search(r'\bNPR\s*=\s*(\d+)', svh)
        if not nodes or not npr or int(npr[1]) != self.npr:
            raise ValueError('missing or inconsistent prepared array schedule')
        self.nodes = int(nodes[1])
        self.stage_words = tuple(words(self.img / f'prog_stage{s:02d}.hex', 1536)
                                 for s in range(self.nodes))
        if any(not p for p in self.stage_words):
            raise ValueError('empty prepared stage program')
        # Pass the compiler-produced configuration verbatim to the actual top.
        self.svh = svh

    def _address(self, user, pos):
        if (type(user) is not int or type(pos) is not int
                or not 0 <= user < self.users or not 0 <= pos < self.steps):
            raise ValueError('unbound user/position')
        return user % self.npr

    def expected_output(self, user, pos):
        return self.expect_words[self._address(user, pos)*self.SMAX + pos]

    def input_token(self, user, pos, *, previous_completion=None):
        p = self._address(user, pos)
        if pos < self.plen:
            return self.prompt_words[p*self.NPMAX + pos]
        # Explicit accepted previous completion (user, position, token).
        # Never substitute the cached golden for an absent hardware completion.
        if (not isinstance(previous_completion, tuple) or len(previous_completion) != 3
                or previous_completion[:2] != (user, pos-1)
                or type(previous_completion[2]) is not int
                or not 0 <= previous_completion[2] < 65536):
            raise ValueError('generated launch requires matching actual previous completion')
        return previous_completion[2]

    def program(self, stage):
        if type(stage) is not int or not 0 <= stage < self.nodes:
            raise ValueError('unbound reduced stage')
        return self.stage_words[stage]

    def qlist_path(self, stage):
        self.program(stage)
        path = self.img / f'qlist_stage{stage:02d}.hex'
        if not path.is_file():
            raise FileNotFoundError(path)
        return path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--scratch', type=Path, required=True)
    ap.add_argument('--name', required=True)
    a = ap.parse_args()
    b = CachedReducedTokenBinding(a.scratch, a.name)
    print(f'{a.name}: {b.nodes} reduced stages, {b.users} users, {b.steps} positions')
    for s in range(b.nodes):
        print(f'stage={s} entry=0 program_words={len(b.program(s))} qlist={b.qlist_path(s)}')
    for u in range(b.users):
        for p in range(b.steps):
            token = b.input_token(u, p) if p < b.plen else 'actual_previous_completion'
            print(f'user={u} pos={p} input={token} compare_output={b.expected_output(u,p)}')


if __name__ == '__main__':
    main()
