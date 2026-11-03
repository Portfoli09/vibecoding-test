"""앱 아이콘(app.ico)을 생성한다. 빌드 전에 한 번만 실행하면 된다. (pip install pillow)"""

from PIL import Image, ImageDraw

SIZE = 256


def make_icon(path: str = "app.ico") -> None:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))

    # 파랑 -> 보라 -> 분홍 대각선 그라데이션 (앱 배너와 같은 색)
    stops = [(37, 99, 235), (124, 58, 237), (219, 39, 119)]
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

    # 주식 차트 모양: 흰 패널 + 캔들(상승 빨강 / 하락 파랑) + 상승 추세선
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((44, 52, 212, 204), radius=16, fill=(255, 255, 255, 245))
    candles = [  # (x, 몸통 위, 몸통 아래, 꼬리 위, 꼬리 아래, 상승 여부)
        (76, 150, 180, 140, 188, False),
        (108, 128, 162, 118, 172, True),
        (140, 138, 160, 126, 170, False),
        (172, 92, 136, 80, 146, True),
    ]
    for x, top, bottom, wick_top, wick_bottom, up in candles:
        color = (244, 63, 94) if up else (59, 130, 246)
        d.line((x, wick_top, x, wick_bottom), fill=color, width=4)
        d.rounded_rectangle((x - 11, top, x + 11, bottom), radius=3, fill=color)
    d.line([(64, 176), (108, 140), (140, 150), (190, 78)], fill=(124, 58, 237), width=7, joint="curve")

    img.save(path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


if __name__ == "__main__":
    make_icon()
    print("app.ico 생성 완료")
