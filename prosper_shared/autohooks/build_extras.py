import subprocess
import sys
from subprocess import STDOUT
from typing import List, Optional, Union

from autohooks.api.git import stage_files
from autohooks.config import Config
from autohooks.precommit.run import ReportProgress
from autohooks.terminal import error, ok, out

DEFAULT_ARGUMENTS = []


def _get_build_extras_config(config: Config) -> Config:
    return config.get("tool", "autohooks", "plugins", "build_extras")


def _ensure_iterable(value: Union[str, List[str]]) -> List[str]:
    if isinstance(value, str):
        return [value]
    return value


def _get_affected_files(config: Optional[Config]) -> List[str]:
    if not config:
        return DEFAULT_ARGUMENTS

    autoimport_config = _get_build_extras_config(config)
    arguments = _ensure_iterable(
        autoimport_config.get_value("affected_files", DEFAULT_ARGUMENTS)
    )

    return arguments


def _get_commands(config: Optional[Config]) -> List[List[str]]:
    if not config:
        return DEFAULT_ARGUMENTS

    autoimport_config = _get_build_extras_config(config)
    arguments = _ensure_iterable(
        autoimport_config.get_value("commands", DEFAULT_ARGUMENTS)
    )

    return arguments


def precommit(
    config: Optional[Config] = None,
    report_progress: Optional[ReportProgress] = None,
    **kwargs,  # pylint: disable=unused-argument
) -> int:
    """Pre-commit hook to build_extras project.

    Args:
        config (Optional[Config]): The auto-commit config.
        report_progress (Optional[ReportProgress]): Used to report progress, if provided.
        **kwargs: Any other unnamed args.

    Returns:
        int: The return code
    """
    ret = 0
    commands = _get_commands(config)
    affected_files = _get_affected_files(config)

    if report_progress:
        report_progress.init(len(commands))

    try:
        for command in commands:
            subprocess.check_output(command, shell=True, stderr=STDOUT)
            ok("Running build_extras")
            if report_progress:
                report_progress.update()
    except subprocess.CalledProcessError as e:
        error("Running build_extras")
        ret = e.returncode
        lint_errors = e.stdout.decode(
            encoding=sys.getdefaultencoding(), errors="replace"
        ).split("\n")
        for line in lint_errors:
            out(line)

    stage_files(affected_files)

    return ret
