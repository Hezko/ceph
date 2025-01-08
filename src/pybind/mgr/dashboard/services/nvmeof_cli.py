# -*- coding: utf-8 -*-
from typing import Any, Dict, Optional
import errno
import json
import yaml
from mgr_module import CLICheckNonemptyFileInput, CLIReadCommand, CLIWriteCommand, HandleCommandResult, CLICommand, HandlerFuncType, HandleCommandResult

from ..rest_client import RequestException
from ..model import nvmeof as model
from .nvmeof_conf import ManagedByOrchestratorException, \
    NvmeofGatewayAlreadyExists, NvmeofGatewaysConfig
from .nvmeof_client import NVMeoFGatewayClient, NVMeoFSubsystemClient, make_dict_from_object, handle_nvmeof_cli_error
from ..exceptions import DashboardException


@CLIReadCommand('dashboard nvmeof-gateway-list')
def list_nvmeof_gateways(_):
    '''
    List NVMe-oF gateways
    '''
    return 0, json.dumps(NvmeofGatewaysConfig.get_gateways_config()), ''


@CLIWriteCommand('dashboard nvmeof-gateway-add')
@CLICheckNonemptyFileInput(desc='NVMe-oF gateway configuration')
def add_nvmeof_gateway(_, inbuf, name: str, group: str, daemon_name: str):
    '''
    Add NVMe-oF gateway configuration. Gateway URL read from -i <file>
    '''
    service_url = inbuf
    try:
        NvmeofGatewaysConfig.add_gateway(name, service_url, group, daemon_name)
        return 0, 'Success', ''
    except NvmeofGatewayAlreadyExists as ex:
        return -errno.EEXIST, '', str(ex)
    except ManagedByOrchestratorException as ex:
        return -errno.EINVAL, '', str(ex)
    except RequestException as ex:
        return -errno.EINVAL, '', str(ex)


@CLIWriteCommand('dashboard nvmeof-gateway-rm')
def remove_nvmeof_gateway(_, name: str, daemon_name: str = ''):
    '''
    Remove NVMe-oF gateway configuration
    '''
    try:
        NvmeofGatewaysConfig.remove_gateway(name, daemon_name)
        return 0, 'Success', ''
    except ManagedByOrchestratorException as ex:
        return -errno.EINVAL, '', str(ex)


class NVMeoFGateway:
    @CLIReadCommand('nvmeof gw info')
    @handle_nvmeof_cli_error
    def list(self, gw_group: Optional[str] = None):
        result = NVMeoFGatewayClient.info(gw_group)
        return HandleCommandResult(0, json.dumps(result), '')
        
        
class NvmeofCLICommand(CLICommand):
    def call(self,
             mgr: Any,
             cmd_dict: Dict[str, Any],
             inbuf: Optional[str] = None) -> HandleCommandResult:
        try:
            ret = super().call(mgr, cmd_dict, inbuf)
            format  = cmd_dict.get('format')
            if format == 'json' or not format:
                out = ret
            elif format == 'yaml':
                out = yaml.dump(json.loads(ret)) 
            else:
                return HandleCommandResult(-errno.EINVAL, '', f"format '{format}' is not implemented")
            return HandleCommandResult(0, out, '')
        except DashboardException as e:
            return HandleCommandResult(-errno.EINVAL, '', str(e))
        
        
class NVMeoFSubsystem:
    @CLIReadCommand('nvmeof subsystem list')
    @handle_nvmeof_cli_error
    def list(self, gw_group: Optional[str] = None):
        result = NVMeoFSubsystemClient.list(gw_group)
        return HandleCommandResult(0, json.dumps(result), '')
    
    @NvmeofCLICommand('nvmeof2 subsystem list')
    def list(self, gw_group: Optional[str] = None):
        return NVMeoFSubsystemClient.list(gw_group)
        
    
    @CLIReadCommand('nvmeof subsystem get')
    @handle_nvmeof_cli_error
    def get(self, nqn: str, gw_group: Optional[str] = None):
        result = NVMeoFSubsystemClient.get(nqn, gw_group)
        return HandleCommandResult(0, json.dumps(result), '')
    
    @CLIReadCommand('nvmeof subsystem create')
    @handle_nvmeof_cli_error
    def create(self, nqn: str, enable_ha: bool, max_namespaces: int = 1024,
                   gw_group: Optional[str] = None):
        NVMeoFSubsystemClient.create(nqn, enable_ha, max_namespaces, gw_group)
        return HandleCommandResult(0, 'Success', '')
    
    @CLIReadCommand('nvmeof subsystem delete')
    @handle_nvmeof_cli_error
    def delete(self, nqn: str, force: Optional[str] = "false", gw_group: Optional[str] = None):
        NVMeoFSubsystemClient.delete(nqn, force, gw_group)
        return HandleCommandResult(0, 'Success', '')
    
    
