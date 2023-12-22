"""Contains utility methods and classes for merging multiple configs."""

from copy import deepcopy
from typing import List

from deepmerge import always_merger


def _merge_config(configs: List[dict]) -> dict:
    """Compiles all the config sources into a single config.

    Args:
        configs (List[dict]): The configs to merge.

    Returns:
        dict: The merged config.
    """
    conf = {}

    for partial_conf in configs:
        always_merger.merge(conf, deepcopy(partial_conf))

    return conf
