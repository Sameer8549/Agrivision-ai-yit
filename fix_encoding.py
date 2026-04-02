"""Fix Windows cp1252 encoding issues  -  strip all non-ASCII from Python files."""
import os

REPLACEMENTS = [
    ('\u2014', ' - '),   # em dash
    ('\u2013', '-'),     # en dash
    ('\u2192', '->'),    # right arrow
    ('\u2190', '<-'),    # left arrow
    ('\u2022', '*'),     # bullet
    ('\u00d7', 'x'),     # multiplication sign
    ('\u2500', '-'),     # box drawing horizontal
    ('\u2550', '='),     # double horizontal
    ('\u2551', '|'),     # double vertical
    ('\u2502', '|'),     # vertical
    ('\u2588', '#'),     # full block
    ('\u00bb', '>>'),
    ('\u00ab', '<<'),
    ('\u2018', "'"),     # left single quote
    ('\u2019', "'"),     # right single quote
    ('\u201c', '"'),     # left double quote
    ('\u201d', '"'),     # right double quote
    ('\u2026', '...'),   # ellipsis
    ('\u00e2', ''),      # common UTF-8 mangled chars
    ('\u2605', '*'),     # star
]

fixed_count = 0
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'node_modules']]
    for fname in files:
        if not fname.endswith('.py'):
            continue
        path = os.path.join(root, fname)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            fixed = content
            for bad, good in REPLACEMENTS:
                fixed = fixed.replace(bad, good)
            if fixed != content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(fixed)
                fixed_count += 1
                print(f'  Fixed: {path}')
        except Exception as e:
            print(f'  Error on {path}: {e}')

print(f'\nDone. Fixed {fixed_count} files.')
