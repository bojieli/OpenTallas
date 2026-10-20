import sys, json, traceback
sys.path.insert(0, 'tools/ref_tile')
import gray_fifo_cdc_constraints as G
spec = json.load(open(sys.argv[1]))
try:
    r = G.lint(spec, '.')
    print('SVG_CDC_LINT PASS'); print(json.dumps(r, default=str)[:20000])
except Exception as e:
    print('SVG_CDC_LINT REFUSE', type(e).__name__, str(e)[:20000]); traceback.print_exc()
