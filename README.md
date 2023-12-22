# prosper-shared

Shared build files for the Python Prosper libraries

[![GitHub Workflow Status (with event)](https://img.shields.io/github/actions/workflow/status/grahamtt/prosper-shared/build-and-release.yml?logo=github)](https://github.com/grahamtt/prosper-shared)
[![PyPI - Version](https://img.shields.io/pypi/v/prosper-shared?label=prosper-shared)](https://pypi.org/project/prosper-shared/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/prosper-shared)
![PyPI - License](https://img.shields.io/pypi/l/prosper-shared)
[![Code Climate coverage](https://img.shields.io/codeclimate/coverage/grahamtt/prosper-shared?logo=codeclimate)](https://codeclimate.com/github/grahamtt/prosper-shared)
[![Code Climate maintainability](https://img.shields.io/codeclimate/maintainability-percentage/grahamtt/prosper-shared?logo=codeclimate)](https://codeclimate.com/github/grahamtt/prosper-shared)
![GitHub commit activity (branch)](https://img.shields.io/github/commit-activity/m/grahamtt/prosper-shared?logo=github)
![GitHub issues](https://img.shields.io/github/issues-raw/grahamtt/prosper-shared?logo=github)

## prosper_shared.autohooks

Pre-commit hooks for use with `autohooks`.

## prosper_shared.omni_config

Util for defining, parsing, merging, validating, and using configs from various sources, including file-based configs,
environment variables, and command-line arguments. This will probably be factored out into an independent library.

## prosper_shared.serde

Util for serializing and deserializing Python objects based on type annotations.

## Configs

Available config values:

```json
{
  "prosper_shared": {
    "serde": {
      "use-decimals": {
        "type": "bool",
        "optional": false,
        "default": true,
        "description": "Floating point values should be parsed as decimals instead of floats."
      },
      "parse-dates": {
        "type": "bool",
        "optional": false,
        "default": true,
        "description": "Date values represented as strings should be parsed into `date` and `datetime` objects. Supports ISO-8601-compliant date strings."
      },
      "parse-enums": {
        "type": "bool",
        "optional": false,
        "default": true,
        "description": "Enum values represented as strings should be parsed into their respective types."
      }
    }
  }
}
```
