import random
import string
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont


def generate_captcha_text(length: int = 5) -> str:
    chars = string.ascii_uppercase + string.digits
    chars = chars.replace('O', '').replace('0', '').replace('I', '').replace('1', '')
    return ''.join(random.choices(chars, k=length))


def generate_captcha_image(text: str) -> BytesIO:
    width, height = 200, 70
    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf", 32)
    except:
        font = ImageFont.load_default()

    for i, char in enumerate(text):
        x = 15 + i * 35
        y = random.randint(10, 30)
        draw.text((x, y), char, fill=(random.randint(0, 100), random.randint(0, 100), random.randint(0, 100)),
                  font=font)

    for _ in range(random.randint(4, 8)):
        x0 = random.randint(0, width)
        y0 = random.randint(0, height)
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        draw.line((x0, y0, x1, y1), fill=(random.randint(100, 200), random.randint(100, 200), random.randint(100, 200)),
                  width=2)

    buffer = BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer


def verify_captcha(user_input: str, correct_text: str) -> bool:
    return user_input.strip().upper() == correct_text