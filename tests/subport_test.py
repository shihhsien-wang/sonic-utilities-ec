import os
import traceback
from unittest import mock

from click.testing import CliRunner

import config.main as config
import show.main as show
from utilities_common.db import Db

from mock import patch

import pytest

class TestSubport(object):
    @classmethod
    def setup_class(cls):
        print("SETUP")
        #cls.config_db_tables = {}
        #cls.app_db_tables = {}
        #cls.state_db_tables = {}
        os.environ['UTILITIES_UNIT_TESTING'] = "1"
    """
    @pytest.fixture(autouse=True)
    def basic_suite(self, get_cmd_module):
        (config, show) = get_cmd_module
        db = Db()
        config_db = db.cfgdb
        db_obj = {'config_db': config_db}
        yield (config, show, db_obj)

    @pytest.fixture(scope='class', autouse=True)
    def basic_suite(self):
        db = Db()
        config_db = db.cfgdb
        db_obj = {'config_db': config_db}
        yield (config, show, db_obj)
    """
    def is_subport_exist(self, db, key):
        tbl = db.get_table("VLAN_SUB_INTERFACE")
        fvs = tbl.get(key)
        return True if fvs != None else False

    def check_subport_admin_status(self, db, key, status):
        entry = db.get_entry("VLAN_SUB_INTERFACE", key)
        return True if entry['admin_status'] == status else False

    def get_err_str(self, result_output):
        return result_output.split('Error: ')[1].strip('\n')


    @pytest.mark.parametrize(
        'setup_single_bgp_instance_chassis', ['v4'],
        indirect=['setup_single_bgp_instance_chassis']
    )
    @patch('config.main.clicommon.run_command')
    def test_subport_ipv4_ipv6_add_del(self, mock_run, setup_single_bgp_instance_chassis) :
        runner = CliRunner()
        db = Db()
        obj = {'config_db':db.cfgdb}

        test_input = [
        ("add", ["Ethernet4.10", "192.169.1.1/24"]),
        ("add", ["Ethernet4.20", "192.169.2.1/24"]),
        ("add", ["Ethernet8.20", "192.169.3.1/24"]),
        ("remove", ["Ethernet4.10", "192.169.1.1/24"]),
        ("remove", ["Ethernet4.20", "192.169.2.1/24"]),
        ("remove", ["Ethernet8.20", "192.169.3.1/24"]),
        ("add", ["Ethernet4.10", "3fff::1/64"]),
        ("remove", ["Ethernet4.10", "3fff::1/64"])
        ]

        for data in test_input:
            oper = data[0]
            test_args = data[1]
            result = runner.invoke(config.config.commands['interface'].commands['ip'].commands[oper], test_args, obj=obj)
            assert result.exit_code == 0
            if oper == "add":
                assert True == self.is_subport_exist(db.cfgdb, test_args[0])
            else:
                assert False == self.is_subport_exist(db.cfgdb, test_args[0])

    @pytest.mark.parametrize(
        'setup_single_bgp_instance_chassis', ['v4'],
        indirect=['setup_single_bgp_instance_chassis']
    )
    @patch('config.main.clicommon.run_command')
    def test_subport_admin_status_change(self, mock_run, setup_single_bgp_instance_chassis) :
        runner = CliRunner()
        db = Db()
        obj = {'config_db':db.cfgdb}

        intf_name = "Ethernet4.10"
        ip_addr = "192.169.1.1/24"
        result = runner.invoke(config.config.commands['interface'].commands['ip'].commands['add'], [intf_name, ip_addr], obj=obj)
        assert result.exit_code == 0
        assert True == self.is_subport_exist(db.cfgdb, intf_name)
        assert True == self.check_subport_admin_status(db.cfgdb, intf_name, 'up')

        result = runner.invoke(config.config.commands['interface'].commands['shutdown'], [intf_name], obj=obj)
        assert result.exit_code == 0
        assert True == self.check_subport_admin_status(db.cfgdb, intf_name, 'down')
        result = runner.invoke(config.config.commands['interface'].commands['ip'].commands['remove'], [intf_name, ip_addr], obj=obj)
        assert result.exit_code == 0

    @patch('config.main.clicommon.run_command')
    def test_subport_validate_intf_name(self, mock_run) :
        runner = CliRunner()
        db = Db()
        obj = {'config_db':db.cfgdb}

        intf_name = "PortChannel0001.10"
        ip_addr = "192.169.1.1/24"
        vrf = "Vrf1"
        result = runner.invoke(config.config.commands['interface'].commands['ip'].commands['add'], [intf_name, ip_addr], obj=obj)
        assert result.exit_code != 0
        assert self.get_err_str(result.output) == 'Sub port interface name is too long!'

        result = runner.invoke(config.config.commands['interface'].commands['vrf'].commands['bind'], [intf_name, vrf], obj=obj)
        assert result.exit_code != 0
        assert self.get_err_str(result.output) == 'Sub port interface name is too long!'

    @patch('config.main.clicommon.run_command')
    def test_subport_validate_vlan_id(self, mock_run):
        runner = CliRunner()
        db = Db()
        obj = {'config_db': db.cfgdb}

        intf_name = "Ethernet4.0"
        ip_addr = "192.169.1.1/24"
        result = runner.invoke(config.config.commands['interface'].commands['ip'].commands['add'], [intf_name, ip_addr], obj=obj)
        assert result.exit_code != 0
        assert self.get_err_str(result.output) == 'Invalid VLAN ID {} (1-4094)'.format(intf_name.split('.')[1])

        intf_name = "Ethernet4.4095"
        result = runner.invoke(config.config.commands['interface'].commands['ip'].commands['add'], [intf_name, ip_addr], obj=obj)
        assert result.exit_code != 0
        assert self.get_err_str(result.output) == 'Invalid VLAN ID {} (1-4094)'.format(intf_name.split('.')[1])

        intf_name = "Ethernet4.abc"
        result = runner.invoke(config.config.commands['interface'].commands['ip'].commands['add'], [intf_name, ip_addr], obj=obj)
        assert result.exit_code != 0
        assert self.get_err_str(result.output) == 'Invalid VLAN ID {} (1-4094)'.format(intf_name.split('.')[1])

    @pytest.mark.parametrize(
        'setup_single_bgp_instance_chassis', ['v4'],
        indirect=['setup_single_bgp_instance_chassis']
    )
    @patch('config.main.clicommon.run_command')
    def test_subport_can_not_coexist_with_eth_l3intf(self, mock_run, setup_single_bgp_instance_chassis) :
        runner = CliRunner()
        db = Db()
        obj = {'config_db':db.cfgdb}

        test_input = [
        ("add", ["Ethernet20", "192.169.1.1/24"], "pass", ""),
        ("add", ["Ethernet20.10", "192.169.2.1/24"], "fail", ["Ethernet20","L3"]),
        ("remove", ["Ethernet20", "192.169.1.1/24"], "pass", ""),
        ("add", ["Ethernet20.10", "192.169.2.1/24"], "pass", ""),
        ("add", ["Ethernet20", "192.169.1.1/24"], "fail", ["Ethernet20.10","subport"]),
        ("remove", ["Ethernet20.10", "192.169.2.1/24"], "pass", ""),
        ("add", ["Ethernet20", "192.169.1.1/24"], "pass", ""),
        ("remove", ["Ethernet20", "192.169.1.1/24"], "pass", "")
        ]

        for data in test_input:
            oper = data[0]
            test_args = data[1]
            expect_result = data[2]
            err_args = data[3]
            result = runner.invoke(config.config.commands['interface'].commands['ip'].commands[oper], test_args, obj=obj)
            if expect_result == "pass":
                assert result.exit_code == 0
                if oper == "add" and '.' in test_args[0]:
                    assert True == self.is_subport_exist(db.cfgdb, test_args[0])
                else:
                    assert False == self.is_subport_exist(db.cfgdb, test_args[1])
            else:
                assert result.exit_code != 0
                assert self.get_err_str(result.output) == '{} is a {} interface!'.format(err_args[0], err_args[1])

    @pytest.mark.parametrize(
        'setup_single_bgp_instance_chassis', ['v4'],
        indirect=['setup_single_bgp_instance_chassis']
    )
    @patch('config.main.clicommon.run_command')
    def test_subport_can_not_coexist_with_pc_l3intf(self, mock_run, setup_single_bgp_instance_chassis) :
        runner = CliRunner()
        db = Db()
        obj = {'config_db':db.cfgdb}
        pc_obj = {'db':db.cfgdb}

        test_input = [
        ("add", ["PortChannel1", "192.169.1.1/24"], "pass", ""),
        ("add", ["PortChannel1.10", "192.169.2.1/24"], "fail", ["PortChannel1","L3"]),
        ("remove", ["PortChannel1", "192.169.1.1/24"], "pass", ""),
        ("add", ["PortChannel1.10", "192.169.2.1/24"], "pass", ""),
        ("add", ["PortChannel1", "192.169.1.1/24"], "fail", ["PortChannel1.10","subport"]),
        ("remove", ["PortChannel1.10", "192.169.2.1/24"], "pass", ""),
        ("add", ["PortChannel1", "192.169.1.1/24"], "pass", ""),
        ("remove", ["PortChannel1", "192.169.1.1/24"], "pass", "")
        ]
        result = runner.invoke(config.config.commands["portchannel"].commands["add"], ["PortChannel1"], obj=pc_obj)
        for data in test_input:
            oper = data[0]
            test_args = data[1]
            expect_result = data[2]
            err_args = data[3]
            result = runner.invoke(config.config.commands['interface'].commands['ip'].commands[oper], test_args, obj=obj)
            if expect_result == "pass":
                assert result.exit_code == 0
                if oper == "add" and '.' in test_args[0]:
                    assert True == self.is_subport_exist(db.cfgdb, test_args[0])
                else:
                    assert False == self.is_subport_exist(db.cfgdb, test_args[0])
            else:
                assert result.exit_code != 0
                assert self.get_err_str(result.output) == '{} is a {} interface!'.format(err_args[0], err_args[1])

    def test_subport_can_not_as_member_of_pc(self):
        runner = CliRunner()
        db = Db()
        obj = {'db':db.cfgdb}

        portchannel_name = "PortChannel0001"
        port_name = "Ethernet20.10"
        result = runner.invoke(config.config.commands['portchannel'].commands['member'].commands['add'], [portchannel_name, port_name], obj=obj)
        assert result.exit_code != 0
        assert self.get_err_str(result.output) == 'Interface name is invalid. Please enter a valid interface name!!'

    @pytest.mark.parametrize(
        'setup_single_bgp_instance_chassis', ['v4'],
        indirect=['setup_single_bgp_instance_chassis']
    )
    @patch('config.main.clicommon.run_command')
    def test_subport_of_eth_can_not_coexist_with_pc_member(self, mock_run, setup_single_bgp_instance_chassis):
        runner = CliRunner()
        db = Db()
        obj = {'config_db':db.cfgdb}
        pc_obj = {'db':db.cfgdb, 'db_wrap':db, 'namespace':''}

        test_input = [
        ("add", ["Ethernet48.10", "192.169.1.1/24"], "pass", ""),
        ("add", ["PortChannel1", "Ethernet48"], "fail", " Ethernet48 has subinterfaces configured"),
        ("remove", ["Ethernet48.10", "192.169.1.1/24"], "pass", ""),
        ("add", ["PortChannel1", "Ethernet48"], "pass", ""),
        ("add", ["Ethernet48.10", "192.169.1.1/24"], "fail", "Ethernet48 is portchannel member"),
        ("del", ["PortChannel1", "Ethernet48"], "pass", "")
        ]
        result = runner.invoke(config.config.commands["portchannel"].commands["add"], ["PortChannel1"], obj=pc_obj)
        for data in test_input:
            oper = data[0]
            test_args = data[1]
            expect_result = data[2]
            err_args = data[3]

            if 'Ethernet' in test_args[0]:
                result = runner.invoke(config.config.commands['interface'].commands['ip'].commands[oper], test_args, obj=obj)
            else:
                result = runner.invoke(config.config.commands['portchannel'].commands['member'].commands[oper], test_args, obj=pc_obj)
            if expect_result == "pass":
                assert result.exit_code == 0
            else:
                assert result.exit_code != 0
                assert self.get_err_str(result.output) == '{}'.format(err_args)

    @patch('config.main.clicommon.run_command')
    def test_subport_vlan_can_not_coexist_with_normal_vlan(self, mock_run, setup_asic_type) :
        runner = CliRunner()
        db = Db()
        obj = {'config_db': db.cfgdb}
        pc_obj = {'db':db.cfgdb}

        test_input = [
        ("add", ["Ethernet20.10","192.169.1.1/24"], "pass"),
        ("add", ["10"], "fail"),
        ("add", ["20"], "pass"),
        ("add", ["Ethernet20.20","192.169.2.1/24"], "fail"),
        ("add", ["PortChannel1.30","192.169.3.1/24"], "pass"),
        ("add", ["30"], "fail"),
        ("add", ["40"], "pass"),
        ("add", ["PortChannel1.40","192.169.4.1/24"], "fail")
        ]

        result = runner.invoke(config.config.commands["portchannel"].commands["add"], ["PortChannel1"], obj=pc_obj)

        for data in test_input:
            oper = data[0]
            test_args = data[1]
            expect_result = data[2]
            if len(test_args) == 2:
                result = runner.invoke(config.config.commands["interface"].commands["ip"].commands[oper], test_args, obj=obj)
            else:
                result = runner.invoke(config.config.commands["vlan"].commands[oper], test_args, obj=db)

            if expect_result == "pass":
                assert result.exit_code == 0
            else:
                assert result.exit_code != 0
                if len(test_args) == 2:
                    assert self.get_err_str(result.output) == 'Vlan{} already exist'.format(test_args[0].split('.')[1])
                else:
                    assert self.get_err_str(result.output) == 'Vlan{} already created by subport'.format(test_args[0])

    @classmethod
    def teardown_class(cls):
        print("TEARDOWN")
        os.environ["UTILITIES_UNIT_TESTING"] = "0"
