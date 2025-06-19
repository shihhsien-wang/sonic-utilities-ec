#!/usr/bin/env python

import pytest

import os
import mock
import logging

import show.main as show
import config.main as config

from click.testing import CliRunner
from utilities_common.db import Db

from .mock_tables import dbconnector
from .syslog_input import config_mock
from .syslog_input import assert_show_output


ERROR_PATTERN_INVALID_IP = "does not appear to be an IPv4 or IPv6 address"
ERROR_PATTERN_PROHIBITED_IP = "is a loopback/multicast/link-local IP address"
ERROR_PATTERN_IP_FAMILY_MISMATCH = "IP address family mismatch"

ERROR_PATTERN_INVALID_PORT = "is not a valid integer"
ERROR_PATTERN_INVALID_PORT_RANGE = "is not in the valid range of 0 to 65535"

ERROR_PATTERN_INVALID_VRF = "invalid choice"
ERROR_PATTERN_NONEXISTENT_VRF = "VRF doesn't exist in Linux"

SUCCESS = 0
ERROR2 = 2


test_path = os.path.dirname(os.path.abspath(__file__))
mock_db_path = os.path.join(test_path, "syslog_input")
logger = logging.getLogger(__name__)


class TestSyslog:
    @classmethod
    def setup_class(cls):
        logger.info("SETUP")
        os.environ["UTILITIES_UNIT_TESTING"] = "1"

    @classmethod
    def teardown_class(cls):
        logger.info("TEARDOWN")
        os.environ["UTILITIES_UNIT_TESTING"] = "0"
        os.environ["UTILITIES_UNIT_TESTING_TOPOLOGY"] = ""
        dbconnector.dedicated_dbs["CONFIG_DB"] = None

    ########## CONFIG SYSLOG ##########

    @mock.patch("utilities_common.cli.run_command", mock.MagicMock(return_value=None))
    @pytest.mark.parametrize("server_ip", ["2.2.2.2", "2222::2222"])
    def test_config_syslog_basic(self, server_ip):
        db = Db()
        runner = CliRunner()

        result = runner.invoke(
            config.config.commands["syslog"].commands["add"], [server_ip], obj=db
        )

        logger.debug("\n" + result.output)
        logger.debug(result.exit_code)
        assert result.exit_code == SUCCESS

        result = runner.invoke(
            config.config.commands["syslog"].commands["del"], [server_ip], obj=db
        )

        logger.debug("\n" + result.output)
        logger.debug(result.exit_code)
        assert result.exit_code == SUCCESS

    @mock.patch("utilities_common.cli.run_command", mock.MagicMock(return_value=None))
    @mock.patch("config.syslog.exec_cmd", mock.MagicMock(side_effect=config_mock.exec_cmd_mock))
    @pytest.mark.parametrize("server_ip,source_ip,port,vrf", [
        ("2.2.2.2", "1.1.1.1", "514", "default"),
        ("4.4.4.4", "3.3.3.3", "514", "mgmt"),
        ("2222::2222", "1111::1111", "514", "Vrf-Data")
    ])
    def test_config_syslog_extended(self, server_ip, source_ip, port, vrf):
        dbconnector.dedicated_dbs["CONFIG_DB"] = os.path.join(mock_db_path, "vrf_cdb")

        db = Db()
        runner = CliRunner()

        result = runner.invoke(
            config.config.commands["syslog"].commands["add"],
            [server_ip, "--source", source_ip, "--port", port, "--vrf", vrf], obj=db
        )

        logger.debug("\n" + result.output)
        logger.debug(result.exit_code)
        assert result.exit_code == SUCCESS

        result = runner.invoke(
            config.config.commands["syslog"].commands["del"], [server_ip], obj=db
        )

        logger.debug("\n" + result.output)
        logger.debug(result.exit_code)
        assert result.exit_code == SUCCESS

    @pytest.mark.parametrize("server_ip,source_ip", [
        ("2.2.2.2", "1.1.1.1111"),
        ("4.4.4.4444", "3.3.3.3")
    ])
    def test_config_syslog_invalid_ip(self, server_ip, source_ip):
        db = Db()
        runner = CliRunner()

        result = runner.invoke(
            config.config.commands["syslog"].commands["add"],
            [server_ip, "--source", source_ip], obj=db
        )

        logger.debug("\n" + result.output)
        logger.debug(result.exit_code)
        assert ERROR_PATTERN_INVALID_IP in result.output
        assert result.exit_code == ERROR2

    @pytest.mark.parametrize("source_ip", ["127.0.0.1", "224.0.0.1"])
    def test_config_syslog_prohibited_sip(self, source_ip):
        db = Db()
        runner = CliRunner()

        result = runner.invoke(
            config.config.commands["syslog"].commands["add"],
            ["2.2.2.2", "--source", source_ip], obj=db
        )

        logger.debug("\n" + result.output)
        logger.debug(result.exit_code)
        assert ERROR_PATTERN_PROHIBITED_IP in result.output
        assert result.exit_code == ERROR2

    def test_config_syslog_ip_family_mismatch(self):
        db = Db()
        runner = CliRunner()

        result = runner.invoke(
            config.config.commands["syslog"].commands["add"],
            ["2.2.2.2", "--source", "1111::1111"], obj=db
        )

        logger.debug("\n" + result.output)
        logger.debug(result.exit_code)
        assert ERROR_PATTERN_IP_FAMILY_MISMATCH in result.output
        assert result.exit_code == ERROR2

    def test_config_syslog_invalid_port(self):
        db = Db()
        runner = CliRunner()

        result = runner.invoke(
            config.config.commands["syslog"].commands["add"],
            ["2.2.2.2", "--port", "514p"], obj=db
        )

        logger.debug("\n" + result.output)
        logger.debug(result.exit_code)
        assert ERROR_PATTERN_INVALID_PORT in result.output
        assert result.exit_code == ERROR2

    @pytest.mark.parametrize("port", ["-1", "65536"])
    def test_config_syslog_invalid_port_range(self, port):
        db = Db()
        runner = CliRunner()

        result = runner.invoke(
            config.config.commands["syslog"].commands["add"],
            ["2.2.2.2", "--port", port], obj=db
        )

        logger.debug("\n" + result.output)
        logger.debug(result.exit_code)
        assert ERROR_PATTERN_INVALID_PORT_RANGE in result.output
        assert result.exit_code == ERROR2

    def test_config_syslog_invalid_vrf(self):
        db = Db()
        runner = CliRunner()

        result = runner.invoke(
            config.config.commands["syslog"].commands["add"],
            ["2.2.2.2", "--vrf", "default1"], obj=db
        )

        logger.debug("\n" + result.output)
        logger.debug(result.exit_code)
        assert ERROR_PATTERN_INVALID_VRF in result.output
        assert result.exit_code == ERROR2

    @pytest.mark.parametrize("vrf", ["mgmt", "Vrf-Data"])
    @mock.patch("config.syslog.get_vrf_list", mock.MagicMock(return_value=[]))
    @mock.patch("config.syslog.get_vrf_member_dict", mock.MagicMock(return_value={}))
    @mock.patch("config.syslog.get_ip_addr_dict", mock.MagicMock(return_value={}))
    def test_config_syslog_nonexistent_vrf(self, vrf):
        dbconnector.dedicated_dbs["CONFIG_DB"] = os.path.join(mock_db_path, "vrf_cdb")

        db = Db()
        runner = CliRunner()

        result = runner.invoke(
            config.config.commands["syslog"].commands["add"],
            ["2.2.2.2", "--vrf", vrf], obj=db
        )

        logger.debug("\n" + result.output)
        logger.debug(result.exit_code)
        assert ERROR_PATTERN_NONEXISTENT_VRF in result.output
        assert result.exit_code == ERROR2

    ########## SHOW SYSLOG ##########

    def test_show_syslog_empty(self):
        db = Db()
        runner = CliRunner()

        result = runner.invoke(
            show.cli.commands["syslog"], [], obj=db
        )

        logger.debug("\n" + result.output)
        logger.debug(result.exit_code)
        assert result.exit_code == SUCCESS
        assert result.output == assert_show_output.show_syslog_empty

    def test_show_syslog(self):
        dbconnector.dedicated_dbs["CONFIG_DB"] = os.path.join(mock_db_path, "syslog_cdb")

        db = Db()
        runner = CliRunner()

        result = runner.invoke(
            show.cli.commands["syslog"], [], obj=db
        )

        logger.debug("\n" + result.output)
        logger.debug(result.exit_code)
        assert result.exit_code == SUCCESS
        assert result.output == assert_show_output.show_syslog

    @mock.patch("utilities_common.cli.run_command", mock.MagicMock(return_value=None))
    @mock.patch("config.syslog.exec_cmd", mock.MagicMock(side_effect=config_mock.exec_cmd_mock_default_vrf_ip_not_found))
    def test_config_syslog_source_ip_not_in_default_vrf(self):
        dbconnector.dedicated_dbs["CONFIG_DB"] = os.path.join(mock_db_path, "vrf_cdb")
        db = Db()
        runner = CliRunner()

        result = runner.invoke(
            config.config.commands["syslog"].commands["add"],
            ["5.5.5.5", "--source", "10.0.0.100"], obj=db
        )

        logger.debug("\n" + result.output)
        logger.debug(result.exit_code)
        assert "IP doesn't exist in Linux default VRF" in result.output
        assert result.exit_code == ERROR2

    @mock.patch("utilities_common.cli.run_command", mock.MagicMock(return_value=None))
    @mock.patch("config.syslog.exec_cmd", mock.MagicMock(side_effect=config_mock.exec_cmd_mock_specified_vrf_ip_not_found))
    def test_config_syslog_source_ip_not_in_specified_vrf(self):
        dbconnector.dedicated_dbs["CONFIG_DB"] = os.path.join(mock_db_path, "vrf_cdb")
        db = Db()
        runner = CliRunner()

        result = runner.invoke(
            config.config.commands["syslog"].commands["add"],
            ["6.6.6.6", "--source", "20.0.0.200", "--vrf", "Vrf-Data"], obj=db
        )

        logger.debug("\n" + result.output)
        logger.debug(result.exit_code)
        assert "IP doesn't exist in Linux Vrf-Data VRF" in result.output
        assert result.exit_code == ERROR2

    @mock.patch("utilities_common.cli.run_command", mock.MagicMock(return_value=None))
    def test_config_syslog_add_duplicate_server(self):
        # Ensure a clean CONFIG_DB state for this test
        dbconnector.dedicated_dbs["CONFIG_DB"] = None
        db = Db()
        runner = CliRunner()

        server_ip = "7.7.7.7"

        # First add operation
        result = runner.invoke(
            config.config.commands["syslog"].commands["add"],
            [server_ip], obj=db
        )
        logger.debug(f"\nFirst add operation output:\n{result.output}")
        logger.debug(f"First add operation exit code: {result.exit_code}")
        assert result.exit_code == SUCCESS

        # Attempt to add the same server again
        result = runner.invoke(
            config.config.commands["syslog"].commands["add"],
            [server_ip], obj=db
        )
        logger.debug(f"\nSecond add operation output:\n{result.output}")
        logger.debug(f"Second add operation exit code: {result.exit_code}")

        # server_validator(..., is_exist=False) is called for the add command.
        # If is_exist_in_db returns True, it raises UsageError with:
        # f"Invalid value for {param_name}: {value} is a valid syslog server"
        expected_error_message = f"Invalid value for server_ip_address: {server_ip} is a valid syslog server"
        assert expected_error_message in result.output
        assert result.exit_code == ERROR2

    @mock.patch("utilities_common.cli.run_command", mock.MagicMock(return_value=None))
    def test_config_syslog_delete_non_existent_server(self):
        # Ensure a clean CONFIG_DB state for this test, so the server is guaranteed not to exist
        dbconnector.dedicated_dbs["CONFIG_DB"] = None
        db = Db()
        runner = CliRunner()

        server_ip_to_delete = "8.8.8.8"

        # Attempt to delete a non-existent server
        result = runner.invoke(
            config.config.commands["syslog"].commands["del"],
            [server_ip_to_delete], obj=db
        )
        logger.debug(f"\nDelete non-existent server output:\n{result.output}")
        logger.debug(f"Delete non-existent server exit code: {result.exit_code}")

        # For the 'del' command, server_validator is called with is_exist=True.
        # If is_exist_in_db returns False (server doesn't exist), it raises UsageError with:
        # f"Invalid value for {param_name}: {value} is not a valid syslog server"
        expected_error_message = f"Invalid value for server_ip_address: {server_ip_to_delete} is not a valid syslog server"
        assert expected_error_message in result.output
        assert result.exit_code == ERROR2
