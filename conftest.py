"""Run-wide pytest configuration: target environment selection.

The tests never build URLs, sessions or payloads themselves: they receive a
service client already wired to whichever environment the run selected. Target
selection is documented in ``src/config/environments.yaml`` and available per
run via ``pytest --env``/``--base-url``.

The pieces that configure a *run* rather than a test package live here, at the
repository root: the CLI options, the header that states which environment a run
exercised, and the session-scoped ``settings`` fixture. The service-client
fixtures built on top of them stay in ``tests/conftest.py``.
"""

import pytest

from src.config.settings import ConfigError, Settings, load_settings


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("pismo")
    group.addoption(
        "--env",
        dest="pismo_env",
        default=None,
        metavar="NAME",
        help="Environment from settings (prism|staging|test). Overrides PISMO_ENV.",
    )
    group.addoption(
        "--base-url",
        dest="pismo_base_url",
        default=None,
        metavar="URL",
        help="Base URL of the service under test. Overrides PISMO_BASE_URL.",
    )


def pytest_report_header(config: pytest.Config) -> str:
    """State which environment a run exercises, before the first test starts."""
    return f"pismo: {_environment(config)}"


def _environment(config: pytest.Config) -> str:
    """One line describing the target, or why the run is not configured to have one."""
    try:
        return _resolve_settings(config).describe()
    except ConfigError as exc:
        return f"not configured ({exc})"


def _resolve_settings(config: pytest.Config) -> Settings:
    return load_settings(
        environment=config.getoption("pismo_env"),
        base_url=config.getoption("pismo_base_url"),
    )


@pytest.fixture(scope="session")
def settings(pytestconfig: pytest.Config) -> Settings:
    """Resolved configuration, or a skip when the environment has no base URL."""
    try:
        return _resolve_settings(pytestconfig)
    except ConfigError as exc:
        pytest.skip(str(exc))
