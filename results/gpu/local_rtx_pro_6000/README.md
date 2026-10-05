# Local RTX PRO 6000 campaign index

Both runs used the existing `qwen-fast` endpoint and left the second endpoint
and all other GPU processes untouched. They are service observations labelled
`shared_contended`, not clean peak benchmarks or energy-attributable runs.

| Run | Disposition | 256/C1 | 2,048/C1 | 8,192/C1 | 256/C2 |
| --- | --- | ---: | ---: | ---: | ---: |
| `20260828T102214Z` | Diagnostic: all ten requests passed, but the original harness incorrectly required byte-identical `/v1/models` responses | 120.277 | 114.629 | 114.694 | 147.818 |
| `20260828T102304Z` | Governed pass: semantic endpoint identity stable; all ten requests passed | 171.342 | 180.198 | 164.876 | 142.393 |

Rates are median **per-request** completion tokens/s including TTFT and
end-of-stream overhead. The C2 row is not aggregate wave throughput.

vLLM regenerates `created` timestamps and permission IDs on every
`/v1/models` response. The corrected harness preserves the full raw snapshots
but excludes only those response-generated fields from its endpoint-stability
decision. Model ID, root checkpoint, maximum context, and permission
capabilities remained stable for both endpoints.

The substantial between-run variation is another reason not to interpret the
numbers as an intrinsic GPU or model peak. The passing run is attached to the
inverse break-even report as a separate Qwen service target; neither run is
substituted for the DeepSeek/B300 analytical comparator.
