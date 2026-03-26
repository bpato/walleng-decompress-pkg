"""Internationalization support for walleng-pkg."""

from __future__ import annotations

import json
import locale
from pathlib import Path
from typing import Any

_TRANSLATIONS: dict[str, dict[str, str]] = {}
_CURRENT_LANG = "en"


def get_available_languages() -> list[str]:
    """Get list of available language codes."""
    return list(_TRANSLATIONS.keys())


def get_current_language() -> str:
    """Get current language code."""
    return _CURRENT_LANG


def set_language(lang: str) -> bool:
    """Set the current language.
    
    Args:
        lang: Language code (e.g., 'en', 'es')
        
    Returns:
        True if language was set successfully.
    """
    global _CURRENT_LANG
    if lang in _TRANSLATIONS:
        _CURRENT_LANG = lang
        return True
    return False


def detect_system_language() -> str:
    """Detect system language and return matching language code."""
    system_lang = locale.getdefaultlocale()[0]
    if system_lang:
        lang_code = system_lang.split("_")[0].lower()
        if lang_code in _TRANSLATIONS:
            return lang_code
    return "en"


def tr(key: str, **kwargs: Any) -> str:
    """Translate a key to the current language.
    
    Args:
        key: Translation key.
        **kwargs: Format arguments for placeholders like {n}.
        
    Returns:
        Translated string or the key if not found.
    """
    if _CURRENT_LANG not in _TRANSLATIONS:
        return key
    
    text = _TRANSLATIONS[_CURRENT_LANG].get(key, key)
    
    if kwargs:
        text = text.format(**kwargs)
    
    return text


def load_translations(translations_dir: Path | None = None) -> None:
    """Load all translation files from the translations directory.
    
    Args:
        translations_dir: Path to translations directory. Defaults to package translations.
    """
    global _TRANSLATIONS
    
    if translations_dir is None:
        translations_dir = Path(__file__).parent / "translations"
    
    _TRANSLATIONS = {}
    
    if not translations_dir.exists():
        return
    
    for json_file in translations_dir.glob("*.json"):
        lang_code = json_file.stem
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                _TRANSLATIONS[lang_code] = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass


def init_i18n(lang: str | None = None) -> str:
    """Initialize internationalization.
    
    Args:
        lang: Optional language code to force. If None, auto-detects from system.
        
    Returns:
        The language code that was set.
    """
    load_translations()
    
    if lang and lang in _TRANSLATIONS:
        set_language(lang)
    else:
        detected = detect_system_language()
        set_language(detected)
    
    return _CURRENT_LANG
