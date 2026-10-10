import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import config
from init import route, tunnel


class PackagedConfigTests(unittest.TestCase):
    def setUp(self):
        original_path = config.config._config_path
        original_contents = original_path.read_bytes()
        self.addCleanup(original_path.write_bytes, original_contents)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        (self.folder / 'config.yaml').write_text(
            'v: 8.8\nrouteConfig: sample-route.txt\n'
            'libimobiledeviceDir: libimobiledevice\nimageDir: DeveloperDiskImage\n',
            encoding='utf-8',
        )
        self.frozen = patch.object(sys, 'frozen', True, create=True)
        self.executable = patch.object(sys, 'executable', str(self.folder / 'ZjuRun.exe'))
        self.frozen.start()
        self.executable.start()
        self.addCleanup(self.frozen.stop)
        self.addCleanup(self.executable.stop)

    def test_reads_config_beside_exe(self):
        self.assertEqual(config.Config().v, 8.8)

    def test_saves_config_beside_exe(self):
        settings = config.Config()
        settings.v = 9.9
        settings.save()
        self.assertIn('v: 9.9', (self.folder / 'config.yaml').read_text(encoding='utf-8'))

    def test_route_is_loaded_beside_exe_from_another_working_directory(self):
        settings = config.Config()
        (self.folder / 'sample-route.txt').write_text('route content', encoding='utf-8')
        previous = Path.cwd()
        elsewhere = self.folder / 'elsewhere'
        elsewhere.mkdir()
        try:
            os.chdir(elsewhere)
            with patch.object(config, 'config', settings), patch.object(route.route, 'parse_route', return_value=['ok']) as parse:
                self.assertEqual(route.get_route(), ['ok'])
                parse.assert_called_once_with('route content')
        finally:
            os.chdir(previous)

    def test_absolute_route_path_is_preserved(self):
        settings = config.Config()
        selected = self.folder / 'chosen.txt'
        selected.write_text('selected route', encoding='utf-8')
        settings.routeConfig = str(selected)
        with patch.object(config, 'config', settings), patch.object(route.route, 'parse_route', return_value=['ok']) as parse:
            self.assertEqual(route.get_route(), ['ok'])
            parse.assert_called_once_with('selected route')


class TunnelLaunchTests(unittest.TestCase):
    def launch(self, frozen, udid):
        process = Mock()
        process.stdout = io.StringIO('fd00::1 12345\n')
        process.poll.return_value = None
        with patch.object(sys, 'frozen', frozen, create=True), patch.object(tunnel.subprocess, 'Popen', return_value=process) as popen:
            result = tunnel.start_tunnel_for_udid(udid)
        self.assertEqual(result, (process, 'fd00::1', 12345))
        return popen.call_args.args[0]

    def test_frozen_tunnel_uses_cli_dispatch_instead_of_reopening_gui(self):
        self.assertEqual(self.launch(True, 'device-1'), [
            sys.executable, '--pmd3', 'lockdown', 'start-tunnel', '--script-mode', '--udid', 'device-1',
        ])

    def test_source_tunnel_keeps_python_module_command(self):
        self.assertEqual(self.launch(False, None), [
            sys.executable, '-m', 'pymobiledevice3', 'lockdown', 'start-tunnel', '--script-mode',
        ])


if __name__ == '__main__':
    unittest.main()
