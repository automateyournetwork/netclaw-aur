import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('launcher', Path(__file__).with_name('launcher.py'))
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.package = self.root / 'package'
        self.source = self.package / 'source'
        self.source.mkdir(parents=True)
        (self.source / 'script').write_text('original')
        (self.source / 'script').chmod(0o755)
        self.workspace = self.root / 'workspace'
        self.release('one')

    def release(self, revision):
        (self.package / 'manifest.json').write_text(json.dumps(launcher.manifest(self.source, revision)))

    def sync(self, explicit=False):
        launcher.sync_source(self.package, self.workspace, explicit)

    def test_first_launch_copies_source_and_keeps_package_immutable(self):
        self.sync()
        self.assertEqual((self.workspace / 'script').read_text(), 'original')
        self.assertEqual(self.workspace.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.workspace / 'script').stat().st_mode & 0o777, 0o755)
        self.assertFalse((self.source / launcher.STATE).exists())

    def test_foreign_workspace_is_preserved(self):
        self.workspace.mkdir()
        (self.workspace / '.env').write_text('private')
        with self.assertRaisesRegex(RuntimeError, 'not managed'):
            self.sync()
        self.assertEqual(list(self.workspace.iterdir()), [self.workspace / '.env'])

    def test_upgrade_needs_explicit_request(self):
        self.sync()
        (self.source / 'script').write_text('updated')
        self.release('two')
        with self.assertRaisesRegex(RuntimeError, 'Stop your NetClaw services'):
            self.sync()
        self.assertEqual((self.workspace / 'script').read_text(), 'original')

    def test_upgrade_preserves_credentials_and_generated_environments(self):
        self.sync()
        (self.workspace / '.env').write_text('private')
        (self.workspace / '.venv').mkdir()
        (self.workspace / '.venv/generated').write_text('keep')
        (self.source / 'script').write_text('updated')
        (self.source / 'new').write_text('added')
        self.release('two')
        self.sync(True)
        self.assertEqual((self.workspace / '.env').read_text(), 'private')
        self.assertEqual((self.workspace / '.venv/generated').read_text(), 'keep')
        self.assertEqual((self.workspace / 'script').read_text(), 'updated')
        self.assertEqual((self.workspace / 'new').read_text(), 'added')
        self.sync(True)

    def test_local_edit_blocks_whole_update(self):
        self.sync()
        (self.workspace / 'script').write_text('custom')
        (self.source / 'new').write_text('new')
        (self.source / 'script').write_text('updated')
        self.release('two')
        with self.assertRaisesRegex(RuntimeError, 'locally changed'):
            self.sync(True)
        self.assertFalse((self.workspace / 'new').exists())
        self.assertEqual((self.workspace / 'script').read_text(), 'custom')

    def test_obsolete_source_removed_but_untracked_files_remain(self):
        self.sync()
        (self.workspace / 'notes').write_text('keep')
        (self.source / 'script').unlink()
        self.release('two')
        self.sync(True)
        self.assertFalse((self.workspace / 'script').exists())
        self.assertEqual((self.workspace / 'notes').read_text(), 'keep')

    def test_new_package_file_cannot_overwrite_untracked_data(self):
        self.sync()
        (self.workspace / 'new').write_text('private')
        (self.source / 'new').write_text('package')
        self.release('two')
        with self.assertRaisesRegex(RuntimeError, 'occupies'):
            self.sync(True)
        self.assertEqual((self.workspace / 'new').read_text(), 'private')

    def test_symlinked_workspace_is_preserved(self):
        self.workspace.symlink_to(self.source, target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, 'symlinked workspace'):
            self.sync()

    def test_symlinked_parent_cannot_write_outside_workspace(self):
        self.sync()
        (self.source / 'nested').mkdir()
        (self.source / 'nested/new').write_text('package')
        outside = self.root / 'outside'
        outside.mkdir()
        (self.workspace / 'nested').symlink_to(outside, target_is_directory=True)
        self.release('two')
        with self.assertRaisesRegex(RuntimeError, 'symlinked workspace directory'):
            self.sync(True)
        self.assertFalse((outside / 'new').exists())

    def test_failed_update_rolls_back_replaced_source(self):
        self.sync()
        (self.source / 'script').write_text('updated')
        self.release('two')
        with patch.object(launcher, 'write_state', side_effect=OSError('disk full')):
            with self.assertRaisesRegex(OSError, 'disk full'):
                self.sync(True)
        self.assertEqual((self.workspace / 'script').read_text(), 'original')
        self.assertEqual(json.loads((self.workspace / launcher.STATE).read_text())['revision'], 'one')


if __name__ == '__main__':
    unittest.main()
