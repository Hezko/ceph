import errno
import unittest
import pytest
from unittest.mock import MagicMock

from mgr_module import HandleCommandResult
from ..services.nvmeof_cli import NvmeofCLICommand
from ..services import nvmeof_cli as nvmeof_cli_module

@pytest.fixture(scope="class")
def sample_command(self):
    test_cmd = "test command"
    @NvmeofCLICommand(test_cmd)
    def func(_):
        return {'a': '1', 'b':2 }
    yield test_cmd
    del NvmeofCLICommand.COMMANDS[test_cmd]
    assert test_cmd not in NvmeofCLICommand.COMMANDS
    
class NvmeofCLICommandTest(unittest.TestCase):
    def test_command_being_added(self, sample_command):
        assert sample_command in NvmeofCLICommand.COMMANDS
        assert type(NvmeofCLICommand.COMMANDS[sample_command]) is NvmeofCLICommand
            
    def test_command_return_cmd_result_default_format(self, monkeypatch, sample_command):
        mock_result = {'a':'b'}
        super_mock = MagicMock()
        super_mock.call.return_value = mock_result
        monkeypatch.setattr(nvmeof_cli_module, 'super', super_mock)
        
        result = NvmeofCLICommand.COMMANDS[sample_command].call(MagicMock(), {})
        assert type(result) is HandleCommandResult
        assert result.retval == 0
        assert result.stdout == '{"a": "b"}'
        assert result.stderr == ''
        
    def test_command_return_cmd_result_json_format(self, monkeypatch, sample_command):
        mock_result = {'a':'b'}
        super_mock = MagicMock()
        super_mock.call.return_value = mock_result
        monkeypatch.setattr(nvmeof_cli_module, 'super', super_mock)
        
        result = NvmeofCLICommand.COMMANDS[sample_command].call(MagicMock(), {'format': 'json'})
        assert type(result) is HandleCommandResult
        assert result.retval == 0
        assert result.stdout == '{"a": "b"}'
        assert result.stderr == ''
        
    def test_command_return_cmd_result_yaml_format(self, monkeypatch, sample_command):
        mock_result = {'a':'b'}
        super_mock = MagicMock()
        super_mock.call.return_value = mock_result
        monkeypatch.setattr(nvmeof_cli_module, 'super', super_mock)
        
        result = NvmeofCLICommand.COMMANDS[sample_command].call(MagicMock(), {'format': 'yaml'})
        assert type(result) is HandleCommandResult
        assert result.retval == 0
        assert result.stdout == 'a: b\n'
        assert result.stderr == ''
        
    def test_command_return_cmd_result_invalid_format(self, monkeypatch, sample_command):
        mock_result = {'a':'b'}
        super_mock = MagicMock()
        super_mock.call.return_value = mock_result
        monkeypatch.setattr(nvmeof_cli_module, 'super', super_mock)
        
        result = NvmeofCLICommand.COMMANDS[sample_command].call(MagicMock(), {'format': 'invalid'})
        assert type(result) is HandleCommandResult
        assert result.retval == -errno.EINVAL
        assert result.stdout == ''
        assert result.stderr 
        
    def test_command_return_empty_cmd_result(self, monkeypatch, sample_command):
        mock_result = None
        super_mock = MagicMock()
        super_mock.call.return_value = mock_result
        monkeypatch.setattr(nvmeof_cli_module, 'super', super_mock)
        
        result = NvmeofCLICommand.COMMANDS[sample_command].call(MagicMock(), {})
        assert type(result) is HandleCommandResult
        assert result.retval == 0
        assert result.stdout == ''
        assert result.stderr == ''
        