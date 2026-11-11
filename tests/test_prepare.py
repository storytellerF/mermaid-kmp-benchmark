import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import prepare


class PrepareTests(unittest.TestCase):
    def test_published_artifact_without_source_revision_does_not_access_git(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = "example:library:1.2.3"
            (root / "libraries.lock.json").write_text(json.dumps({
                "cmp": {"artifact": artifact}
            }))
            output = io.StringIO()
            with patch.object(prepare, "ROOT", root), patch.object(prepare, "run") as git, contextlib.redirect_stdout(output):
                prepare.prepare()
            git.assert_not_called()
            self.assertIn(artifact, output.getvalue())
            self.assertFalse((root / ".upstream").exists())

    def test_unmarked_source_fetch_failure_still_aborts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "libraries.lock.json").write_text(json.dumps({
                "native": {"repository": "example/library", "commit": "b" * 40, "modules": ["core"]}
            }))
            def run(*args):
                if "fetch" in args:
                    raise subprocess.CalledProcessError(128, args)
                return ""
            with patch.object(prepare, "ROOT", root), patch.object(prepare, "run", side_effect=run):
                with self.assertRaises(subprocess.CalledProcessError):
                    prepare.prepare()
