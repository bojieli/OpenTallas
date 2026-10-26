KV boot-age bounds, current reach405 plan

PATH-KV approved FIA 127->255 and V-port RT31->63 at21:21 PDT. Both cfg fields already hold8bits. The pair controller changes only a supported-range comparator. The V-port extends its two1bit slot/select pipelines32edges each:64FF/master,1024FF across16ports. Existing tap indices and output dates stay identical:0added token/boot cycles. DQ remains15, deepest slot tap79<255.

Actual current FIA131/RT50 and maximum representable FIA255/RT63 pass edge-for-edge lockstep against fixed-age production reference RTL. Both request/response data and clean faults are checked. The slot-tap and control-calendar mutants fail. FIA has only0as an invalid representable value at bound255; the bench tests it once. Existing 19-word boot-age encoding and generated plan variant are regenerated coherently. New source-bound params must be reflected in the next native asbuilt/bind; old physical views retain their historical bounds and do not qualify the extended range.

Run: bash tools/qwen_kv_die/kv_bootage_bench.sh OUT vport0 D=1 R=50; bash tools/qwen_kv_die/kv_bootage_bench.sh OUT pvctl0 A=131 (separate argv vport 0 / pvctl 0). Evidence is source exactness only; refreshed kits and physical closure remain due.
