import errno
from unittest.mock import MagicMock

import pytest
from mgr_module import CLICommand, HandleCommandResult

from ..services.nvmeof_cli import NvmeofCLICommand
from ..controllers import nvmeof as controller
from ..model import nvmeof as model

@pytest.fixture(scope="class", name="sample_command")
def fixture_sample_command():
    test_cmd = "test command"

    @NvmeofCLICommand(test_cmd)
    def func(_): # noqa # pylint: disable=unused-variable
        return {'a': '1', 'b': 2}
    yield test_cmd
    del NvmeofCLICommand.COMMANDS[test_cmd]
    assert test_cmd not in NvmeofCLICommand.COMMANDS


@pytest.fixture(name='base_call_mock')
def fixture_base_call_mock(monkeypatch):
    mock_result = {'a': 'b'}
    super_mock = MagicMock()
    super_mock.return_value = mock_result
    monkeypatch.setattr(CLICommand, 'call', super_mock)
    return super_mock


@pytest.fixture(name='base_call_return_none_mock')
def fixture_base_call_return_none_mock(monkeypatch):
    mock_result = None
    super_mock = MagicMock()
    super_mock.return_value = mock_result
    monkeypatch.setattr(CLICommand, 'call', super_mock)
    return super_mock


class TestNvmeofCLICommand:
    def test_command_being_added(self, sample_command):
        assert sample_command in NvmeofCLICommand.COMMANDS
        assert isinstance(NvmeofCLICommand.COMMANDS[sample_command], NvmeofCLICommand)

    def test_command_return_cmd_result_default_format(self, base_call_mock, sample_command):
        result = NvmeofCLICommand.COMMANDS[sample_command].call(MagicMock(), {})
        assert isinstance(result, HandleCommandResult)
        assert result.retval == 0
        assert result.stdout == '{"a": "b"}'
        assert result.stderr == ''
        base_call_mock.assert_called_once()

    def test_command_return_cmd_result_json_format(self, base_call_mock, sample_command):
        result = NvmeofCLICommand.COMMANDS[sample_command].call(MagicMock(), {'format': 'json'})
        assert isinstance(result, HandleCommandResult)
        assert result.retval == 0
        assert result.stdout == '{"a": "b"}'
        assert result.stderr == ''
        base_call_mock.assert_called_once()

    def test_command_return_cmd_result_yaml_format(self, base_call_mock, sample_command):
        result = NvmeofCLICommand.COMMANDS[sample_command].call(MagicMock(), {'format': 'yaml'})
        assert isinstance(result, HandleCommandResult)
        assert result.retval == 0
        assert result.stdout == 'a: b\n'
        assert result.stderr == ''
        base_call_mock.assert_called_once()

    def test_command_return_cmd_result_invalid_format(self, base_call_mock, sample_command):
        mock_result = {'a': 'b'}
        super_mock = MagicMock()
        super_mock.call.return_value = mock_result

        result = NvmeofCLICommand.COMMANDS[sample_command].call(MagicMock(), {'format': 'invalid'})
        assert isinstance(result, HandleCommandResult)
        assert result.retval == -errno.EINVAL
        assert result.stdout == ''
        assert result.stderr
        base_call_mock.assert_called_once()

    def test_command_return_empty_cmd_result(self, base_call_return_none_mock, sample_command):
        result = NvmeofCLICommand.COMMANDS[sample_command].call(MagicMock(), {})
        assert isinstance(result, HandleCommandResult)
        assert result.retval == 0
        assert result.stdout == ''
        assert result.stderr == ''
        base_call_return_none_mock.assert_called_once()

class TestGWCommands:
    def test_gw_info(self, monkeypatch):
        gw_info_mock = MagicMock()
        gw_info_mock.cli_version = "1.2.3"
        gw_info_mock.version = "2.0.0"
        gw_info_mock.name = "gw1"
        gw_info_mock.group = "ga"
        gw_info_mock.addr = "192.168.1.1"
        gw_info_mock.port = 8080
        gw_info_mock.load_balancing_group = 1
        gw_info_mock.spdk_version = '11.1'
        gw_info_mock.status = 0
        gw_info_mock.error_message = ''
        
        # gw_info = {
        #             "cli_version": "1.2.3",
        #             "version": "2.0.0",
        #             "name": "Gateway1",
        #             "group": "GroupA",
        #             "addr": "192.168.1.1",
        #             "port": 8080,
        #             "load_balancing_group": 1,
        #             "spdk_version": "SPDKv19.11",
        #             "status":0,
        #             "error_message": ''
        #           }
        stub_mock = MagicMock()
        stub_mock.stub.get_gateway_info.return_value = gw_info_mock
        nvmf_client_mock = MagicMock()
        nvmf_client_mock.return_value = stub_mock
        monkeypatch.setattr(controller, 'NVMeoFClient', nvmf_client_mock)
        ret = NvmeofCLICommand.COMMANDS["nvmeof gw info"].call(None, {}, '')
        
        assert isinstance(ret, model.GatewayInfo)