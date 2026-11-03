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

    # 분석 차트 모양: 어두운 패널 + 거래량 막대 + 상승 추세 종가선
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((40, 48, 216, 208), radius=18, fill=(15, 23, 42, 240))
    for gy in (88, 128, 168):
        d.line((56, gy, 200, gy), fill=(51, 65, 85, 255), width=2)
    for i, h in enumerate([18, 30, 22, 38, 26, 44, 34]):
        x = 62 + i * 20
        d.rectangle((x, 196 - h, x + 12, 196), fill=(100, 116, 139, 255))
    points = [(58, 160), (82, 138), (104, 150), (128, 112), (150, 124), (176, 84), (200, 68)]
    d.polygon(points + [(200, 196), (58, 196)], fill=(59, 130, 246, 70))
    d.line(points, fill=(96, 165, 250), width=8, joint="curve")
    d.ellipse((190, 58, 210, 78), fill=(52, 211, 153))

    img.save(path, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


if __name__ == "__main__":
    make_icon()
    print("app.ico 생성 완료")
