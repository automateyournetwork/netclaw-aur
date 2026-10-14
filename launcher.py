"""Launch a packaged NetClaw snapshot in a private, writable user workspace."""

import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile

PACKAGE = Path('/usr/share/netclaw')
STATE = '.netclaw-package.json'


def describe(path):
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode):
        return {'link': os.readlink(path)}
    if not stat.S_ISREG(info.st_mode):
        raise RuntimeError(f'Expected a source file: {path}')
    with path.open('rb') as handle:
        digest = hashlib.file_digest(handle, 'sha256').hexdigest()
    return {'sha256': digest, 'mode': stat.S_IMODE(info.st_mode)}


def manifest(source, revision):
    files = {}
    for path in sorted(source.rglob('*')):
        if path.is_symlink():
            if not path.resolve().is_relative_to(source.resolve()):
                raise RuntimeError(f'Source link escapes the package: {path}')
        elif path.is_dir():
            continue
        files[path.relative_to(source).as_posix()] = describe(path)
    return {'revision': revision, 'files': files}


def safe_path(root, relative):
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise RuntimeError(f'Unsafe source path: {relative}')
    target = root / path
    for parent in target.parents:
        if parent == root:
            break
        if parent.is_symlink():
            raise RuntimeError(f'Preserving symlinked workspace directory: {parent}')
    return target


def write_state(path, value):
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(value, handle, sort_keys=True)
        handle.write('\n')
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def sync_source(package, workspace, explicit=False):
    source = package / 'source'
    current = json.loads((package / 'manifest.json').read_text())
    if workspace.is_symlink():
        raise RuntimeError(f'Preserving symlinked workspace: {workspace}')
    if not workspace.exists():
        with tempfile.TemporaryDirectory(prefix='.netclaw-init-', dir=workspace.parent) as temporary:
            staged = Path(temporary) / 'workspace'
            shutil.copytree(source, staged, symlinks=True)
            staged.chmod(0o700)
            write_state(staged / STATE, current)
            staged.rename(workspace)
        return

    state = workspace / STATE
    if state.is_symlink() or not state.is_file():
        raise RuntimeError(f'Workspace is not managed by this package; leaving it untouched: {workspace}')
    previous = json.loads(state.read_text())
    if current['revision'] == previous['revision']:
        return
    if not explicit:
        raise RuntimeError('The package source has changed. Stop your NetClaw services, then run '
                           '`netclaw --sync-source` and `netclaw install` to review component updates.')

    # Preflight the entire change before touching anything. Credentials and
    # generated component environments are not in this tracked-file list.
    old_files, new_files = previous['files'], current['files']
    changed = [name for name in sorted(old_files.keys() | new_files.keys())
               if old_files.get(name) != new_files.get(name)]
    for name in changed:
        target = safe_path(workspace, name)
        exists = target.exists() or target.is_symlink()
        expected = old_files.get(name)
        if expected is not None:
            if not exists or describe(target) != expected:
                raise RuntimeError(f'Preserving a locally changed source file: {target}')
        elif exists:
            raise RuntimeError(f'Preserving a file that occupies a new package path: {target}')

    # Keep backups until every source replacement and the state write succeed.
    # An interrupted update retains this private recovery directory.
    transaction = Path(tempfile.mkdtemp(prefix='.netclaw-update-', dir=workspace.parent))
    applied = []
    remove_transaction = False
    try:
        for name in changed:
            target = safe_path(workspace, name)
            backup = transaction / 'old' / name
            if target.exists() or target.is_symlink():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup, follow_symlinks=False)
            applied.append(name)
            if name in new_files:
                staged = transaction / 'new' / name
                staged.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source / name, staged, follow_symlinks=False)
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(staged, target)
            else:
                target.unlink()
        write_state(state, current)
        remove_transaction = True
    except BaseException:
        try:
            for name in reversed(applied):
                target = safe_path(workspace, name)
                backup = transaction / 'old' / name
                if backup.exists() or backup.is_symlink():
                    os.replace(backup, target)
                else:
                    target.unlink(missing_ok=True)
            remove_transaction = True
        except BaseException as recovery_error:
            raise RuntimeError(f'Update recovery needs attention; backups are in {transaction}') from recovery_error
        raise
    finally:
        if remove_transaction:
            shutil.rmtree(transaction)


def main():
    args = sys.argv[1:]
    if args in (['--help'], ['-h']):
        print('NetClaw\n\n'
              '  netclaw                 Open the interactive menu\n'
              '  netclaw install         Choose runtime and components; configure credentials\n'
              '  netclaw install --help  Show upstream installer options\n'
              '  netclaw --sync-source   Update unchanged workspace source after a package upgrade\n\n'
              'Package installation does not configure credentials or start services.\n'
              'Other arguments are passed to the upstream NetClaw command.')
        return
    if os.geteuid() == 0:
        raise RuntimeError('Run NetClaw as your desktop user, without sudo.')
    os.umask(0o077)
    data = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
    if not data.is_absolute():
        raise RuntimeError('XDG_DATA_HOME must be an absolute path.')
    data.mkdir(parents=True, exist_ok=True)
    workspace = data / 'netclaw'
    with (data / '.netclaw-package.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        sync_source(PACKAGE, workspace, explicit=args == ['--sync-source'])
    if args == ['--sync-source']:
        print('NetClaw workspace source is current. Run `netclaw install` to review component updates.')
        return
    if args[:1] == ['install']:
        command = [str(workspace / 'scripts/install.sh'), *args[1:]]
    else:
        command = [str(workspace / 'scripts/netclaw'), *args]
    os.chdir(workspace)
    os.execv('/bin/bash', ['bash', *command])


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print(f'netclaw: {error}', file=sys.stderr)
        sys.exit(1)
