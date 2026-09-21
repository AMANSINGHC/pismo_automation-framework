"""Run-wide pytest configuration: target environment selection and reporting.

The tests never build URLs, sessions or payloads themselves: they receive a
service client already wired to whichever environment the run selected. Target
selection is documented in ``src/config/environments.yaml`` and available per
run via ``pytest --env``/``--base-url``.

The pieces that configure a *run* rather than a test package live here, at the
repository root: the CLI options, the header that states which environment a
report exercised, the session-scoped ``settings`` fixture, and the two report
artifacts (JUnit XML + HTML) that every run writes under ``reports/``. The
service-client fixtures built on top of them stay in ``tests/conftest.py``.
"""

import pytest

from pathlib import Path
from collections.abc import Callable
from src.config.settings import ConfigError, Settings, load_settings

REPORT_DIR = "reports"
JUNIT_REPORT = "junit.xml"
HTML_REPORT = "report.html"


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


def pytest_configure(config: pytest.Config) -> None:
    """Give every run the same two artifacts under ``reports/``.

    pytest creates neither a report file nor its parent directory and a fresh
    clone has no ``reports/``, so the directory is made here: a missing directory
    must not be able to fail a run, and neither should forgetting a flag.

    Only options a run left unset are defaulted, so an explicit ``--junitxml`` or
    ``--html`` (a CI job pointing at its own results directory, say) still wins.
    """
    has_html = _has_html_plugin(config)
    if has_html:
        _add_environment_to_html(config)

    wants_junit = config.option.xmlpath is None
    wants_html = has_html and config.option.htmlpath is None
    if not (wants_junit or wants_html):
        return

    reports = Path(config.rootpath) / REPORT_DIR
    reports.mkdir(exist_ok=True)
    if wants_junit:
        config.option.xmlpath = str(reports / JUNIT_REPORT)
    if wants_html:
        config.option.htmlpath = str(reports / HTML_REPORT)
        # Left alone, the plugin writes an assets/ stylesheet next to the report,
        # which makes the artifact a directory rather than one attachable file.
        if hasattr(config.option, "self_contained_html"):
            config.option.self_contained_html = True


def _has_html_plugin(config: pytest.Config) -> bool:
    """pytest-html is a package of its own, so its report is only defaulted if it is there."""
    return config.pluginmanager.hasplugin("html") and hasattr(config.option, "htmlpath")


def pytest_report_header(config: pytest.Config) -> str:
    """Make every report state which environment it exercised."""
    return f"pismo: {_environment(config)}"


@pytest.fixture(scope="session", autouse=True)
def _environment_in_junit_xml(
    record_testsuite_property: Callable[[str, object], None],
    pytestconfig: pytest.Config,
) -> None:
    """Put the line the console header prints into the JUnit XML as a property.

    CI usually keeps only the XML, so the artifact has to say what it exercised.
    ``record_testsuite_property`` is pytest's own session-scoped fixture, and a
    documented no-op when a run writes no XML.
    """
    record_testsuite_property("pismo", _environment(pytestconfig))


def _environment(config: pytest.Config) -> str:
    """One line describing the target, or why the run is not configured to have one."""
    try:
        return _resolve_settings(config).describe()
    except ConfigError as exc:
        return f"not configured ({exc})"


def _add_environment_to_html(config: pytest.Config) -> None:
    """Let the HTML report state the target too, not just the console.

    pytest-html documents this route: pytest-metadata owns the environment table
    and fills its stash entry from its own ``tryfirst`` ``pytest_configure``,
    which therefore runs before this hook. pytest-html is an optional package
    here, so this import is kept local to the code that needs it.
    """
    try:
        from pytest_metadata.plugin import metadata_key
    except ImportError:
        return

    if metadata_key in config.stash:
        config.stash[metadata_key]["pismo"] = _environment(config)


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
