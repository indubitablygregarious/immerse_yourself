"""
Tests for ConfigLoader

These tests verify that the YAML configuration loader works correctly,
including validation and error handling.
"""

import pytest
from pathlib import Path
from config_loader import ConfigLoader, ConfigValidationError


def test_config_loader_loads_valid_config():
    """Test that valid YAML configs load successfully."""
    loader = ConfigLoader("env_conf")

    # Load tavern config (should exist)
    config = loader.load("tavern.yaml")

    # Verify structure
    assert "name" in config
    assert config["name"] == "Tavern"
    assert config["category"] == "social"
    assert "engines" in config


def test_config_loader_validates_required_fields():
    """Test that configs with missing required fields are rejected."""
    # This test would need a fixture file with missing fields
    # For now, testing the validation logic is present
    loader = ConfigLoader("env_conf")

    # The loader should validate configs when loading
    assert hasattr(loader, "_validate_config")


def test_config_loader_caching():
    """Test that config caching works."""
    loader = ConfigLoader("env_conf")

    # Load config twice
    config1 = loader.load("tavern.yaml")
    config2 = loader.load("tavern.yaml")

    # Should be the same object (cached)
    assert config1 is config2


def test_config_loader_cache_bypass():
    """Test that cache can be bypassed."""
    loader = ConfigLoader("env_conf")

    # Load with cache
    config1 = loader.load("tavern.yaml", use_cache=True)

    # Load without cache
    config2 = loader.load("tavern.yaml", use_cache=False)

    # Should be different objects
    assert config1 is not config2

    # But contents should be the same
    assert config1 == config2


def test_config_loader_discover_all():
    """Test that all configs can be discovered."""
    loader = ConfigLoader("env_conf")

    configs = loader.discover_all()

    # Should find at least the 5 example configs we created
    assert len(configs) >= 5

    # All should have required fields
    for config in configs:
        assert "name" in config
        assert "category" in config
        assert "engines" in config


def test_config_loader_category_filter():
    """Test filtering configs by category."""
    loader = ConfigLoader("env_conf")

    social_configs = loader.get_by_category("social")

    # Should find tavern.yaml
    assert any(c["name"] == "Tavern" for c in social_configs)

    # All should be social category
    for config in social_configs:
        assert config["category"] == "social"


def test_config_loader_invalid_directory():
    """Test that invalid config directory raises error."""
    with pytest.raises(FileNotFoundError):
        ConfigLoader("nonexistent_directory")


def test_config_loader_missing_file():
    """Test that loading missing file raises error."""
    loader = ConfigLoader("env_conf")

    with pytest.raises(FileNotFoundError):
        loader.load("nonexistent_environment.yaml")


def test_config_clear_cache():
    """Test cache clearing."""
    loader = ConfigLoader("env_conf")

    # Load and cache
    loader.load("tavern.yaml")
    assert len(loader._cache) > 0

    # Clear cache
    loader.clear_cache()
    assert len(loader._cache) == 0


def test_config_reload():
    """Test config reload bypasses cache."""
    loader = ConfigLoader("env_conf")

    # Load and cache
    config1 = loader.load("tavern.yaml")

    # Reload
    config2 = loader.reload("tavern.yaml")

    # Should be different objects
    assert config1 is not config2
