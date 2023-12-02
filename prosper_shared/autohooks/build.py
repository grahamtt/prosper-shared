import subprocess
import sys
from subprocess import STDOUT
from typing import List, Optional, Tuple, Union

from autohooks.config import Config
from autohooks.precommit.run import ReportProgress
from autohooks.terminal import error, ok, out

DEFAULT_ARGUMENTS = ()


def _get_build_config(config: Config) -> Config:
    return config.get("tool", "autohooks", "plugins", "build")


def _ensure_iterable(value: Union[str, List[str]]) -> List[str]:
    if isinstance(value, str):
        return [value]
    return value


def _get_build_arguments(config: Optional[Config]) -> Union[List[str], Tuple[str]]:
    if not config:
        return DEFAULT_ARGUMENTS

    autoimport_config = _get_build_config(config)
    arguments = _ensure_iterable(
        autoimport_config.get_value("arguments", DEFAULT_ARGUMENTS)
    )

    return arguments


def precommit(
    config: Optional[Config] = None,
    report_progress: Optional[ReportProgress] = None,
    **kwargs,  # pylint: disable=unused-argument
) -> int:
    """Pre-commit hook to build project.

    Args:
        config (Optional[Config]): The auto-commit config.
        report_progress (Optional[ReportProgress]): Used to report progress, if provided.
        **kwargs: Any other unnamed args.

    Returns:
        int: The return code
    """
    if report_progress:
        report_progress.init(1)

    ret = 0
    arguments = ["poetry", "build"]
    arguments.extend(_get_build_arguments(config))

    try:
        subprocess.check_output(arguments, stderr=STDOUT)
        ok("Running build")
        if report_progress:
            report_progress.update()
    except subprocess.CalledProcessError as e:
        error("Running build")
        ret = e.returncode
        lint_errors = e.stdout.decode(
            encoding=sys.getdefaultencoding(), errors="replace"
        ).split("\n")
        for line in lint_errors:
            out(line)

    return ret
