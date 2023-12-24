import subprocess
import sys
from subprocess import STDOUT
from typing import Iterable, List, Optional, Union

from autohooks.api import error, ok
from autohooks.api.git import (
    get_staged_status,
    stage_files_from_status_list,
    stash_unstaged_changes,
)
from autohooks.api.path import match
from autohooks.config import Config
from autohooks.precommit.run import ReportProgress
from autohooks.terminal import out

DEFAULT_INCLUDE = ("*.toml", "poetry.lock")
DEFAULT_ARGUMENTS = ()


def _check_toml_sort_installed() -> None:
    try:
        import toml_sort  # pylint: disable=unused-import, import-outside-toplevel # noqa: F401,E501
    except ImportError:
        raise RuntimeError(
            "Could not find toml_sort. "
            "Please add toml_sort to your python environment."
        ) from None

    try:
        subprocess.check_output(["poetry", "sort", "-h"])
    except subprocess.CalledProcessError:
        raise RuntimeError(
            "Could not find poetry dependency sort plugin. "
            "Please install it via `poetry self add poetry-plugin-sort`."
        ) from None


def _get_toml_sort_config(config: Config) -> Config:
    return config.get("tool", "autohooks", "plugins", "toml_sort")


def _ensure_iterable(value: Union[str, List[str]]) -> List[str]:
    if isinstance(value, str):
        return [value]
    return value


def _get_include_from_config(config: Optional[Config]) -> Iterable[str]:
    if not config:
        return DEFAULT_INCLUDE

    toml_sort_config = _get_toml_sort_config(config)
    include = _ensure_iterable(toml_sort_config.get_value("include", DEFAULT_INCLUDE))

    return include


def _get_toml_sort_arguments(config: Optional[Config]) -> Iterable[str]:
    if not config:
        return DEFAULT_ARGUMENTS

    toml_sort_config = _get_toml_sort_config(config)
    arguments = _ensure_iterable(
        toml_sort_config.get_value("arguments", DEFAULT_ARGUMENTS)
    )

    return arguments


def precommit(
    config: Optional[Config] = None,
    report_progress: Optional[ReportProgress] = None,
    **kwargs,  # pylint: disable=unused-argument
) -> int:
    """Run `poetry sort` and toml-sort on commit."""
    _check_toml_sort_installed()

    include = _get_include_from_config(config)
    files = [f for f in get_staged_status() if match(f.path, include)]

    if report_progress:
        report_progress.init(len(files) + 1)

    ret = 0
    arguments = ["toml-sort"]
    arguments.extend(_get_toml_sort_arguments(config))

    with stash_unstaged_changes(files):
        try:
            args = ["poetry", "sort"]
            subprocess.check_output(args, stderr=STDOUT)
            ok("Running `poetry sort`")
            if report_progress:
                report_progress.update()
        except subprocess.CalledProcessError as e:
            ret = e.returncode
            error("Running `poetry sort`")
            lint_errors = e.stdout.decode(
                encoding=sys.getdefaultencoding(), errors="replace"
            ).split("\n")
            for line in lint_errors:
                out(line)

        for f in files:
            try:
                args = arguments.copy()
                args.append(str(f.absolute_path()))
                subprocess.check_output(args, stderr=STDOUT)
                ok(f"Running toml_sort on {f.path}")
                if report_progress:
                    report_progress.update()
            except subprocess.CalledProcessError as e:
                ret = e.returncode
                error(f"Running toml_sort on {f.path}")
                lint_errors = e.stdout.decode(
                    encoding=sys.getdefaultencoding(), errors="replace"
                ).split("\n")
                for line in lint_errors:
                    out(line)

        stage_files_from_status_list(files)

    return ret
