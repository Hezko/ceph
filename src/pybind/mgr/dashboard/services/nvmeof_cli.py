# -*- coding: utf-8 -*-
from typing import Optional
import errno
import json
from mgr_module import CLICheckNonemptyFileInput, CLIReadCommand, CLIWriteCommand

from ..rest_client import RequestException
from ..model import nvmeof as model
from .nvmeof_conf import ManagedByOrchestratorException, \
    NvmeofGatewayAlreadyExists, NvmeofGatewaysConfig
from .nvmeof_client import NVMeoFGatewayClient, make_dict_from_object, handle_nvmeof_cli_error
        
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


#TODO: decorator to handle errors
class NVMeoFGateway(NVMeoFGatewayClient):
    @CLIReadCommand('nvmeof gw info')
    @handle_nvmeof_cli_error
    def list(self, gw_group: Optional[str] = None):
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'TOMER {gw_group=}')
        result = NVMeoFGatewayClient.list(gw_group)
        result = make_dict_from_object(model.GatewayInfo, result)
        return 0, json.dumps(result), ''
        