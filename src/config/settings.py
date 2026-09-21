"""Environment configuration and Base URL resolution.

The single source of truth is ``environments.yaml``, which sits next to this
module. Environment variables are overrides only, so a run can be re-pointed at
another environment without touching code, and nothing breaks for someone who
just clones the repository.

Resolution order (highest priority first)::

    explicit argument  ->  environment variable  ->  environments.yaml

Example::

    load_settings()                                    # prism, from environments.yaml
    load_settings(base_url="https://staging.example")  # ad-hoc URL
    PISMO_ENV=staging PISMO_BASE_URL=... pytest -m smoke
"""

import os
import yaml

from pathlib import Path
from typing import Any, Mapping
from dataclasses import dataclass

DEFAULT_CONFIG_FILE = Path(__file__).with_name("environments.yaml")

ENV_ENVIRONMENT = "PISMO_ENV"
ENV_BASE_URL = "PISMO_BASE_URL"
ENV_TIMEOUT_S = "PISMO_TIMEOUT_S"

DEFAULT_TIMEOUT_S = 10.0


class ConfigError(RuntimeError):
    """Raised when the configuration is missing, malformed or unusable."""


@dataclass(frozen=True)
class Settings:
    """Everything the HTTP layer needs in order to talk to one environment."""

    environment: str
    base_url: str
    timeout_s: float
    headers: Mapping[str, str]
    config_path: Path

    def describe(self) -> str:
        """One-line summary, printed in the pytest header of every run."""
        return (
            f"environment={self.environment} base_url={self.base_url} "
            f"timeout={self.timeout_s}s config={self.config_path}"
        )


def load_settings(
    *,
    environment: str | None = None,
    base_url: str | None = None,
    timeout_s: float | None = None,
    config_path: Path | str | None = None,
) -> Settings:
    """Build :class:`Settings` from the YAML file plus any overrides."""
    path = Path(config_path) if config_path is not None else DEFAULT_CONFIG_FILE
    config = _read_config(path)
    environments = config.get("environments") or {}
    name = _resolve_environment_name(environment, config, environments)
    profile = _profile(environments[name], config.get("defaults"), path)

    resolved_base_url = str(
        base_url or _env_or_none(ENV_BASE_URL) or profile.get("base_url") or ""
    ).strip()
    if not resolved_base_url:
        raise ConfigError(
            f"No base_url configured for environment '{name}'. Set environments.{name}.base_url "
            f"in {path} or export {ENV_BASE_URL} (or pass --base-url)."
        )

    return Settings(
        environment=name,
        base_url=resolved_base_url.rstrip("/"),
        timeout_s=_resolve_timeout_s(timeout_s, profile, path),
        headers=_default_headers(),
        config_path=path,
    )


def _read_config(path: Path) -> dict[str, Any]:
    """Load the YAML document, tolerating an empty file."""
    if not path.is_file():
        raise ConfigError(f"Configuration file not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ConfigError(f"Configuration file must contain a YAML mapping: {path}")
    return data


def _env_or_none(name: str) -> str | None:
    """Read an override, treating a blank value as unset."""
    value = os.environ.get(name, "").strip()
    return value or None


def _resolve_environment_name(
    requested: str | None, config: Mapping[str, Any], environments: Mapping[str, Any]
) -> str:
    if not isinstance(environments, dict) or not environments:
        raise ConfigError("No 'environments' defined in the configuration file.")
    name = requested or _env_or_none(ENV_ENVIRONMENT) or config.get("environment")
    if not name:
        raise ConfigError(
            "No environment selected. Set 'environment' in the configuration file, "
            f"export {ENV_ENVIRONMENT} or pass --env."
        )
    if name not in environments:
        raise ConfigError(
            f"Unknown environment '{name}'. Configured environments: "
            f"{', '.join(sorted(environments))}."
        )
    return str(name)


def _profile(block: Any, defaults: Any, path: Path) -> dict[str, Any]:
    """Merge the shared ``defaults`` block with one environment block."""
    if block is not None and not isinstance(block, dict):
        raise ConfigError(f"Each environment in {path} must be a mapping, got: {block!r}")
    if defaults is not None and not isinstance(defaults, dict):
        raise ConfigError(f"'defaults' in {path} must be a mapping, got: {defaults!r}")
    return {**(defaults or {}), **(block or {})}


def _resolve_timeout_s(explicit: float | None, profile: Mapping[str, Any], path: Path) -> float:
    if explicit is not None:
        return _to_float(explicit, source="load_settings(timeout_s=...)")
    from_env = _env_or_none(ENV_TIMEOUT_S)
    if from_env is not None:
        return _to_float(from_env, source=ENV_TIMEOUT_S)
    return _to_float(profile.get("timeout_s", DEFAULT_TIMEOUT_S), source=f"{path} (timeout_s)")


def _to_float(raw: Any, *, source: str) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"timeout_s must be a number, got {raw!r} from {source}") from exc
    if value <= 0:
        raise ConfigError(f"timeout_s must be greater than zero, got {value} from {source}")
    return value


def _default_headers() -> dict[str, str]:
    """Headers sent with every request: content negotiation only.

    Authentication is deliberately not implemented: the contract confirms no
    mechanism (C3a finding: "authentication / authorization requirement is absent"),
    so the framework must not invent one. When the mechanism is confirmed, resolve
    the credential here and every client picks it up from one place.
    """
    return {"Accept": "application/json", "Content-Type": "application/json"}
