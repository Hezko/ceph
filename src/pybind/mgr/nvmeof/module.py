import logging
import time

from mgr_module import CLIReadCommand, HandleCommandResult, MgrModule, Option
import rbd

logger = logging.getLogger(__name__)


class NVMeoF(MgrModule):
    MODULE_OPTIONS = [
        Option(
            name='metadata_pool_pg_num',
            type='int',
            default=128,
            desc='pg_num for metadata pool',
            runtime=True
        ),
        Option(
            name='metadata_pool_name',
            type='str',
            default='.nvmeof',
            desc='the name of the NVMeoF metadata pool',
            runtime=True
        ),
    ]

    def __init__(self, *args, **kwargs):
        super(NVMeoF, self).__init__(*args, **kwargs)
        self.run = True

    def _print_log(self, ret, out, err, cmd):
        logger.info(f"logging command: {cmd} *** ret:{str(ret)}, out:{str(out)}, err: {str(err)}")

    def _mon_cmd(self, cmd: dict):
        ret, out, err = self.mon_command(cmd)
        self._print_log(ret, out, err, cmd)
        if ret != 0:
            raise RuntimeError(f"mon_command failed: {cmd}, ret={ret}, out={out}, err={err}")
        return ret, out, err

    def _pool_exists(self, pool_name: str) -> bool:
        logger.info(f"checking if pool {pool_name} exists")
        pool_exists = self.rados.pool_exists(pool_name)
        if pool_exists:
            logger.info(f"pool {pool_name} already exists")
        else:
            logger.info(f"pool {pool_name} doesnt exist")
        return pool_exists

    def _create_pool(self, pool_name: str, pg_num: int):
        create_cmd = {
            'prefix': 'osd pool create',
            'pool': pool_name,
            'pg_num': pg_num,
            'pool_type': 'replicated',
            'yes_i_really_mean_it': True
        }
        try:
            self._mon_cmd(create_cmd)
            logger.info(f"Pool '{pool_name}' created.")
        except RuntimeError as e:
            if 'already exists' in str(e):
                logger.info(f"Pool '{pool_name}' already exists.", exc_info=True)
            else:
                logger.error(f"Error creating pool '{pool_name}': {e}", exc_info=True)
                raise

    def _enable_rbd_application(self, pool_name: str):
        cmd = {
            'prefix': 'osd pool application enable',
            'pool': pool_name,
            'app': 'rbd',
        }
        try:
            self._mon_cmd(cmd)
            logger.info(f"'rbd' application enabled on pool '{pool_name}'.")
        except RuntimeError as e:
            msg = str(e)
            if "already enabled" in msg:
                logger.info(f"'rbd' application already enabled on '{pool_name}'.", exc_info=True)
            else:
                logger.error(
                    f"Failed to enable 'rbd' application on '{pool_name}': {msg}",
                    exc_info=True
                )
                raise

    def _rbd_pool_init(self, pool_name: str):
        # Idempotent; safe to call multiple times
        with self.rados.open_ioctx(pool_name) as ioctx:
            rbd.RBD().pool_init(ioctx, False)
        logger.info(f"RBD pool_init completed on '{pool_name}'.")

    def _create_pool_if_not_exists(self, pool_name: str, pg_num: int):
        if not self._pool_exists(pool_name):
            self._create_pool(pool_name, pg_num)
        self._enable_rbd_application(pool_name)
        self._rbd_pool_init(pool_name)

    def serve(self):
        try:
            pg_num = self.get_module_option('metadata_pool_pg_num')
            pool_name = self.get_module_option('metadata_pool_name')

            logger.info(f"Starting NVMeoF module. Checking if pool '{pool_name}' exists.")
            self._create_pool_if_not_exists(pool_name, pg_num)

            while self.run:
                time.sleep(10)
        except Exception as e:
            logger.error(f"NVMeoF serve() encountered an error: {e}", exc_info=True)
            # Allow mgr to keep the module loaded

    def shutdown(self):
        logger.info("Shutting down NVMeoF module.")
        self.run = False

    @CLIReadCommand('ping')
    def hello(self) -> HandleCommandResult:
        return HandleCommandResult(stdout='pong')
