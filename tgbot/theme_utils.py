import os

from tgbot.config import SLUG_TO_CATEGORY


def theme_extensions(device: str) -> tuple[str, ...]:
    return {
        "ios": (".tgios-theme",),
        "android": (".attheme",),
        "windows": (".tdesktop-theme", ".tgdesktop-theme"),
    }.get(device, tuple())


def theme_extension(device: str) -> str:
    exts = theme_extensions(device)
    return exts[0] if exts else ""


def is_theme_file(filename: str, device: str) -> bool:
    return any(filename.endswith(ext) for ext in theme_extensions(device))


def resolve_theme_file(folder: str, theme_name: str, device: str) -> str | None:
    for ext in theme_extensions(device):
        candidate = os.path.join(folder, f"{theme_name}{ext}")
        if os.path.exists(candidate):
            return candidate
    return None


def resolve_device_folder(device: str) -> str:
    folder = os.path.join("themes", device)
    if os.path.isdir(folder):
        return folder
    if device == "android":
        fallback = os.path.join("themes", "andriod")
        if os.path.isdir(fallback):
            return fallback
    return folder


def find_theme_preview(folder: str, theme_name: str) -> str | None:
    same_name_jpg = os.path.join(folder, f"{theme_name}.jpg")
    legacy_preview = os.path.join(folder, f"{theme_name}_preview.jpg")
    if os.path.exists(same_name_jpg):
        return same_name_jpg
    if os.path.exists(legacy_preview):
        return legacy_preview
    return None


def get_themes_page_data(device: str, category_slug: str, page: int = 0) -> tuple[dict | None, str | None]:
    category = SLUG_TO_CATEGORY.get(category_slug)
    if not category:
        return None, "❌ Категория не найдена"

    folder = os.path.join(resolve_device_folder(device), category)
    if not os.path.exists(folder):
        return None, "❌ Темы не найдены"

    themes = sorted(
        {
            os.path.splitext(file)[0]
            for file in os.listdir(folder)
            if not file.startswith(".") and is_theme_file(file, device)
        }
    )
    if not themes:
        return None, "❌ Темы не найдены"

    total_pages = len(themes)
    page = max(0, min(page, total_pages - 1))
    current_theme = themes[page]
    return {
        "category": category,
        "folder": folder,
        "themes": themes,
        "page": page,
        "total_pages": total_pages,
        "current_theme": current_theme,
        "preview_file": find_theme_preview(folder, current_theme),
    }, None
