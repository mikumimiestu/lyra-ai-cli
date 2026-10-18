"""Create a pip-installable source archive without writing to the CLI checkout."""
import ast
import gzip
import io
from pathlib import Path
import sys
import tarfile

root = Path(__file__).resolve().parents[2]
syntax = ast.parse((root / 'setup.py').read_text(encoding='utf-8'))
setup_call = next(node.value for node in syntax.body if isinstance(node, ast.Expr)
                  and isinstance(node.value, ast.Call)
                  and isinstance(node.value.func, ast.Name) and node.value.func.id == 'setup')
settings = {item.arg: ast.literal_eval(item.value) for item in setup_call.keywords}
version = (root / 'version.txt').read_text().strip()
if settings['version'] != version:
    raise ValueError('setup.py and version.txt must declare the same CLI version')
folder = f"{settings['name'].replace('-', '_')}-{version}"
files = ['setup.py', 'README.md', 'version.txt'] + [name + '.py' for name in settings['py_modules']]
archive = io.BytesIO()
with tarfile.open(fileobj=archive, mode='w') as package:
    for filename in files:
        contents = (root / filename).read_bytes()
        info = tarfile.TarInfo(f'{folder}/{filename}')
        info.size = len(contents)
        info.mode = 0o644
        package.addfile(info, io.BytesIO(contents))
sys.stdout.buffer.write(gzip.compress(archive.getvalue(), mtime=0))
