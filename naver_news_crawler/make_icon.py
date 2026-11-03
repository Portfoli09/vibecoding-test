"""앱 아이콘(app.ico)을 생성한다. 빌드 전에 한 번만 실행하면 된다. (pip install pillow)"""

from PIL import Image, ImageDraw

SIZE = 256


def make_icon(path: str = "app.ico") -> None:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))

    # 보라 -> 분홍 -> 주황 대각선 그라데이션 (앱 배너와 같은 색)
    stops = [(124, 58, 237), (219, 39, 119), (249, 115, 22)]
    gradient = Image.new("RGBA", (SIZE, SIZE))
    px = gradient.load()
    for y in range(SIZE):
        for x in range(SIZE):
            t = (x + y) / (2 * (SIZE - 1)) * (len(stops) - 1)
            i = min(int(t), len(stops) - 2)
            f = t - i
            a, b = stops[i], stops[i + 1]
            px[x, y] = tuple(round(a[k] + (b[k] - a[k]) * f) for k in range(3)) + (255,)

    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle((8, 8, SIZE - 8, SIZE - 8), radius=56, fill=255)
    img.paste(gradient, (0, 0), mask)

    # 신문 모양: 흰 종이 + 제목 줄 + 사진 상자 + 본문 줄
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((52, 60, 204, 196), radius=14, fill=(255, 255, 255, 245))
    d.rounded_rectangle((70, 78, 186, 96), radius=6, fill=(124, 58, 237))
    d.rounded_rectangle((70, 110, 120, 160), radius=6, fill=(219, 39, 119))
    for y in (112, 128, 144):
        d.rounded_rectangle((132, y, 186, y + 8), radius=4, fill=(148, 163, 184))
    d.rounded_rectangle((70, 172, 186, 180), radius=4, fill=(148, 163, 184))

    img.save(path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


if __name__ == "__main__":
    make_icon()
    print("app.ico 생성 완료")
