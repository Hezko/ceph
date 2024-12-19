# -*- coding: utf-8 -*-
from typing import Any, Dict, Optional
import errno
import json
import yaml

from mgr_module import CLICheckNonemptyFileInput, CLIReadCommand, CLIWriteCommand, CLICommand, HandlerFuncType, HandleCommandResult

from ..rest_client import RequestException
from ..exceptions import DashboardException
from .nvmeof_conf import ManagedByOrchestratorException, \
    NvmeofGatewayAlreadyExists, NvmeofGatewaysConfig


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

import logging
logger = logging.getLogger(__name__)


class NvmeofCLICommand(CLICommand):
    def call(self,
             mgr: Any,
             cmd_dict: Dict[str, Any],
             inbuf: Optional[str] = None) -> HandleCommandResult:
        logger.error('IN CALL FUNC')
        try:  # Let's capture exceptions
            ret = super().call(mgr, cmd_dict, inbuf)
            import json # REMOVE
            logger.error("QQQQ cmd_dict")
            logger.error(str(cmd_dict)) # REMOVE
            types = set([str(type(v)) for _, v in CLICommand.COMMANDS.items()])
            logger.error(','.join(types))
            logger.error(json.dumps(cmd_dict)) # REMOVE
            format  = cmd_dict['format']
            # if format == 'plain':
            #     out =...
            if format == 'json' or not format:
                out = ret
            elif format == 'yaml':
                out = yaml.dumps(json.loads(ret))
            
            out=ret # REMOVE
            return HandleCommandResult(0, out, '')
        except DashboardException as e:
            logger.exception('tomer error')
            return HandleCommandResult(-e.code, '', e.error_message)
                