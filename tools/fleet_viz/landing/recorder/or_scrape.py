import asyncio, json, re, sys
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); out = {}
        for slug in sys.argv[1:]:
            pg = await b.new_page(viewport=dict(width=1400, height=1000)); hits = []
            async def onresp(r):
                if 'frontend' in r.url and ('stat' in r.url or 'endpoint' in r.url or 'throughput' in r.url):
                    try: hits.append((r.url, (await r.text())[:20000]))
                    except Exception: pass
            pg.on('response', onresp)
            await pg.goto(f'https://openrouter.ai/{slug}/providers', wait_until='networkidle', timeout=90000); await pg.wait_for_timeout(4000)
            txt = await pg.inner_text('body')
            out[slug] = dict(text=txt, api=hits)
            await pg.close()
        await b.close()
        json.dump(out, open('/home/ubuntu/landing-scratch/rec/openrouter_raw.json', 'w'))
asyncio.run(main())
