from copytrader.config import Settings, is_valid_address

VALID = "0x" + "a" * 40


def test_address_validation():
    assert is_valid_address(VALID)
    assert not is_valid_address("0x...")
    assert not is_valid_address("")


def test_dry_run_does_not_require_private_key():
    assert Settings(target_wallet=VALID).validate() == []


def test_live_mode_requires_credentials():
    errors = Settings(target_wallet=VALID, dry_run=False).validate()
    assert any("PRIVATE_KEY" in e for e in errors)
    assert any("FUNDER_ADDRESS" in e for e in errors)


def test_private_key_is_hidden_from_repr():
    assert "secret" not in repr(Settings(private_key="secret"))


def test_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("TARGET_WALLET", VALID)
    monkeypatch.setenv("COPY_RATIO_PERCENT", "25")
    monkeypatch.setenv("DRY_RUN", "false")
    settings = Settings.from_env(tmp_path / "missing.env")
    assert settings.target_wallet == VALID
    assert settings.copy_ratio_percent == 25
    assert settings.dry_run is False
