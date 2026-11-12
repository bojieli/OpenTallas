"""KW-FIX-45 11-12: face-window notes carry Python list reprs ("[72.38, 0.0, ...]"); inside a Tcl "..." puts the brackets are
command substitution (QC: invalid command name "72.38399999999999,"). The note must be escaped."""
import subprocess
import landing_place as LP


def test_tcl_q_escapes_brackets_quotes_dollar_backslash():
    assert LP._tcl_q('a [1, 2] "x" $y \\z') == 'a \\[1, 2\\] \\"x\\" \\$y \\\\z'


def test_generated_puts_line_parses_and_prints_the_note_in_tclsh():
    note = "u_cland_fstart_cws1_o moved 10.53 um along/off face S: [72.38399999999999, 0.0, 81.024, 8.1] -> [1.0, 2.0]"
    line = f'puts "OT_CLAND face-window {LP._tcl_q(note)}"'
    out = subprocess.run(["tclsh"], input=line + "\n", capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "OT_CLAND face-window " + note
