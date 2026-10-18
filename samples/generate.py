"""Generate fictional samples; no real patient or product information."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).parent
public = root.parent / "frontend" / "public" / "samples"
public.mkdir(parents=True, exist_ok=True)
for kind, title, name, strength, dose, instruction in [
    ("medication", "MEDICATION GUIDE", "Demo Medication A", "5 mg", "1 tablet", "Once daily at the time confirmed with your pharmacist."),
    ("supplement", "SUPPLEMENT LABEL", "Demo Supplement B", "100 mg per capsule", "1 capsule", "Once daily. Follow your existing confirmed instructions."),
]:
    image = Image.new("RGB", (900, 1050), "#faf9f0")
    draw = ImageDraw.Draw(image)
    def font(size):
        try:
            return ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", size)
        except OSError:
            return ImageFont.load_default(size=size)
    draw.rounded_rectangle((45, 45, 855, 1005), radius=22, fill="white", outline="#c6d5c9", width=3)
    draw.text((90, 100), "DOSE TIMER / FICTIONAL SAMPLE", font=font(23), fill="#5f8070")
    draw.text((90, 165), title, font=font(37), fill="#185c50")
    draw.line((90, 245, 810, 245), fill="#d8e2d8", width=2)
    for y, label, value in [(300, "NAME", name), (440, "STRENGTH", strength), (580, "AMOUNT PER DOSE", dose)]:
        draw.text((90, y), label, font=font(20), fill="#78917f")
        draw.text((90, y + 40), value, font=font(32), fill="#293f34")
    draw.text((90, 730), "DIRECTIONS", font=font(20), fill="#78917f")
    if kind == "medication":
        lines = ["Once daily at the time confirmed", "with your pharmacist."]
    else:
        lines = ["Once daily. Follow your existing", "confirmed instructions."]
    for i, line in enumerate(lines):
        draw.text((90, 775 + i * 43), line, font=font(29), fill="#293f34")
    draw.text((90, 925), "SYNTHETIC DATA - NOT FOR MEDICAL USE", font=font(20), fill="#a17946")
    image.save(root / f"{kind}.png")
    image.save(public / f"{kind}.png")
    payload = {"items": [{"name": name, "strength": strength, "dose": dose, "instruction": instruction}],
        "warnings": ["Fictional sample: simulated transcription, not a live AI result. No exact clock time is printed. Enter and confirm your own reminder time."]}
    (root / f"{kind}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
