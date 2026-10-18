"""Assemble actual CUA screen captures into an exactly three-minute demo.

Only waiting/recovery intervals are cut. Captions are outside the app image.
No app result, reading, report or timing banner is synthesized.
"""
import bisect
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[1]
capture = root / '.local' / 'video-capture'
out = root / '.local' / 'video-edit'
out.mkdir(parents=True, exist_ok=True)
manifest = json.loads((capture / 'manifest.json').read_text(encoding='utf-8'))
frames = manifest['frames']
stamps = [v['at'] for v in frames]
segments = [
    (0, 25.967, 'Dose Timer: medication and supplement reminders in one place.\nLive deployed app on Google Cloud Run; fictional data only.'),
    (25.967, 35, '1. Read a medication guide with Gemini.\nThis is real image analysis. The waiting interval is shortened.'),
    (99, 119, '2. Review the unverified reading.\nCheck the name, strength, dose and original directions.'),
    (148, 169, 'Choose a fixed time from existing instructions, then confirm.\nAI does not recommend doses or times; extraction alone never activates reminders.'),
    (174.799, 195.635, '3. Add a fictional supplement label.\nGemini reads the visible label; the user remains in control.'),
    (195.635, 210.652, 'Review the supplement and confirm its reminder time.\nStrength and amount per dose are kept separate.'),
    (210.652, 224.976, '4. See medication and supplement reminders together.\nBoth reviewed routines now appear in today\'s timeline.'),
    (224.976, 239.874, '5. Jump to a reminder using the labelled DEMO clock.\nThe due alert follows the user-confirmed schedule.'),
    (239.874, 259.647, '6. Mark the reminder as taken.\nThis is an explicit self-report, not verification of ingestion.'),
    (259.647, 270.956, 'Confirmed routines retain their original directions.\nData is isolated per user and stored privately on Google Cloud.'),
    (270.956, 276.544, 'Dose Timer | Gemini + Google Cloud Run\nOpen-page reminders only. No dose or interaction advice.'),
]

font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 26)
small = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 17)
title = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 19)
entries = []
timeline = []
elapsed = 0
for start, end, caption in segments:
    points = [start] + [v for v in stamps if start < v < end] + [end]
    timeline.append({'start': elapsed, 'end': elapsed + end - start, 'source_start': start, 'source_end': end, 'caption': caption})
    for a, b in zip(points, points[1:]):
        index = max(0, bisect.bisect_right(stamps, a) - 1)
        original = capture / Path(frames[index]['file']).name
        screen = Image.open(original).convert('RGB')
        screen.thumbnail((1240, 765), Image.Resampling.LANCZOS)
        # Upscale uniformly to the available picture area, preserving all pixels.
        factor = min(1240 / screen.width, 765 / screen.height)
        screen = screen.resize((round(screen.width * factor), round(screen.height * factor)), Image.Resampling.LANCZOS)
        canvas = Image.new('RGB', (1280, 960), '#f1f6f2')
        draw = ImageDraw.Draw(canvas)
        draw.text((24, 10), 'DOSE TIMER  |  LIVE CLOUD RUN DEMO  |  SYNTHETIC DATA', font=title, fill='#185c50')
        canvas.paste(screen, ((1280 - screen.width) // 2, 45))
        draw.rectangle((0, 820, 1280, 960), fill='#154e43')
        lines = []
        for paragraph in caption.split('\n'):
            line = ''
            for word in paragraph.split():
                proposed = (line + ' ' + word).strip()
                if draw.textlength(proposed, font=font) > 1200:
                    lines.append(line)
                    line = word
                else:
                    line = proposed
            lines.append(line)
        for j, line in enumerate(lines):
            draw.text(((1280 - draw.textlength(line, font=font)) / 2, 836 + j * 31), line, font=font, fill='white')
        draw.text((24, 932), 'Actual deployed UI • Waiting/recovery intervals edited • No narration', font=small, fill='#b8d3c6')
        file = out / f'video-{len(entries):05d}.png'
        canvas.save(file)
        entries.append([file.name, b - a])
    elapsed += end - start

entries[-1][1] += 180 - elapsed
timeline[-1]['end'] = 180
with (out / 'concat.txt').open('w', encoding='utf-8') as f:
    for name, duration in entries:
        f.write(f"file '{name}'\nduration {duration:.6f}\n")
    f.write(f"file '{entries[-1][0]}'\n")
outputs = root / 'outputs'
outputs.mkdir(exist_ok=True)
(outputs / 'demo-video-edit.json').write_text(json.dumps({'duration': 180, 'segments': timeline, 'source': 'Actual CUA captures of the deployed public app', 'audio': 'none'}, indent=2), encoding='utf-8')
print(f'Prepared {len(entries)} captured frames; target duration 180 seconds.')
