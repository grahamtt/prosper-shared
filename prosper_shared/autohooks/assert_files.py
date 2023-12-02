from os.path import isfile
from typing import List, Optional, Tuple, Union

from autohooks.api import error
from autohooks.config import Config
from autohooks.precommit.run import ReportProgress

DEFAULT_ARGUMENTS = ("dist/coverage.info",)


def _get_assert_files_config(config: Config) -> Config:
    return config.get("tool", "autohooks", "plugins", "assert_files")


def _ensure_iterable(value: Union[str, List[str]]) -> List[str]:
    if isinstance(value, str):
        return [value]
    return value


def _get_files_to_assert_files(
    config: Optional[Config],
) -> Union[List[str], Tuple[str]]:
    if not config:
        return DEFAULT_ARGUMENTS

    assert_files_config = _get_assert_files_config(config)
    arguments = _ensure_iterable(
        assert_files_config.get_value("files", DEFAULT_ARGUMENTS)
    )

    return arguments


def precommit(
    config: Optional[Config] = None,
    report_progress: Optional[ReportProgress] = None,
    **kwargs,  # pylint: disable=unused-argument
) -> int:
    """Pre-commit hook to assert some files are present after the build.

    Args:
        config (Optional[Config]): The auto-commit config.
        report_progress (Optional[ReportProgress]): Used to report progress, if provided.
        **kwargs: Any other unnamed args.

    Returns:
        int: The return code
    """
    ret = 0
    files_to_assert_files = _get_files_to_assert_files(config)

    if report_progress:
        report_progress.init(len(files_to_assert_files))

    for file in files_to_assert_files:
        if isfile(file):
            report_progress.update()
        else:
            ret = 1
            error(f"Path {file} not found or is not a file")

    return ret
