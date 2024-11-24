# -*- coding: utf-8 -*-
import errno
import json

from mgr_module import CLICheckNonemptyFileInput, CLIReadCommand, CLIWriteCommand

from ..rest_client import RequestException
from .nvmeof_conf import ManagedByOrchestratorException, \
    NvmeofGatewayAlreadyExists, NvmeofGatewaysConfig

import traceback
import logging
logger = logging.getLogger(__name__)
# try:
#     from ..controllers.nvmeof import NVMeoFSubsystem

#     test = NVMeoFSubsystem()

#     @CLIReadCommand('dashboard tomer-test2')
#     def test123(_):
#         return 0, test.list("dummygw")
# except:
#     @CLIReadCommand('dashboard tomer-test-exception-caught')
#     def test123(_):
#         return 0, json.dumps({'a':1})


try:
    from ..services.nvmeof_client import NVMeoFClient

    @CLIReadCommand('dashboard tomer-test-x')
    def list_nvmeof_gateways2(_):
        '''
        List NVMe-oF gateways
        '''
        return 0, json.dumps(NVMeoFClient(gw_group='dummygw').stub.list_subsystems(
                    NVMeoFClient.pb2.list_subsystems_req()
                )), ''
except Exception as e:
    logger.exception('ttttt ex')
    s12 = str(e)
    @CLIReadCommand('dashboard tomer-test-exception-caught')
    def test123(_):
        return 0, json.dumps({"gateways": {}, "bla": s12}), ''

@CLIReadCommand('nvmf param-test')
def nvmf_param_test(*args, **kwargs):
    '''
    List NVMe-oF gateways
    '''
    logger.error('tomer-test-x params')
    logger.error(f'args: {str(args)}')
    logger.error(f'kwargs: {str(kwargs)}')
    return 0, json.dumps(NvmeofGatewaysConfig.get_gateways_config()), ''


@CLIReadCommand('nvmf test')
def nvmf_test(_):
    '''
    List NVMe-oF gateways
    '''
    return 0, json.dumps(NvmeofGatewaysConfig.get_gateways_config()), ''


@CLIReadCommand('dashboard real-import-test')
def list_nvmeof_gateways333321(_):
    '''
    List NVMe-oF gateways
    ''' 
    from ..controllers import NVMeoFSubsystem
    obj = NVMeoFSubsystem()
    
    
    return 0, json.dumps(obj.list()), ''

@CLIReadCommand('dashboard import-test')
def list_nvmeof_gateways222(_):
    '''
    List NVMe-oF gateways
    '''
    try:
        from ..services import nvmeof_client as nc
        logger.error(str(dir(nc)))
        logger.error(f'{str(nc.__name__)}, {str(nc.__file__)}')
        from ..services.nvmeof_client import NVMeoFClient
    except Exception as e:
        logger.exception('ttttt ex')
    
    return 0, json.dumps(NVMeoFClient(gw_group='dummygw').stub.list_subsystems(
                    NVMeoFClient.pb2.list_subsystems_req()
                )), ''

@CLIReadCommand('dashboard tomer-test')
def list_nvmeof_gateways1(_):
    '''
    List NVMe-oF gateways
    '''
    
    logger.error('YYYYYYYYYYY')
    for line in traceback.format_stack():
        logger.error(line.strip())
    logger.error('end YYYYYYYYYYY')
    return 0, json.dumps(NvmeofGatewaysConfig.get_gateways_config()), ''


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
