import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from meta_from_extension import find_latest_export


class ExportDiscoveryTests(unittest.TestCase):
    def test_current_and_legacy_names_select_newest(self):
        with tempfile.TemporaryDirectory() as home:
            downloads = Path(home) / 'Downloads'
            downloads.mkdir()
            legacy = downloads / 'meta_export_legacy.json'
            current = downloads / 'meta_demo_20261029_20261028.json'
            unrelated = downloads / 'other.json'
            for index, path in enumerate([legacy, current, unrelated]):
                path.write_text('{}')
                os.utime(path, (100 + index, 100 + index))
            with patch('os.path.expanduser', return_value=home):
                self.assertEqual(Path(find_latest_export()), current)

    def test_missing_downloads_returns_none(self):
        with tempfile.TemporaryDirectory() as home, patch('os.path.expanduser', return_value=home):
            self.assertIsNone(find_latest_export())


if __name__ == '__main__':
    unittest.main()
