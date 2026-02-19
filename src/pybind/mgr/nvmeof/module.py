import logging
from typing import Any, Tuple

from mgr_module import MgrModule, Option
import rbd

logger = logging.getLogger(__name__)

POOL_NAME = ".nvmeof"
PG_NUM = 1
hello
class NVMeoF(MgrModule):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super(NVMeoF, self).__init__(*args, **kwargs)

    def _print_log(self, ret: int, out: str, err: str, cmd: str) -> None:
        logger.info(f"logging command: {cmd} *** ret:{str(ret)}, out:{out}, err: {err}")

    def _mon_cmd(self, cmd: dict) -> Tuple[int, str, str]:
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
            logger.info(f"pool {pool_name} doesn't exist")
        return pool_exists

    def _create_pool(self, pool_name: str, pg_num: int) -> None:
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
            logger.error(f"Error creating pool '{pool_name}", exc_info=True)
            raise

    def _enable_rbd_application(self, pool_name: str) -> None:
        cmd = {
            'prefix': 'osd pool application enable',
            'pool': pool_name,
            'app': 'rbd',
        }
        try:
            self._mon_cmd(cmd)
            logger.info(f"'rbd' application enabled on pool '{pool_name}'.")
        except RuntimeError as e:
            logger.error(
                f"Failed to enable 'rbd' application on '{pool_name}'",
                exc_info=True
            )
            raise

    def _rbd_pool_init(self, pool_name: str) -> None:
        with self.rados.open_ioctx(pool_name) as ioctx:
            rbd.RBD().pool_init(ioctx, False)
        logger.info(f"RBD pool_init completed on '{pool_name}'.")

    def create_pool_if_not_exists(self) -> None:
        if not self._pool_exists(POOL_NAME):
            self._create_pool(POOL_NAME, PG_NUM)
        self._enable_rbd_application(POOL_NAME)
        self._rbd_pool_init(POOL_NAME)

