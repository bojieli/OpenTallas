"""Read literal ORFS options from generated kit arrays without executing Bash."""
import shlex


def parse(text):
    lexer = shlex.shlex(text, posix=True, punctuation_chars='()')
    lexer.whitespace_split = True
    tokens = list(lexer)
    if tokens.count('EXTRA=') > 1 or any(
            token == 'EXTRA+=' or token.startswith('EXTRA[') for token in tokens):
        raise ValueError('kit EXTRA must have one literal assignment without mutations')
    if 'EXTRA=' in tokens:
        index = tokens.index('EXTRA=') + 1
        if index < len(tokens) and tokens[index] == '()':
            return {}
        if index >= len(tokens) or tokens[index] != '(':
            raise ValueError('kit EXTRA must be a literal array')
        words = []
        for token in tokens[index + 1:]:
            if token == ')':
                break
            words.append(token)
        else:
            raise ValueError('unterminated kit EXTRA array')
    else:
        # Compatibility with historical diagnostic argument fragments.
        words = tokens
    result = {}
    for index, token in enumerate(words):
        if token != '--orfs-var':
            continue
        if index + 1 >= len(words) or '=' not in words[index + 1]:
            raise ValueError('kit --orfs-var requires a literal NAME=value')
        name, value = words[index + 1].split('=', 1)
        if name in result and result[name] != value:
            raise ValueError('conflicting kit ORFS variable: ' + name)
        result[name] = value
    return result
