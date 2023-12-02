import shutil
from os import remove
from os.path import isdir, isfile
from typing import List, Optional, Tuple, Union

from autohooks.config import Config
from autohooks.precommit.run import ReportProgress

DEFAULT_ARGUMENTS = ("dist",)


def _get_clean_config(config: Config) -> Config:
    return config.get("tool", "autohooks", "plugins", "clean")


def _ensure_iterable(value: Union[str, List[str]]) -> List[str]:
    if isinstance(value, str):
        return [value]
    return value


def _get_files_to_clean(config: Optional[Config]) -> Union[List[str], Tuple[str]]:
    if not config:
        return DEFAULT_ARGUMENTS

    clean_config = _get_clean_config(config)
    arguments = _ensure_iterable(clean_config.get_value("files", DEFAULT_ARGUMENTS))

    return arguments


def precommit(
    config: Optional[Config] = None,
    report_progress: Optional[ReportProgress] = None,
    **kwargs,  # pylint: disable=unused-argument
) -> int:
    """Pre-commit hook to clean up files before the build.

    Args:
        config (Optional[Config]): The auto-commit config.
        report_progress (Optional[ReportProgress]): Used to report progress, if provided.
        **kwargs: Any other unnamed args.

    Returns:
        int: The return code
    """
    ret = 0
    files_to_clean = _get_files_to_clean(config)

    if report_progress:
        report_progress.init(len(files_to_clean))

    for file in files_to_clean:
        if isfile(file):
            remove(file)
        elif isdir(file):
            shutil.rmtree(file)
        report_progress.update()

    return ret
