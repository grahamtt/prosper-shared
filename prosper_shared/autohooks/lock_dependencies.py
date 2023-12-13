import re
import subprocess
import sys
from subprocess import STDOUT
from typing import Iterable, List, Optional, Union

from autohooks.api import error, ok
from autohooks.api.git import stage_files, stash_unstaged_changes
from autohooks.config import Config
from autohooks.precommit.run import ReportProgress
from autohooks.terminal import out

DEFAULT_ARGUMENTS = ()


def _get_lock_dependencies_config(config: Config) -> Config:
    return config.get("tool", "autohooks", "plugins", "lock_dependencies")


def _ensure_iterable(value: Union[str, List[str]]) -> List[str]:
    if isinstance(value, str):
        return [value]
    return value


def _get_lock_dependencies_arguments(config: Optional[Config]) -> Iterable[str]:
    if not config:
        return DEFAULT_ARGUMENTS

    lock_dependencies_config = _get_lock_dependencies_config(config)
    arguments = _ensure_iterable(
        lock_dependencies_config.get_value("arguments", DEFAULT_ARGUMENTS)
    )

    return arguments


def precommit(
    config: Optional[Config] = None,
    report_progress: Optional[ReportProgress] = None,
    **kwargs,  # pylint: disable=unused-argument
) -> int:
    """Runs `poetry lock` to update dependencies.

    Args:
        config (Optional[Config]): The full config for the project. The config for this tool will be extracted from it
            later.
        report_progress (Optional[ReportProgress]): If set, the hook will use this to send updates when work is
            finished.
        **kwargs: Not used.

    Returns:
        int: Indicates the output status of the underlying process. 0 -> success, >0 -> failure
    """
    if report_progress:
        report_progress.init(1)

    ret = 0
    arguments = ["poetry"]
    arguments.extend(_get_lock_dependencies_arguments(config))

    with stash_unstaged_changes():
        try:
            args = arguments.copy()
            subprocess.check_output(args, stderr=STDOUT)
            ok("Running `poetry lock`")
            if report_progress:
                report_progress.update()
        except subprocess.CalledProcessError as e:
            ret = e.returncode
            error("Running `poetry lock`")
            lint_errors: List[str] = e.stdout.decode(
                encoding=sys.getdefaultencoding(), errors="replace"
            ).split("\n")
            for line in lint_errors:
                if re.match(r"[ ]{4}[0-9]+:", line):
                    out(line)

        stage_files(["poetry.lock"])

    return ret
