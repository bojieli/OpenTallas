# Regional LEP r5b clock successor

The r4b actual native census passed at maximum32. Its CTS failed final clk_a TT boundary spread82.2ps against80ps, while its leaf-max balancing metric was24.65ps. No physical closure is claimed.

This successor uses clock leaf group size 12 instead of24 and18um bins instead of36um. That changes actual local clock fanout and wire lengths. It constructs balance using the existing platform placement RC option, consistent with final boundary measurement. All final TT/FF limits remain unchanged. The companion successor uses another bounded local fanout as a fallback.

Safe design checklist: source pin flops and face geometry are unchanged; existing data reach remains unchanged; native source remains exact a516fe9b1; no logic depth or payload edge changed; all40 SRAMs and storage interfaces are unchanged; outline and channels are preserved; only physical clock buffers and grouping change; reset/data ages remain unchanged and payload flops stay reset-free. Prior production-shape golden and causal witnesses are retained. No new optional validation campaign is added.
