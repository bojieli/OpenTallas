"""Numbers for the /landing page, read from committed result files at request time (cached by mtime).

Our rates: the newest results/arch/token_path_<date>/ export (one token's, or one MTP step's, critical path,
so tok/s = 1 / latency is a PER-USER rate), cross-referenced to the newest results/arch/reprice_<date>/reprice.json.
GPU rates: results/external/registry.json (third-party; owner rule: cite the registry, never re-research).
GPU prefill: the third-party prefill citations carried in results/arch/prefill_ingest.json (the registry holds none).
Aggregate rates: no aggregate was recomputed for the 2026-10-08 design points; the newest committed aggregates
(2026-09-28, earlier design points) are returned flagged stale=True with their own per-user rate for context.
"""
import json, os, subprocess, threading
from pathlib import Path

class Landing:
    def __init__(self, repo, log=print):
        self.repo = Path(repo); self.log = log; self.lock = threading.Lock(); self.key = None; self.cache = None

    def _latest(self, pattern, must):
        c = sorted(p for p in (self.repo / 'results' / 'arch').glob(pattern) if (p / must).is_file())
        return c[-1] if c else None

    def _date(self, rel):
        try:
            out = subprocess.run(['git', '-C', str(self.repo), 'log', '-1', '--format=%cs %h', '--', rel], capture_output=True, text=True, timeout=10).stdout.split()
            return dict(date=out[0], commit=out[1]) if out else dict(date=None, commit=None)
        except Exception:
            return dict(date=None, commit=None)

    def numbers(self):
        tp = self._latest('token_path_2*', 'index.json'); rp = self._latest('reprice_2*', 'reprice.json')
        files = [tp / f for f in ('qwen_rom.json', 'ds_rom.json', 'ds_rom_mtp.json', 'hbm_ds.json', 'hbm_ds_mtp.json')] + [
            rp / 'reprice.json', self.repo / 'results/external/registry.json', self.repo / 'results/arch/prefill_ingest.json',
            self.repo / 'results/arch/v41_lanes.json', self.repo / 'results/arch/qwen3_budget.json']
        key = tuple((str(f), f.stat().st_mtime) for f in files if f.is_file())
        with self.lock:
            if key == self.key and self.cache: return self.cache
        try:
            o = self._build(tp, rp)
        except Exception as e:
            self.log('landing numbers: %r' % e); o = dict(error=str(e))
        with self.lock: self.key, self.cache = key, o
        return o

    def _build(self, tp, rp):
        rel = lambda p: str(Path(p).relative_to(self.repo))
        J = lambda p: json.load(open(p))
        rep = J(rp / 'reprice.json'); rep_date = rep.get('date')
        def ours(fname, field='headline.tok_s'):
            d = J(tp / fname); v = d
            for k in field.split('.'): v = v[k]
            h = d['headline']
            return dict(value=v, source=rel(tp / fname), field=field, date=rep_date, commit=self._date(rel(tp / fname))['commit'],
                        basis=h.get('source'), status=h.get('status'), mode=h.get('mode'), title=d.get('title'))
        reg = J(self.repo / 'results/external/registry.json'); E = {e['id']: e for e in reg['entries']}
        def ext(eid, path, label):
            v = E[eid]['value']
            for k in path: v = v[k]
            e = E[eid]
            return dict(value=v, source='results/external/registry.json', field=f'entries[id={eid}].value' + ''.join(f'.{k}' for k in path),
                        date=e.get('date') or reg.get('date'), title=e['title'], label=label, url=e.get('url'))
        pre = J(self.repo / 'results/arch/prefill_ingest.json')['citations']
        lanes = J(self.repo / 'results/arch/v41_lanes.json')['energy']['1048576']
        qb = J(self.repo / 'results/arch/qwen3_budget.json')['power_production']['scenarios']['B_proposed_production']
        lanes_d = self._date('results/arch/v41_lanes.json'); qb_d = self._date('results/arch/qwen3_budget.json')
        def stale(v, src, field, d, note): return dict(value=v, source=src, field=field, date=d['date'], commit=d['commit'], stale=True, note=note)
        ds_note = 'earlier V4.1 array design point (per-user then 7,049 AR / 15,890 MTP tok/s); not recomputed for the S81 1,792-pair design'
        nim = 20000 / 0.4032   # NIM: 20,000 input tokens, TTFT 403.2 ms on H100 -> prompt tokens per second
        out = dict(
            generated_from=dict(token_path=rel(tp), reprice=rel(rp), reprice_date=rep_date, registry_date=reg.get('date')),
            label='analytical',
            designs=[
                dict(id='qwen_rom', name='Qwen ROM', model='Qwen3-8B', context='8K', mode='AR',
                     per_user=ours('qwen_rom.json'),
                     aggregate=stale(qb['rom']['batch128']['tokens_s'], 'results/arch/qwen3_budget.json',
                                     'power_production.scenarios.B_proposed_production.rom.batch128.tokens_s', qb_d,
                                     'earlier two-reticle package at 128 users (per-user then 10,874 tok/s); not recomputed for the current die')),
                dict(id='ds_rom', name='DS ROM array', model='DeepSeek-V4.1 Flash', context='1M', mode='AR / MTP',
                     per_user=ours('ds_rom.json'), per_user_mtp=ours('ds_rom_mtp.json'),
                     aggregate=stale(lanes['sat1024']['rom']['aggregate_tokens_s'], 'results/arch/v41_lanes.json', 'energy.1048576.sat1024.rom.aggregate_tokens_s', lanes_d, ds_note + '; 1,024 users'),
                     aggregate_mtp=stale(lanes['sat1024_mtp']['rom']['aggregate_tokens_s'], 'results/arch/v41_lanes.json', 'energy.1048576.sat1024_mtp.rom.aggregate_tokens_s', lanes_d, ds_note + '; 1,024 users')),
                dict(id='hbm_ds', name='HBM accelerator', model='DeepSeek-V4.1 Flash', context='1M', mode='AR / MTP',
                     per_user=ours('hbm_ds.json'), per_user_mtp=ours('hbm_ds_mtp.json'),
                     aggregate=stale(lanes['sat1024']['hbm']['aggregate_tokens_s'], 'results/arch/v41_lanes.json', 'energy.1048576.sat1024.hbm.aggregate_tokens_s', lanes_d, 'earlier HBM comparator design point; 1,024 users'),
                     aggregate_mtp=stale(lanes['sat1024_mtp']['hbm']['aggregate_tokens_s'], 'results/arch/v41_lanes.json', 'energy.1048576.sat1024_mtp.hbm.aggregate_tokens_s', lanes_d, 'earlier HBM comparator design point; 1,024 users')),
            ],
            gpu=dict(
                qwen=dict(per_user=ext('new:dflash_table3_table4', ['qwen3_8b_b200_c1_math500', 'dflash_tok_s'], 'B200 + DFlash speculative decoding, SGLang, concurrency 1, MATH-500 (tau 8.01)'),
                          per_user_ar=ext('new:dflash_table3_table4', ['qwen3_8b_b200_c1_math500', 'ar_tok_s'], 'B200, SGLang, concurrency 1, no speculation'),
                          aggregate=None,
                          prefill=dict(value=round(nim, 1), source='results/arch/prefill_ingest.json', field='citations.nim_llama8b (20,000 tokens / 0.4032 s TTFT)',
                                       date=self._date('results/arch/prefill_ingest.json')['date'], title=pre['nim_llama8b']['what'], url=pre['nim_llama8b']['url'],
                                       label='Llama-3.1-8B FP8, one H100, TTFT at 20K input tokens (8B-class proxy)')),
                ds=dict(per_user=ext('roofline:lmsys_v4pro', ['tok_s'], 'DeepSeek-V4-Pro + DSpark, 8 x B300 TP8, batch 1 (V4-Pro: 49B active vs Flash 13B)'),
                        per_user_flash=ext('nvls:lmsys_dsv4_day0', ['h200_v4flash_tp4_tok_s', '4K'], 'DeepSeek-V4-Flash, 4 x H200 TP4, single batch, 4K context'),
                        aggregate=ext('new:infx_dsv4pro_b200_vs_b300', ['b200_tok_s_chip', '222'], 'B200 tok/s per chip at 222 tok/s per user (V4-Pro, agentic AgentX scenario)'),
                        prefill=dict(value=26156, source='results/arch/prefill_ingest.json', field='citations.lmsys_gb200_dsv3',
                                     date=self._date('results/arch/prefill_ingest.json')['date'], title=pre['lmsys_gb200_dsv3']['what'], url=pre['lmsys_gb200_dsv3']['url'],
                                     label='DeepSeek-V3/R1 prefill per GB200 GPU, 2,000-token inputs (FP8 attention, NVFP4 MoE)'))),
        )
        return out
