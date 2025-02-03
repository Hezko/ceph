import functools
import logging
from collections.abc import Iterable
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Type, Generator

from ..exceptions import DashboardException
from .nvmeof_conf import NvmeofGatewaysConfig

logger = logging.getLogger("nvmeof_client")

try:
    import grpc  # type: ignore
    import grpc._channel  # type: ignore
    from google.protobuf.message import Message  # type: ignore

    from .proto import gateway_pb2 as pb2  # type: ignore
    from .proto import gateway_pb2_grpc as pb2_grpc  # type: ignore
except ImportError:
    grpc = None
else:

    class NVMeoFClient(object):
        pb2 = pb2

        def __init__(self, gw_group: Optional[str] = None, traddr: Optional[str] = None):
            logger.info("Initiating nvmeof gateway connection...")
            try:
                if not gw_group:
                    service_name, self.gateway_addr = NvmeofGatewaysConfig.get_service_info()
                else:
                    service_name, self.gateway_addr = NvmeofGatewaysConfig.get_service_info(
                        gw_group
                    )
            except TypeError as e:
                raise DashboardException(
                    f'Unable to retrieve the gateway info: {e}'
                )

            # While creating listener need to direct request to the gateway
            # address where listener is supposed to be added.
            if traddr:
                gateways_info = NvmeofGatewaysConfig.get_gateways_config()
                matched_gateway = next(
                    (
                        gateway
                        for gateways in gateways_info['gateways'].values()
                        for gateway in gateways
                        if traddr in gateway['service_url']
                    ),
                    None
                )
                if matched_gateway:
                    self.gateway_addr = matched_gateway.get('service_url')
                    logger.debug("Gateway address set to: %s", self.gateway_addr)

            root_ca_cert = NvmeofGatewaysConfig.get_root_ca_cert(service_name)
            if root_ca_cert:
                client_key = NvmeofGatewaysConfig.get_client_key(service_name)
                client_cert = NvmeofGatewaysConfig.get_client_cert(service_name)

            if root_ca_cert and client_key and client_cert:
                logger.info('Securely connecting to: %s', self.gateway_addr)
                credentials = grpc.ssl_channel_credentials(
                    root_certificates=root_ca_cert,
                    private_key=client_key,
                    certificate_chain=client_cert,
                )
                self.channel = grpc.secure_channel(self.gateway_addr, credentials)
            else:
                logger.info("Insecurely connecting to: %s", self.gateway_addr)
                self.channel = grpc.insecure_channel(self.gateway_addr)
            self.stub = pb2_grpc.GatewayStub(self.channel)

    def make_namedtuple_from_object(cls: Type[NamedTuple], obj: Any) -> NamedTuple:
        return cls(
            **{
                field: getattr(obj, field)
                for field in cls._fields
                if hasattr(obj, field)
            }
        )  # type: ignore

    Model = Dict[str, Any]

    def map_model(
        model: Type[NamedTuple],
        first: Optional[str] = None,
    ) -> Callable[..., Callable[..., Model]]:
        def decorator(func: Callable[..., Message]) -> Callable[..., Model]:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Model:
                message = func(*args, **kwargs)
                if first:
                    try:
                        message = getattr(message, first)[0]
                    except IndexError:
                        raise DashboardException(
                            msg="Not Found", http_status_code=404, component="nvmeof"
                        )

                return make_namedtuple_from_object(model, message)._asdict()

            return wrapper

        return decorator

    Collection = List[Model]

    def map_collection(
        model: Type[NamedTuple],
        pick: str,
        finalize: Optional[Callable[[Message, Collection], Collection]] = None,
    ) -> Callable[..., Callable[..., Collection]]:
        def decorator(func: Callable[..., Message]) -> Callable[..., Collection]:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Collection:
                message = func(*args, **kwargs)
                collection: Iterable = getattr(message, pick)
                out = [
                    make_namedtuple_from_object(model, i)._asdict() for i in collection
                ]
                if finalize:
                    return finalize(message, out)
                return out

            return wrapper

        return decorator

    import errno

    NVMeoFError2HTTP = {
        # errno errors
        errno.EPERM: 403,  # 1
        errno.ENOENT: 404,  # 2
        errno.EACCES: 403,  # 13
        errno.EEXIST: 409,  # 17
        errno.ENODEV: 404,  # 19
        # JSONRPC Spec: https://www.jsonrpc.org/specification#error_object
        -32602: 422,  # Invalid Params
        -32603: 500,  # Internal Error
    }

    def handle_nvmeof_error(func: Callable[..., Message]) -> Callable[..., Message]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Message:
            try:
                response = func(*args, **kwargs)
            except grpc._channel._InactiveRpcError as e:  # pylint: disable=protected-access
                raise DashboardException(
                    msg=e.details(),
                    code=e.code(),
                    http_status_code=504,
                    component="nvmeof",
                )

            if response.status != 0:
                raise DashboardException(
                    msg=response.error_message,
                    code=response.status,
                    http_status_code=NVMeoFError2HTTP.get(response.status, 400),
                    component="nvmeof",
                )
            return response

        return wrapper

    def empty_response(func: Callable[..., Message]) -> Callable[..., None]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> None:
            func(*args, **kwargs)

        return wrapper


    class MaxRecursionDepthError(Exception):
        pass


    def obj_to_namedtuple(data: Any, target_type: Type[NamedTuple], max_depth: int = 4) -> NamedTuple:
        """
        Convert an object or dict to a NamedTuple, handling nesting and lists lazily.
        This will raise an error if nesting depth exceeds the max depth (default 4) 
        to avoid bloating the memory in case of mutual references between objects.

        :param data: The input data - object or dictionary
        :param target_type: The target NamedTuple type
        :param max_depth: The maximum depth allowed for recursion
        :return: An instance of the target NamedTuple with fields populated from the JSON
        """

        if not isinstance(target_type, type) or not hasattr(target_type, '_fields'):
            raise TypeError("target_type must be a NamedTuple type.")

        def convert(value, field_type, depth) -> Generator:
            if depth > max_depth:
                raise MaxRecursionDepthError(f"Maximum nesting depth of {max_depth} exceeded at depth {depth}.")
            
            if isinstance(value, dict) and hasattr(field_type, '_fields'):
                # Lazily create NamedTuple for nested dicts
                yield from lazily_create_namedtuple(value, field_type, depth + 1)
            elif isinstance(value, list):
                # Handle empty lists directly
                if not value:
                    yield []
                else:
                    # Lazily process each item in the list based on the expected item type
                    item_type = field_type.__args__[0] if hasattr(field_type, '__args__') else None
                    processed_items = []
                    for v in value:
                        if item_type:
                            processed_items.append(next(convert(v, item_type, depth + 1)))
                        else:
                            processed_items.append(v)
                    yield processed_items
            else:
                # Yield the value as is for simple types
                yield value

        def lazily_create_namedtuple(data: Any, target_type: Type[NamedTuple], depth: int) -> Generator:
            """ Lazily create NamedTuple from a dict """
            field_values = {}
            for field, field_type in zip(target_type._fields, target_type.__annotations__.values()):
                # this condition is complex since we need to navigate between dicts, empty dicts and objects
                if hasattr(data, field): 
                    # Lazily process each field's value
                    field_values[field] = next(convert(getattr(data, field), field_type, depth))
                elif isinstance(data, dict) and data.get(field) is not None:
                    field_values[field] = next(convert(data.get(field), field_type, depth))
                else:
                    # If the field is missing from the JSON we assign None
                    field_values[field] = None

            namedtuple_instance = target_type(**field_values)
            yield namedtuple_instance

        namedtuple_values = next(lazily_create_namedtuple(data, target_type, 1))
        return namedtuple_values

    def map_model2(model: Type[NamedTuple]) -> Callable[..., Callable[..., Model]]:
        def decorator(func: Callable[..., Message]) -> Callable[..., Model]:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Model:
                message = func(*args, **kwargs)

                return obj_to_namedtuple(message, model)._asdict()

            return wrapper

        return decorator
    
    def pick(field:str, first: bool=False) -> Callable[..., Callable[..., object]]:
        def decorator(func: Callable[..., Dict]) -> Callable[..., object]:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> object:
                model = func(*args, **kwargs)
                field_to_ret = getattr(model, field)
                if first:
                    field_to_ret = field_to_ret[0]
                return field_to_ret
            return wrapper
        return decorator