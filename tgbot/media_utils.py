import shutil
import subprocess
from PIL import Image


def build_sticker_png(source_path: str, output_path: str):
    with Image.open(source_path) as img:
        img = img.convert("RGBA")
        resampling = getattr(Image, "Resampling", Image).LANCZOS
        img.thumbnail((512, 512), resampling)
        canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
        offset = ((512 - img.width) // 2, (512 - img.height) // 2)
        canvas.paste(img, offset, img)
        canvas.save(output_path, "PNG")


def extract_sticker_pack_title(raw_text: str | None) -> str | None:
    if not raw_text:
        return None
    text = raw_text.strip()
    if not text:
        return None
    lowered = text.lower()
    for prefix in ("название:", "название", "пак:", "стикерпак:"):
        if lowered.startswith(prefix):
            text = text[len(prefix):].strip()
            break
    if not text:
        return None
    return text[:64]


def build_wallpaper_jpg(source_path: str, output_path: str):
    with Image.open(source_path) as img:
        img = img.convert("RGB")
        resampling = getattr(Image, "Resampling", Image).LANCZOS
        max_side = 1440
        if max(img.width, img.height) > max_side:
            img.thumbnail((max_side, max_side), resampling)
        img.save(output_path, "JPEG", quality=82, optimize=True, progressive=True)


def build_attheme_with_wallpaper(wallpaper_path: str, theme_path: str):
    lines = [
        "dialogBackground=-1",
        "dialogBackgroundGray=-1",
        "dialogTextBlack=-16777216",
        "dialogTextLink=-12732993",
        "dialogTextBlue=-12732993",
        "chat_inBubble=-1",
        "chat_outBubble=-12862209",
        "chat_outBubbleSelected=-14110905",
        "chat_messageTextIn=-16777216",
        "chat_messageTextOut=-1",
        "chat_serviceText=-1",
    ]

    offset = 0
    while True:
        header = f"wallpaperFileOffset={offset}\\n" + "\\n".join(lines) + "\\n"
        new_offset = len(header.encode("utf-8"))
        if new_offset == offset:
            break
        offset = new_offset

    with open(theme_path, "wb") as theme_f:
        theme_f.write(header.encode("utf-8"))
        with open(wallpaper_path, "rb") as wall_f:
            theme_f.write(wall_f.read())


def convert_video_to_note(input_path: str, output_path: str):
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        try:
            import imageio_ffmpeg
            ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception as exc:
            raise FileNotFoundError("ffmpeg executable not found") from exc

    command = [
        ffmpeg_bin,
        "-y",
        "-i",
        input_path,
        "-t",
        "59",
        "-vf",
        "crop='min(iw,ih)':'min(iw,ih)',scale=512:512",
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-preset",
        "veryfast",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        output_path,
    ]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
