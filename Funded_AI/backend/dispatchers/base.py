import os
from backend.config import PROMPT_DIR


def load_marketing_prompt(lang: str) -> str:
    if not lang or not isinstance(lang, str):
        raise ValueError("lang parametresi geçerli bir string olmalı")

    system_path = os.path.join(PROMPT_DIR, "marketing_system.txt")
    lang_path = os.path.join(PROMPT_DIR, f"marketing_{lang}.txt")
    default_lang_path = os.path.join(PROMPT_DIR, "marketing_en.txt")

    if not os.path.exists(system_path):
        raise FileNotFoundError(f"Sistem prompt dosyası bulunamadı: {system_path}")

    with open(system_path, encoding="utf-8") as f:
        system = f.read().strip()

    prompt_path = lang_path if os.path.exists(lang_path) else default_lang_path

    if not os.path.exists(prompt_path):
        raise FileNotFoundError(
            f"Dil prompt dosyası bulunamadı: {prompt_path} (lang={lang})"
        )

    with open(prompt_path, encoding="utf-8") as f:
        lang_prompt = f.read().strip()

    return system + "\n\n" + lang_prompt