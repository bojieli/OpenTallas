"""Build the timed-control-reset source profile for a new native head master.

Only generated copies are changed. Parallel kept reset captures add one known
delivery edge, with no local synchronizer or false path. Datapath registers run
through reset; the interface qualifies their values with its valid bits.
"""
import re


def _mask(text):
    pattern = r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"'
    return re.sub(pattern, lambda m: "".join("\n" if c == "\n" else " " for c in m[0]), text)


def _statement_end(masked, start):
    tokens = list(re.finditer(r"\bbegin\b|\bend\b|\bif\b|\belse\b|\bfor\b|\bcase\b|\bendcase\b|[();]", masked[start:]))

    def parens(i):
        assert tokens[i][0] == "("
        depth = 1
        i += 1
        while depth:
            if tokens[i][0] == "(": depth += 1
            if tokens[i][0] == ")": depth -= 1
            i += 1
        return i

    def stmt(i):
        t = tokens[i][0]
        if t == "begin":
            depth = 1
            i += 1
            while depth:
                if tokens[i][0] == "begin": depth += 1
                if tokens[i][0] == "end": depth -= 1
                i += 1
            return i
        if t == "if":
            i = stmt(parens(i + 1))
            if i < len(tokens) and tokens[i][0] == "else": i = stmt(i + 1)
            return i
        if t == "for": return stmt(parens(i + 1))
        if t == "case":
            depth = 1
            i += 1
            while depth:
                if tokens[i][0] == "case": depth += 1
                if tokens[i][0] == "endcase": depth -= 1
                i += 1
            return i
        while tokens[i][0] != ";": i += 1
        return i + 1

    last = stmt(0)
    return start + tokens[last - 1].end()


def control_data_reset(text, filename):
    """Remove only the named arithmetic payload resets, preserving controls."""
    if filename == "ot_hdc_fp32_f12.sv":
        start = text.index("module ot_hdc_fp32_add_f12 #(")
        stop = text.index("module ot_hdc_fp32_mul_f12 #(", start)
        body = text[start:stop]
        old = """        if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
        else begin
            valid_out <= u_v;
            if (u_byp) begin y <= u_code; err <= u_err; end
            else if (u_zero) begin y <= 32'd0; err <= E_NONE; end
            else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
        end"""
        new = """        if (!rst_n) valid_out <= 1'b0; else valid_out <= u_v;
        if (u_byp) begin y <= u_code; err <= u_err; end
        else if (u_zero) begin y <= 32'd0; err <= E_NONE; end
        else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
        else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end"""
        assert body.count(old) == 1, "native FP add output anchor changed"
        text = text[:start] + body.replace(old, new) + text[stop:]
    if filename == "ot_dsrom_bmul3.sv":
        old = """        if (!rst_n) begin y <= 32'd0; fault <= 1'b0; end
        else begin y <= s4_y; fault <= s4_v && s4_bad; end"""
        new = """        if (!rst_n) fault <= 1'b0; else fault <= s4_v && s4_bad;
        y <= s4_y;"""
        assert text.count(old) == 1, "native BF16 multiplier output anchor changed"
        text = text.replace(old, new)
    return text


def timed_profile(text, filename, first_tag=0):
    text = control_data_reset(text, filename)
    masked = _mask(text)
    pattern = r"always\s*@\(\s*posedge\s+clk\s+or\s+negedge\s+rst_n\s*\)"
    changes = []
    for tag, m in enumerate(re.finditer(pattern, masked), first_tag):
        end = _statement_end(masked, m.end())
        body = text[m.end():end]
        assert re.search(r"\brst_n\b", _mask(body)), (filename, tag)
        local = f"hd_rst_{tag}_n"
        prefix = (f"wire {local};\n"
                  f"    ot_s81hd_rst_capture #(.TAG({tag})) u_hd_rst_{tag} "
                  f"(.clk(clk), .rst_n_in(rst_n), .rst_n_out({local}));\n"
                  "    always @(posedge clk)")
        changes.append((m.start(), end, prefix + re.sub(r"\brst_n\b", local, body)))
    for lo, hi, replacement in reversed(changes): text = text[:lo] + replacement + text[hi:]
    return text, dict(file=filename, parallel_capture_blocks=len(changes),
                      first_tag=first_tag, next_tag=first_tag + len(changes),
                      reset_delivery_cycles=1, synchronous_consumption=True)
