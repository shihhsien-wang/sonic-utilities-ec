import os
from click.testing import CliRunner
from mock import patch

import config.main as config
from utilities_common.db import Db

class TestNtp(object):
    @classmethod
    def setup_class(cls):
        os.environ['UTILITIES_UNIT_TESTING'] = '1'

    @classmethod
    def teardown_class(cls):
        os.environ['UTILITIES_UNIT_TESTING'] = '0'

    @patch('config.main.clicommon.run_command')
    def test_ntp_server_add_del(self, mock_run):
        mock_run.return_value = ("", 0)
        runner = CliRunner()
        db = Db()
        obj = {'db': db.cfgdb}

        result = runner.invoke(config.config.commands['ntp'].commands['server'].commands['add'],
                               ['0.pool.ntp.org', '--type', 'server', '--key', '42', '--version', '4'],
                               obj=obj)
        assert result.exit_code == 0
        entry = db.cfgdb.get_entry('NTP_SERVER', '0.pool.ntp.org')
        assert entry == {'resolve_as': '0.pool.ntp.org', 'association_type': 'server', 'key_id': '42', 'version': '4'}
        mock_run.assert_called_with(['systemctl', 'restart', 'ntp-config'], display_cmd=False)

        result = runner.invoke(config.config.commands['ntp'].commands['server'].commands['del'],
                               ['0.pool.ntp.org'], obj=obj)
        assert result.exit_code == 0
        table = db.cfgdb.get_table('NTP_SERVER')
        assert '0.pool.ntp.org' not in table

    @patch('config.main.clicommon.run_command')
    def test_ntp_key_add_del(self, mock_run):
        mock_run.return_value = ("", 0)
        runner = CliRunner()
        db = Db()
        obj = {'db': db.cfgdb}

        result = runner.invoke(config.config.commands['ntp'].commands['key'].commands['add'],
                               ['42', 'theanswer', '--type', 'sha1', '--trusted', 'yes'], obj=obj)
        assert result.exit_code == 0
        entry = db.cfgdb.get_entry('NTP_AUTH', '42')
        assert entry == {'secret': 'theanswer', 'type': 'sha1', 'trusted': 'true'}

        result = runner.invoke(config.config.commands['ntp'].commands['key'].commands['del'],
                               ['42'], obj=obj)
        assert result.exit_code == 0
        table = db.cfgdb.get_table('NTP_AUTH')
        assert '42' not in table
