"""
SKY STRIKER - 제비우스 스타일 종스크롤 슈팅 게임 (pygame)

조작법
  방향키 / WASD : 이동
  Z / Space    : 공중 사격 (연사). 조준점에 지상 적이 잡히면 폭탄도 자동 투하
  X / Shift    : 지상 폭탄 (조준점 위치에 떨어짐) -> 지상 적만 맞음
  M            : 사운드 켜기/끄기
  P / Esc      : 일시정지
  Enter        : 시작 / 재시작

아이템 (적을 부수면 떨어짐, 금색 수송기는 반드시 아이템을 떨어뜨림)
  P  파워업        : 현재 무기 레벨 +1 (최대 4)
  S  스프레드      : 부채꼴로 퍼지는 연사 무기
  L  레이저        : 적을 관통하는 레이저
  H  호밍          : 적을 쫓아가는 유도 미사일
  B  폭탄 강화     : 폭발 범위 증가, Lv3부터 폭탄 2발 동시 사용
  O  옵션          : 따라다니며 같이 쏘는 보조기 (최대 2기)
  G  실드          : 피격 1회 막아줌 (최대 2겹)
  N  노바          : 화면의 공중 적과 적탄을 한 번에 제거
  1UP              : 목숨 +1
  $  메달          : 보너스 점수 (연속으로 먹을수록 증가)

효과음과 배경음악은 프로그램이 직접 합성하므로 별도 파일이 필요 없습니다.
실행: pip install pygame  후  python shooting.py
"""
import math
import os
import random
import sys
from array import array
from collections import deque

import pygame

# ---------------------------------------------------------------- 설정
WIDTH, HEIGHT = 480, 720
FPS = 60
SCROLL_SPEED = 1.2          # 지형 스크롤 속도 (px/frame)
TILE = 24                   # 지형 타일 크기
SIGHT_DIST = 150            # 플레이어 ~ 폭탄 조준점 거리
BOMB_TIME = 26              # 폭탄 낙하 시간 (frame)
HISCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shooting_hiscore.txt")

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
YELLOW = (255, 230, 90)
RED = (235, 60, 60)
ORANGE = (255, 150, 40)
CYAN = (90, 220, 255)
GOLD = (255, 200, 60)

WEAPON_NAMES = {"spread": "SPREAD", "laser": "LASER", "homing": "HOMING"}


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def aim(x, y, tx, ty, speed, spread=0.0):
    ang = math.atan2(ty - y, tx - x) + spread
    return math.cos(ang) * speed, math.sin(ang) * speed


# ================================================================ 사운드 (직접 합성)
class SoundBank:
    """pygame.mixer로 효과음과 배경음악을 코드로 합성해 재생한다. 오디오 장치가 없으면 조용히 꺼진다."""

    def __init__(self):
        self.ok = False
        self.muted = False
        self.sounds = {}
        self.bgm = None
        self.bgm_channel = None
        try:
            init = pygame.mixer.get_init()
            if not init:
                pygame.mixer.init(22050, -16, 1, 512)
                init = pygame.mixer.get_init()
            self.sr, size, self.channels = init
            if abs(size) != 16:
                return
            pygame.mixer.set_num_channels(24)
            pygame.mixer.set_reserved(1)
            self.bgm_channel = pygame.mixer.Channel(0)
            self._build()
            self.ok = True
        except Exception:
            self.ok = False

    # ---------- 합성 도구
    def tone(self, dur, f0, f1=None, wave="square", vol=0.3, decay=1.0):
        f1 = f0 if f1 is None else f1
        sr = self.sr
        n = int(sr * dur)
        out = [0.0] * n
        ph = 0.0
        for i in range(n):
            t = i / n
            ph += (f0 + (f1 - f0) * t) / sr
            p = ph % 1.0
            if wave == "square":
                v = 1.0 if p < 0.5 else -1.0
            elif wave == "tri":
                v = 4.0 * abs(p - 0.5) - 1.0
            elif wave == "saw":
                v = 2.0 * p - 1.0
            else:
                v = math.sin(ph * math.tau)
            env = (1.0 - t) ** decay
            if i < 30:
                env *= i / 30
            out[i] = v * env * vol
        return out

    def noise(self, dur, vol=0.5, c0=0.6, c1=0.05, decay=1.0):
        n = int(self.sr * dur)
        out = [0.0] * n
        y = 0.0
        for i in range(n):
            t = i / n
            a = c0 + (c1 - c0) * t
            y += a * (random.uniform(-1, 1) - y)
            out[i] = y * vol * (1.0 - t) ** decay
        return out

    @staticmethod
    def mix(*parts):
        n = max(len(p) for p in parts)
        out = [0.0] * n
        for p in parts:
            for i, v in enumerate(p):
                out[i] += v
        return out

    def seq(self, notes, step, wave="square", vol=0.2):
        out = []
        for f in notes:
            if f <= 1:                       # 0 또는 작은 값 = 쉼표
                out += [0.0] * int(self.sr * step)
            else:
                out += self.tone(step, f, wave=wave, vol=vol, decay=0.6)
        return out

    def to_sound(self, samples, volume=1.0):
        buf = array("h")
        stereo = self.channels == 2
        for v in samples:
            s = int(clamp(v, -1.0, 1.0) * 32767)
            buf.append(s)
            if stereo:
                buf.append(s)
        snd = pygame.mixer.Sound(buffer=buf.tobytes())
        snd.set_volume(volume)
        return snd

    # ---------- 효과음 목록
    def _build(self):
        S = self.to_sound
        self.sounds = {
            "shot": S(self.tone(0.06, 1500, 700, "square", 0.12, 1.5)),
            "laser": S(self.tone(0.09, 2400, 1300, "saw", 0.12, 1.2)),
            "missile": S(self.mix(self.noise(0.12, 0.25, 0.8, 0.3), self.tone(0.12, 500, 900, "tri", 0.12))),
            "enemy_shot": S(self.tone(0.07, 900, 500, "tri", 0.10, 1.0), 0.6),
            "hit": S(self.noise(0.04, 0.35, 0.9, 0.6, 1.5), 0.7),
            "bomb_drop": S(self.tone(0.42, 1300, 350, "sine", 0.18, 0.4)),
            "bomb_hit": S(self.mix(self.noise(0.4, 1.1, 0.35, 0.02, 1.2), self.tone(0.3, 140, 40, "sine", 0.4))),
            "explode": S(self.mix(self.noise(0.3, 0.9, 0.5, 0.03, 1.3), self.tone(0.2, 220, 60, "square", 0.08))),
            "explode_big": S(self.mix(self.noise(1.0, 1.4, 0.3, 0.01, 1.0), self.tone(0.8, 110, 25, "sine", 0.5))),
            "player_die": S(self.mix(self.tone(0.9, 900, 50, "square", 0.18, 0.8), self.noise(0.9, 0.8, 0.4, 0.02))),
            "item": S(self.seq([988, 1319, 1976], 0.045, "square", 0.15)),
            "powerup": S(self.mix(self.tone(0.35, 300, 1500, "square", 0.1, 0.5),
                                  self.seq([523, 659, 784, 1047, 1319], 0.07, "tri", 0.2))),
            "oneup": S(self.seq([784, 988, 1175, 1568, 1175, 1568], 0.08, "square", 0.17)),
            "shield": S(self.mix(self.tone(0.3, 600, 200, "sine", 0.35, 0.8), self.tone(0.3, 1210, 410, "sine", 0.12))),
            "nova": S(self.mix(self.noise(1.0, 1.0, 0.9, 0.05, 0.8), self.tone(1.0, 60, 2000, "saw", 0.12, 0.3))),
            "medal": S(self.seq([1568, 2093], 0.05, "square", 0.13)),
            "start": S(self.seq([523, 659, 784, 1047, 784, 1047], 0.09, "square", 0.17)),
            "gameover": S(self.seq([659, 587, 523, 440, 392, 330], 0.16, "tri", 0.3)),
            "alert": S(self.seq([880, 0, 880, 0, 880], 0.09, "square", 0.15)),
        }
        self.bgm = self.to_sound(self._make_bgm(), 0.35)

    def _make_bgm(self):
        """140 BPM, Am-F-G-Em 4마디 루프"""
        sr = self.sr
        step = 60 / 140 / 4
        st = int(sr * step)
        total = st * 64
        buf = [0.0] * total

        def add(pos, samples):
            end = min(total, pos + len(samples))
            for i in range(pos, end):
                buf[i] += samples[i - pos]

        roots = [110.0, 87.31, 98.0, 82.41]
        chords = [[440, 523.25, 659.25], [349.23, 440, 523.25],
                  [392, 493.88, 587.33], [329.63, 392, 493.88]]
        kick = self.tone(0.12, 130, 40, "sine", 0.55, 1.5)
        hat = self.noise(0.03, 0.18, 0.95, 0.9, 2.0)
        for s in range(64):
            bar, k = divmod(s, 16)
            pos = s * st
            if k in (0, 3, 6, 8, 10, 12, 14):
                f = roots[bar] * (2 if k in (6, 14) else 1)
                add(pos, self.tone(step * 1.6, f, wave="tri", vol=0.32, decay=0.7))
            if k in (0, 8):
                add(pos, kick)
            if k % 2 == 0:
                add(pos, hat)
            f = chords[bar][k % 3] * (2 if (k // 4) % 2 else 1)
            add(pos, self.tone(step * 0.9, f, wave="square", vol=0.045, decay=1.2))
        return buf

    # ---------- 재생
    def play(self, name):
        if self.ok and not self.muted and name in self.sounds:
            self.sounds[name].play()

    def start_bgm(self):
        if self.ok and not self.muted:
            self.bgm_channel.play(self.bgm, loops=-1)

    def stop_bgm(self):
        if self.ok:
            self.bgm_channel.stop()

    def toggle(self, playing):
        if not self.ok:
            return
        self.muted = not self.muted
        if self.muted:
            pygame.mixer.stop()
        elif playing:
            self.start_bgm()


# ================================================================ 지형 (종스크롤 배경)
class Terrain:
    """타일 한 줄씩 미리 그려두고 아래로 흘려보내는 무한 스크롤 지형"""

    def __init__(self):
        self.rows = []              # [surface, y, river_x]
        self.t = 0
        self.river_x = WIDTH * 0.62
        self.river_w = 70
        self.road_gap = random.randint(60, 110)
        y = HEIGHT
        while y > -TILE:
            y -= TILE
            surf, rx = self._make_row()
            self.rows.insert(0, [surf, y, rx])

    def _make_row(self):
        self.t += 1
        t = self.t
        surf = pygame.Surface((WIDTH, TILE))

        self.river_x += math.sin(t * 0.045) * 2.2 + random.uniform(-0.8, 0.8)
        self.river_x = clamp(self.river_x, 90, WIDTH - 90)
        self.river_w = clamp(self.river_w + random.uniform(-2, 2), 50, 95)

        cols = WIDTH // TILE
        for i in range(cols):
            x = i * TILE
            shade = random.randint(-8, 8)
            surf.fill((70 + shade, 130 + shade, 60 + shade), (x, 0, TILE, TILE))
            n = (math.sin(i * 0.55 + t * 0.11) + math.sin(i * 0.23 - t * 0.067)
                 + math.sin((i + t) * 0.031))
            if n > 1.2:
                surf.fill((40, 95, 45), (x, 0, TILE, TILE))
                for _ in range(3):
                    pygame.draw.circle(surf, (25, 70 + random.randint(0, 20), 30),
                                       (x + random.randint(4, TILE - 4), random.randint(4, TILE - 4)),
                                       random.randint(4, 7))
            elif random.random() < 0.04:
                pygame.draw.circle(surf, (95, 150, 80), (x + TILE // 2, TILE // 2), 2)

        l = int(self.river_x - self.river_w / 2)
        r = int(self.river_x + self.river_w / 2)
        surf.fill((200, 185, 130), (l - 6, 0, r - l + 12, TILE))
        surf.fill((45, 95, 170), (l, 0, r - l, TILE))
        if random.random() < 0.5:
            wx = random.randint(l + 4, max(l + 5, r - 14))
            pygame.draw.line(surf, (110, 160, 220), (wx, TILE // 2), (wx + 10, TILE // 2), 2)

        self.road_gap -= 1
        if self.road_gap <= 0:
            surf.fill((95, 95, 100), (0, 2, WIDTH, TILE - 4))
            for dx in range(0, WIDTH, 30):
                surf.fill((220, 210, 120), (dx, TILE // 2 - 1, 14, 2))
            surf.fill((140, 100, 60), (l - 8, 0, r - l + 16, TILE))
            pygame.draw.rect(surf, (90, 60, 35), (l - 8, 0, r - l + 16, TILE), 2)
            self.road_gap = random.randint(70, 140)
        return surf, self.river_x

    def update(self, speed):
        for row in self.rows:
            row[1] += speed
        while self.rows and self.rows[-1][1] > HEIGHT:
            self.rows.pop()
        while self.rows[0][1] > -TILE:
            surf, rx = self._make_row()
            self.rows.insert(0, [surf, self.rows[0][1] - TILE, rx])

    def top_river(self):
        return self.rows[0][2], self.river_w

    def draw(self, screen):
        for surf, y, _ in self.rows:
            screen.blit(surf, (0, int(y)))


# ================================================================ 이펙트
class Particle:
    def __init__(self, x, y, color, speed=3.0, life=30, size=3):
        ang = random.uniform(0, math.tau)
        sp = random.uniform(0.3, speed)
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(ang) * sp, math.sin(ang) * sp
        self.life = self.max_life = random.randint(life // 2, life)
        self.color = color
        self.size = size

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.95
        self.vy *= 0.95
        self.life -= 1

    def draw(self, screen):
        k = self.life / self.max_life
        r = max(1, int(self.size * k + 0.5))
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), r)


class Ring:
    """폭탄/실드/노바용 퍼지는 원 이펙트"""

    def __init__(self, x, y, r_max, color, life=18, width=3, follow_ground=False):
        self.x, self.y = x, y
        self.r_max = r_max
        self.color = color
        self.life = self.max_life = life
        self.width = width
        self.follow_ground = follow_ground

    def update(self):
        self.life -= 1
        if self.follow_ground:
            self.y += SCROLL_SPEED

    def draw(self, screen):
        k = 1 - self.life / self.max_life
        r = max(2, int(self.r_max * k))
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), r, max(1, self.width))


class Popup:
    """아이템 획득 시 떠오르는 글자"""

    def __init__(self, x, y, text, color):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.life = 55

    def update(self):
        self.y -= 0.8
        self.life -= 1


class Crater:
    def __init__(self, x, y, r):
        self.x, self.y, self.r = x, y, r

    def draw(self, screen):
        pygame.draw.circle(screen, (60, 50, 35), (int(self.x), int(self.y)), self.r)
        pygame.draw.circle(screen, (35, 30, 20), (int(self.x), int(self.y)), int(self.r * 0.6))


# ================================================================ 아이템
# 종류: (색, 표시 글자, 이름, 등장 가중치)
ITEM_INFO = {
    "P": ((240, 70, 70), "P", "POWER UP", 20),
    "S": ((255, 160, 40), "S", "SPREAD", 8),
    "L": ((60, 200, 255), "L", "LASER", 8),
    "H": ((120, 230, 90), "H", "HOMING", 8),
    "B": ((150, 110, 70), "B", "BOMB UP", 10),
    "O": ((180, 120, 255), "O", "OPTION", 8),
    "G": ((80, 140, 255), "G", "SHIELD", 10),
    "N": ((255, 255, 255), "N", "NOVA", 4),
    "1": ((90, 230, 140), "1UP", "1UP", 2),
    "M": ((255, 210, 60), "$", "MEDAL", 22),
}


class Item:
    def __init__(self, kind, x, y):
        self.kind = kind
        self.x, self.y = x, y
        self.x0 = x
        self.t = random.randint(0, 100)
        self.vy = -2.0          # 처음엔 살짝 튀어오름
        self.alive = True

    def update(self):
        self.t += 1
        self.vy = min(1.4, self.vy + 0.08)
        self.y += self.vy
        self.x = clamp(self.x0 + math.sin(self.t * 0.05) * 14, 14, WIDTH - 14)
        if self.y > HEIGHT + 20:
            self.alive = False

    def draw(self, screen, font, tick):
        color, label, _, _ = ITEM_INFO[self.kind]
        x, y = int(self.x), int(self.y)
        w = 34 if label == "1UP" else 24
        rect = pygame.Rect(x - w // 2, y - 10, w, 20)
        glow = (tick // 6) % 2 == 0
        pygame.draw.rect(screen, color, rect, border_radius=9)
        pygame.draw.rect(screen, WHITE if glow else (40, 40, 50), rect, 2, border_radius=9)
        txt_color = BLACK if self.kind in ("N", "M", "1", "S", "H") else WHITE
        img = font.render(label, True, txt_color)
        screen.blit(img, img.get_rect(center=(x, y + 1)))


# ================================================================ 플레이어
def draw_ship(screen, x, y, s=1.0, tick=0):
    body = [(x, y - 16 * s), (x + 5 * s, y - 4 * s), (x + 17 * s, y + 8 * s), (x + 5 * s, y + 9 * s),
            (x, y + 14 * s), (x - 5 * s, y + 9 * s), (x - 17 * s, y + 8 * s), (x - 5 * s, y - 4 * s)]
    pygame.draw.polygon(screen, (205, 210, 225), body)
    pygame.draw.polygon(screen, (80, 85, 115), body, 2)
    pygame.draw.line(screen, (120, 125, 160), (x - 14 * s, y + 6 * s), (x + 14 * s, y + 6 * s), 1)
    pygame.draw.ellipse(screen, (60, 170, 230), (x - 3 * s, y - 8 * s, 6 * s, 10 * s))
    if s >= 1.0:
        glow = ORANGE if (tick // 3) % 2 else YELLOW
        pygame.draw.circle(screen, glow, (int(x - 4 * s), int(y + 13 * s)), 3)
        pygame.draw.circle(screen, glow, (int(x + 4 * s), int(y + 13 * s)), 3)


class Player:
    SPEED = 4.2

    def __init__(self, weapon="spread", level=1, bomb_lv=1):
        self.x = WIDTH / 2
        self.y = HEIGHT - 110
        self.radius = 6
        self.shot_cd = 0
        self.missile_cd = 0
        self.invuln = 150
        self.tick = 0
        self.weapon = weapon
        self.level = level
        self.bomb_lv = bomb_lv
        self.options = 0
        self.shield = 0
        self.trail = deque([(self.x, self.y)] * 40, maxlen=40)

    @property
    def sight(self):
        return self.x, self.y - SIGHT_DIST

    def option_pos(self, i):
        return self.trail[-1 - (i + 1) * 14]

    def update(self, keys):
        self.tick += 1
        dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
        if dx and dy:
            dx *= 0.7071
            dy *= 0.7071
        self.x = clamp(self.x + dx * self.SPEED, 18, WIDTH - 18)
        self.y = clamp(self.y + dy * self.SPEED, SIGHT_DIST + 20, HEIGHT - 24)
        if dx or dy or self.tick % 4 == 0:
            self.trail.append((self.x, self.y))
        if self.shot_cd > 0:
            self.shot_cd -= 1
        if self.missile_cd > 0:
            self.missile_cd -= 1
        if self.invuln > 0:
            self.invuln -= 1

    def fire(self, game):
        x, y, lv = self.x, self.y - 12, self.level
        shots = game.shots
        if self.weapon == "spread":
            shots.append(Shot(x - 6, y, 0, -12))
            shots.append(Shot(x + 6, y, 0, -12))
            angles = {1: [], 2: [-0.13, 0.13], 3: [-0.26, -0.13, 0.13, 0.26],
                      4: [-0.36, -0.22, -0.1, 0.1, 0.22, 0.36]}[lv]
            for a in angles:
                shots.append(Shot(x, y, math.sin(a) * 12, -math.cos(a) * 12))
            self.shot_cd = 7 if lv < 4 else 5
            game.sfx.play("shot")
        elif self.weapon == "laser":
            dmg = 1 if lv < 3 else 2
            offsets = {1: [0], 2: [-7, 7], 3: [-7, 7], 4: [-12, 0, 12]}[lv]
            for ox in offsets:
                shots.append(Shot(x + ox, y, 0, -18, dmg, "laser", pierce=True))
            self.shot_cd = 5
            game.sfx.play("laser")
        else:  # homing
            shots.append(Shot(x - 5, y, 0, -12))
            shots.append(Shot(x + 5, y, 0, -12))
            self.shot_cd = 7
            if self.missile_cd == 0:
                for i in range(lv):
                    side = -1 if i % 2 == 0 else 1
                    a = side * (0.5 + 0.35 * (i // 2))
                    shots.append(Shot(x + side * 10, y + 8, math.sin(a) * 7, -math.cos(a) * 7, 1, "missile"))
                self.missile_cd = 22
                game.sfx.play("missile")
            else:
                game.sfx.play("shot")
        for i in range(self.options):
            ox, oy = self.option_pos(i)
            shots.append(Shot(ox, oy - 8, 0, -12))

    def draw(self, screen):
        for i in range(self.options):
            ox, oy = self.option_pos(i)
            c = (180, 120, 255) if (self.tick // 5) % 2 else (230, 200, 255)
            pygame.draw.circle(screen, (60, 30, 100), (int(ox), int(oy)), 8)
            pygame.draw.circle(screen, c, (int(ox), int(oy)), 6)
        if self.invuln > 0 and (self.invuln // 4) % 2 == 0:
            return
        draw_ship(screen, self.x, self.y, 1.0, self.tick)
        if self.shield > 0:
            r = 22 + (self.tick // 4) % 3
            pygame.draw.circle(screen, (90, 160, 255), (int(self.x), int(self.y)), r, 2)
            if self.shield > 1:
                pygame.draw.circle(screen, (170, 210, 255), (int(self.x), int(self.y)), r + 4, 1)


class Shot:
    def __init__(self, x, y, vx, vy, dmg=1, kind="bullet", pierce=False):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.dmg = dmg
        self.kind = kind
        self.pierce = pierce
        self.hit = set()
        self.alive = True
        self.life = 120

    def update(self, game):
        if self.kind == "missile":
            target, best = None, 1e9
            for e in game.air:
                if e.alive and e.y > -10:
                    d = math.hypot(e.x - self.x, e.y - self.y)
                    if d < best:
                        target, best = e, d
            ang = math.atan2(self.vy, self.vx)
            if target:
                want = math.atan2(target.y - self.y, target.x - self.x)
                diff = (want - ang + math.pi) % math.tau - math.pi
                ang += clamp(diff, -0.14, 0.14)
            speed = min(9.0, math.hypot(self.vx, self.vy) + 0.3)
            self.vx, self.vy = math.cos(ang) * speed, math.sin(ang) * speed
            if game.tick % 2 == 0:
                game.particles.append(Particle(self.x, self.y, (200, 200, 200), 0.6, 14, 2))
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        if self.y < -30 or self.y > HEIGHT + 30 or self.x < -30 or self.x > WIDTH + 30 or self.life <= 0:
            self.alive = False

    def draw(self, screen):
        x, y = int(self.x), int(self.y)
        if self.kind == "laser":
            w = 4 if self.dmg == 1 else 6
            pygame.draw.rect(screen, CYAN, (x - w // 2 - 1, y - 14, w + 2, 26))
            pygame.draw.rect(screen, WHITE, (x - w // 2 + 1, y - 12, max(1, w - 2), 22))
        elif self.kind == "missile":
            ang = math.atan2(self.vy, self.vx)
            ex, ey = x - math.cos(ang) * 9, y - math.sin(ang) * 9
            pygame.draw.line(screen, (220, 230, 220), (x, y), (ex, ey), 4)
            pygame.draw.circle(screen, (120, 230, 90), (x, y), 3)
            pygame.draw.circle(screen, ORANGE, (int(ex), int(ey)), 2)
        else:
            pygame.draw.rect(screen, YELLOW, (x - 2, y - 8, 4, 14))
            pygame.draw.rect(screen, WHITE, (x - 1, y - 6, 2, 8))


class Bomb:
    def __init__(self, x, y, tx, ty):
        self.sx, self.sy = x, y
        self.tx, self.ty = tx, ty
        self.t = 0
        self.alive = True

    @property
    def pos(self):
        k = self.t / BOMB_TIME
        return self.sx + (self.tx - self.sx) * k, self.sy + (self.ty - self.sy) * k

    def update(self, scroll):
        self.t += 1
        self.ty += scroll
        if self.t >= BOMB_TIME:
            self.alive = False

    def draw(self, screen):
        x, y = self.pos
        r = max(2, int(6 - 3 * self.t / BOMB_TIME))
        pygame.draw.circle(screen, (40, 40, 50), (int(x), int(y)), r)
        pygame.draw.circle(screen, (200, 200, 210), (int(x), int(y)), r, 1)


class EnemyBullet:
    def __init__(self, x, y, vx, vy):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.radius = 4
        self.alive = True

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if not (-20 < self.x < WIDTH + 20 and -20 < self.y < HEIGHT + 20):
            self.alive = False

    def draw(self, screen, tick):
        c = ORANGE if (tick // 4) % 2 else RED
        pygame.draw.circle(screen, c, (int(self.x), int(self.y)), 5)
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), 2)


# ================================================================ 공중 적
class AirEnemy:
    STATS = {               # 반지름, 체력, 점수
        "spinner": (12, 1, 100),
        "diver": (12, 1, 150),
        "gunship": (20, 6, 500),
        "carrier": (18, 4, 800),
    }

    def __init__(self, kind, x, y, group=None):
        self.kind = kind
        self.x, self.y = x, y
        self.x0 = x
        self.radius, self.hp, self.points = self.STATS[kind]
        self.vx, self.vy = 0.0, 0.0
        self.t = 0
        self.alive = True
        self.flash = 0
        self.turned = False
        self.phase = 0
        self.group = group
        self.stop_y = random.uniform(110, 230)
        if kind == "spinner":
            self.vy = 3.2
        elif kind == "diver":
            self.vy = 4.3
        elif kind == "carrier":
            self.vy = 1.1

    def update(self, game):
        self.t += 1
        p = game.player if game.player_alive else None
        if self.flash:
            self.flash -= 1

        if self.kind == "spinner":
            target_y = (p.y - 170) if p else HEIGHT * 0.5
            if not self.turned:
                if p:
                    self.x += clamp(p.x - self.x, -2.0, 2.0)
                if self.y >= target_y:
                    self.turned = True
                    side = 1 if (p and self.x > p.x) or (not p and self.x > WIDTH / 2) else -1
                    self.vx = 3.5 * side
                    if random.random() < 0.35 + game.difficulty * 0.1:
                        game.fire_aimed(self.x, self.y, 4.0)
            else:
                self.vy = max(-3.0, self.vy - 0.25)
                self.x += self.vx
            self.y += self.vy
        elif self.kind == "diver":
            self.y += self.vy
            self.x = self.x0 + math.sin(self.t * 0.07) * 70
            if self.t == 40 and random.random() < 0.5:
                game.fire_aimed(self.x, self.y, 4.5)
        elif self.kind == "carrier":
            self.y += self.vy
            self.x = self.x0 + math.sin(self.t * 0.02) * 90
        elif self.kind == "gunship":
            if self.phase == 0:
                self.y += 2.0
                if self.y >= self.stop_y:
                    self.phase, self.t = 1, 0
            elif self.phase == 1:
                self.x += math.sin(self.t * 0.03) * 0.8
                if self.t % 50 == 25:
                    for s in (-0.25, 0, 0.25):
                        game.fire_aimed(self.x, self.y + 10, 3.6, s)
                if self.t > 220:
                    self.phase = 2
            else:
                self.y -= 1.8

        if (self.x < -50 or self.x > WIDTH + 50 or self.y > HEIGHT + 50
                or (self.y < -60 and self.t > 40)):
            self.alive = False

    def draw(self, screen, tick):
        x, y = int(self.x), int(self.y)
        hit = self.flash > 0
        if self.kind == "spinner":
            ang = tick * 0.25
            pygame.draw.circle(screen, WHITE if hit else (150, 155, 175), (x, y), 12)
            pygame.draw.circle(screen, (70, 75, 95), (x, y), 12, 2)
            for k in range(3):
                a = ang + k * math.tau / 3
                pygame.draw.line(screen, (230, 80, 110), (x, y),
                                 (x + math.cos(a) * 10, y + math.sin(a) * 10), 3)
            pygame.draw.circle(screen, (40, 40, 60), (x, y), 4)
        elif self.kind == "diver":
            pts = [(x, y + 14), (x + 13, y - 8), (x, y - 3), (x - 13, y - 8)]
            pygame.draw.polygon(screen, WHITE if hit else (230, 120, 50), pts)
            pygame.draw.polygon(screen, (110, 50, 20), pts, 2)
            pygame.draw.circle(screen, (255, 235, 140), (x, y + 2), 3)
        elif self.kind == "carrier":
            body = [(x - 22, y), (x - 10, y - 12), (x + 10, y - 12), (x + 22, y), (x + 10, y + 12), (x - 10, y + 12)]
            pygame.draw.polygon(screen, WHITE if hit else GOLD, body)
            pygame.draw.polygon(screen, (130, 90, 20), body, 2)
            c = WHITE if (tick // 6) % 2 else (255, 120, 120)
            pygame.draw.rect(screen, c, (x - 7, y - 5, 14, 10), border_radius=3)
            for sx in (-1, 1):
                a = tick * 0.6 * sx
                pygame.draw.line(screen, (90, 70, 30), (x + sx * 16 - math.cos(a) * 7, y - 10),
                                 (x + sx * 16 + math.cos(a) * 7, y - 10), 2)
        else:
            pts = [(x + math.cos(a) * 22, y + math.sin(a) * 16)
                   for a in [k * math.tau / 6 for k in range(6)]]
            pygame.draw.polygon(screen, WHITE if hit else (110, 120, 150), pts)
            pygame.draw.polygon(screen, (50, 55, 80), pts, 2)
            pygame.draw.rect(screen, (60, 65, 90), (x - 26, y - 4, 52, 8))
            pygame.draw.circle(screen, (90, 230, 160) if (tick // 10) % 2 else (40, 160, 110), (x, y), 6)


# ================================================================ 지상 적
class GroundEnemy:
    STATS = {               # 반지름, 체력, 점수
        "turret": (14, 1, 300),
        "tank": (14, 1, 250),
        "dome": (16, 1, 200),
        "fortress": (30, 3, 3000),
    }

    def __init__(self, kind, x, y):
        self.kind = kind
        self.x, self.y = x, y
        self.radius, self.hp, self.points = self.STATS[kind]
        self.alive = True
        self.flash = 0
        self.t = 0
        self.vx = random.choice([-0.8, 0.8]) if kind == "tank" else 0
        self.fire_cd = random.randint(60, 140)
        self.barrel = math.pi / 2

    def update(self, game, scroll):
        self.t += 1
        self.y += scroll
        if self.flash:
            self.flash -= 1
        if self.kind == "tank":
            self.x += self.vx
            if self.x < 20 or self.x > WIDTH - 20:
                self.vx = -self.vx
        p = game.player
        if game.player_alive:
            self.barrel = math.atan2(p.y - self.y, p.x - self.x)

        can_fire = game.player_alive and 20 < self.y < p.y - 120
        if self.kind in ("turret", "tank", "fortress") and can_fire:
            self.fire_cd -= 1
            if self.fire_cd <= 0:
                if self.kind == "fortress":
                    for s in (-0.4, -0.2, 0, 0.2, 0.4):
                        game.fire_aimed(self.x, self.y, 3.4, s)
                    self.fire_cd = 75
                else:
                    game.fire_aimed(self.x, self.y, 3.6 + game.difficulty * 0.3)
                    self.fire_cd = random.randint(int(110 / game.difficulty), int(170 / game.difficulty))
        if self.y > HEIGHT + 80:
            self.alive = False

    def draw(self, screen, tick):
        x, y = int(self.x), int(self.y)
        hit = self.flash > 0
        if self.kind == "turret":
            pygame.draw.circle(screen, (90, 90, 95), (x, y), 15)
            pygame.draw.circle(screen, WHITE if hit else (150, 150, 160), (x, y), 11)
            pygame.draw.circle(screen, (60, 60, 70), (x, y), 15, 2)
            ex, ey = x + math.cos(self.barrel) * 16, y + math.sin(self.barrel) * 16
            pygame.draw.line(screen, (40, 40, 45), (x, y), (ex, ey), 5)
            pygame.draw.circle(screen, RED, (x, y), 4)
        elif self.kind == "tank":
            pygame.draw.rect(screen, (40, 40, 35), (x - 15, y - 13, 30, 6))
            pygame.draw.rect(screen, (40, 40, 35), (x - 15, y + 7, 30, 6))
            pygame.draw.rect(screen, WHITE if hit else (120, 125, 70), (x - 13, y - 9, 26, 18))
            pygame.draw.circle(screen, (90, 95, 50), (x, y), 7)
            ex, ey = x + math.cos(self.barrel) * 15, y + math.sin(self.barrel) * 15
            pygame.draw.line(screen, (50, 50, 30), (x, y), (ex, ey), 4)
        elif self.kind == "dome":
            pygame.draw.circle(screen, (70, 70, 80), (x, y), 17)
            pygame.draw.circle(screen, WHITE if hit else (180, 185, 200), (x, y), 13)
            pygame.draw.circle(screen, (230, 235, 245), (x - 4, y - 4), 5)
            c = (255, 220, 80) if (tick // 15) % 2 else (200, 140, 30)
            pygame.draw.circle(screen, c, (x, y), 4)
        else:  # fortress
            pts = [(x + math.cos(a) * 62, y + math.sin(a) * 62)
                   for a in [math.pi / 8 + k * math.tau / 8 for k in range(8)]]
            pygame.draw.polygon(screen, (85, 85, 95), pts)
            pygame.draw.polygon(screen, (50, 50, 60), pts, 3)
            pygame.draw.circle(screen, (60, 60, 70), (x, y), 40, 3)
            for k in range(8):
                a = k * math.tau / 8
                pygame.draw.line(screen, (65, 65, 75), (x + math.cos(a) * 30, y + math.sin(a) * 30),
                                 (x + math.cos(a) * 55, y + math.sin(a) * 55), 2)
            pulse = int(30 * (1 + math.sin(tick * 0.15)))
            pygame.draw.circle(screen, (40, 40, 50), (x, y), 26)
            pygame.draw.circle(screen, WHITE if hit else (200 + pulse // 2, 40, 40 + pulse), (x, y), 20)
            pygame.draw.circle(screen, (255, 200, 200), (x - 6, y - 6), 5)


# ================================================================ 게임 본체
class Game:
    def __init__(self):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("SKY STRIKER")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas,arial", 20, bold=True)
        self.small = pygame.font.SysFont("consolas,arial", 15)
        self.item_font = pygame.font.SysFont("consolas,arial", 14, bold=True)
        self.big = pygame.font.SysFont("consolas,arial", 48, bold=True)
        self.sfx = SoundBank()
        self.hiscore = self.load_hiscore()
        self.terrain = Terrain()
        self.state = "title"
        self.paused = False
        self.tick = 0
        self.reset()

    # ---------- 점수 저장
    def load_hiscore(self):
        try:
            with open(HISCORE_FILE) as f:
                return int(f.read().strip() or 0)
        except (OSError, ValueError):
            return 0

    def save_hiscore(self):
        try:
            with open(HISCORE_FILE, "w") as f:
                f.write(str(self.hiscore))
        except OSError:
            pass

    # ---------- 초기화
    def reset(self):
        self.player = Player()
        self.player_alive = True
        self.shots, self.bombs, self.enemy_bullets = [], [], []
        self.air, self.ground, self.particles, self.craters = [], [], [], []
        self.items, self.rings, self.popups = [], [], []
        self.groups = {}
        self.next_group = 0
        self.score = 0
        self.lives = 3
        self.frame = 0
        self.air_timer = 90
        self.ground_timer = 60
        self.carrier_timer = 600
        self.fortress_timer = 1800
        self.respawn_timer = 0
        self.over_timer = 0
        self.extend_at = 20000
        self.medal_value = 500
        self.flash_timer = 0
        self.last_eshot = -10

    @property
    def difficulty(self):
        return min(2.5, 1.0 + self.frame / 5400)

    # ---------- 생성
    def fire_aimed(self, x, y, speed, spread=0.0):
        if not self.player_alive:
            return
        vx, vy = aim(x, y, self.player.x, self.player.y, speed, spread)
        self.enemy_bullets.append(EnemyBullet(x, y, vx, vy))
        if self.tick - self.last_eshot > 4:
            self.sfx.play("enemy_shot")
            self.last_eshot = self.tick

    def spawn_air(self):
        r = random.random()
        if r < 0.45:
            x0 = random.uniform(50, WIDTH - 50)
            n = random.randint(3, 5)
            gid = self.next_group
            self.next_group += 1
            self.groups[gid] = [n, 0]
            for i in range(n):
                self.air.append(AirEnemy("spinner", x0, -20 - i * 38, gid))
        elif r < 0.82:
            self.air.append(AirEnemy("diver", random.uniform(80, WIDTH - 80), -20))
        elif sum(1 for e in self.air if e.kind == "gunship") < 2:
            self.air.append(AirEnemy("gunship", random.uniform(60, WIDTH - 60), -30))

    def spawn_ground(self):
        rx, rw = self.terrain.top_river()
        for _ in range(10):
            x = random.uniform(30, WIDTH - 30)
            if abs(x - rx) > rw / 2 + 24:
                break
        else:
            return
        kind = random.choices(["turret", "tank", "dome"], [0.45, 0.3, 0.25])[0]
        self.ground.append(GroundEnemy(kind, x, -30))

    def spawn_fortress(self):
        x = random.uniform(110, WIDTH - 110)
        y = -80
        self.ground.append(GroundEnemy("fortress", x, y))
        for dx, dy in ((-44, -44), (44, -44), (-44, 44), (44, 44)):
            self.ground.append(GroundEnemy("turret", x + dx, y + dy))
        self.sfx.play("alert")

    def explode(self, x, y, big=False, ground=False):
        n = 40 if big else 18
        for _ in range(n):
            c = random.choice([ORANGE, YELLOW, RED, WHITE])
            self.particles.append(Particle(x, y, c, 5 if big else 3, 45 if big else 28, 5 if big else 3))
        if ground:
            self.craters.append(Crater(x, y, 22 if big else 12))
        self.sfx.play("explode_big" if big else "explode")

    def add_score(self, pts):
        self.score += pts
        if self.score >= self.extend_at:
            self.lives += 1
            self.extend_at += 40000
            self.sfx.play("oneup")
            self.popups.append(Popup(WIDTH / 2, HEIGHT / 2, "EXTEND!", (90, 230, 140)))

    # ---------- 아이템
    def random_item_kind(self):
        kinds = list(ITEM_INFO)
        weights = [ITEM_INFO[k][3] for k in kinds]
        k = random.choices(kinds, weights)[0]
        p = self.player
        if k == "O" and p.options >= 2:
            k = "M"
        if k == "P" and p.level >= 4:
            k = random.choice(["M", "G", "B"])
        return k

    def drop_item(self, x, y, kind=None):
        self.items.append(Item(kind or self.random_item_kind(), x, y))

    def collect(self, item):
        p = self.player
        k = item.kind
        color, _, name, _ = ITEM_INFO[k]
        snd = "item"
        text = name
        if k == "P":
            p.level = min(4, p.level + 1)
            text = f"POWER Lv{p.level}"
            snd = "powerup"
        elif k in ("S", "L", "H"):
            w = {"S": "spread", "L": "laser", "H": "homing"}[k]
            if p.weapon == w:
                p.level = min(4, p.level + 1)
            p.weapon = w
            text = f"{WEAPON_NAMES[w]} Lv{p.level}"
            snd = "powerup"
        elif k == "B":
            p.bomb_lv = min(3, p.bomb_lv + 1)
            text = f"BOMB Lv{p.bomb_lv}"
        elif k == "O":
            p.options = min(2, p.options + 1)
            text = f"OPTION x{p.options}"
            snd = "powerup"
        elif k == "G":
            p.shield = min(2, p.shield + 1)
            snd = "shield"
        elif k == "N":
            self.nova()
            snd = "nova"
        elif k == "1":
            self.lives += 1
            snd = "oneup"
        elif k == "M":
            self.add_score(self.medal_value)
            text = f"+{self.medal_value}"
            self.medal_value = min(5000, self.medal_value + 500)
            snd = "medal"
        self.add_score(100)
        self.sfx.play(snd)
        self.popups.append(Popup(item.x, item.y - 14, text, color))

    def nova(self):
        self.flash_timer = 20
        self.rings.append(Ring(self.player.x, self.player.y, 700, WHITE, 30, 8))
        self.enemy_bullets.clear()
        for e in self.air:
            if e.alive and -20 < e.y < HEIGHT:
                self.damage_air(e, 5)

    # ---------- 입력
    def drop_bomb(self):
        if self.state != "play" or self.paused or not self.player_alive:
            return
        max_bombs = 2 if self.player.bomb_lv >= 3 else 1
        if sum(1 for b in self.bombs if b.alive) >= max_bombs:
            return
        sx, sy = self.player.sight
        self.bombs.append(Bomb(self.player.x, self.player.y, sx, sy))
        self.sfx.play("bomb_drop")

    def bomb_radius(self):
        return 14 + 8 * (self.player.bomb_lv - 1)

    def sight_locked(self):
        sx, sy = self.player.sight
        return any(math.hypot(g.x - sx, g.y - sy) < g.radius + self.bomb_radius() - 6 for g in self.ground)

    # ---------- 업데이트
    def update(self, keys):
        self.tick += 1
        if self.paused:
            return

        self.terrain.update(SCROLL_SPEED)
        for c in self.craters:
            c.y += SCROLL_SPEED
        self.craters = [c for c in self.craters if c.y < HEIGHT + 40]
        self.update_effects()

        if self.state != "play":
            if self.state == "over":
                self.over_timer += 1
                self.update_enemies()
            return

        self.frame += 1
        if self.flash_timer:
            self.flash_timer -= 1

        if self.player_alive:
            self.player.update(keys)
            if keys[pygame.K_z] or keys[pygame.K_SPACE]:
                if self.player.shot_cd == 0:
                    self.player.fire(self)
                # 자동 폭탄: 사격 중 조준점에 지상 적이 잡히면 폭탄도 자동으로 투하
                if self.sight_locked():
                    self.drop_bomb()
        else:
            self.respawn_timer -= 1
            if self.respawn_timer <= 0:
                if self.lives > 0:
                    self.lives -= 1
                    old = self.player
                    self.player = Player(old.weapon, max(1, old.level - 1), max(1, old.bomb_lv - 1))
                    self.player_alive = True
                else:
                    self.game_over()
                    return

        # 적 생성
        self.air_timer -= 1
        if self.air_timer <= 0:
            self.spawn_air()
            self.air_timer = int(random.randint(50, 100) / self.difficulty)
        self.ground_timer -= 1
        if self.ground_timer <= 0:
            self.spawn_ground()
            self.ground_timer = int(random.randint(80, 150) / self.difficulty)
        self.carrier_timer -= 1
        if self.carrier_timer <= 0:
            self.air.append(AirEnemy("carrier", random.uniform(110, WIDTH - 110), -30))
            self.carrier_timer = random.randint(900, 1300)
        self.fortress_timer -= 1
        if self.fortress_timer <= 0:
            self.spawn_fortress()
            self.fortress_timer = 2700

        for s in self.shots:
            s.update(self)
        for b in self.bombs:
            b.update(SCROLL_SPEED)
            if not b.alive:
                self.bomb_land(b.tx, b.ty)
        for it in self.items:
            it.update()
        self.update_enemies()
        self.collide()

        self.shots = [s for s in self.shots if s.alive]
        self.bombs = [b for b in self.bombs if b.alive]
        self.items = [i for i in self.items if i.alive]

    def update_effects(self):
        for p in self.particles:
            p.update()
        for r in self.rings:
            r.update()
        for p in self.popups:
            p.update()
        self.particles = [p for p in self.particles if p.life > 0]
        self.rings = [r for r in self.rings if r.life > 0]
        self.popups = [p for p in self.popups if p.life > 0]

    def update_enemies(self):
        for e in self.air:
            e.update(self)
        for g in self.ground:
            g.update(self, SCROLL_SPEED)
        for b in self.enemy_bullets:
            b.update()
        self.air = [e for e in self.air if e.alive]
        self.ground = [g for g in self.ground if g.alive]
        self.enemy_bullets = [b for b in self.enemy_bullets if b.alive]

    def bomb_land(self, x, y):
        radius = self.bomb_radius()
        for _ in range(12 + radius // 2):
            self.particles.append(Particle(x, y, random.choice([ORANGE, YELLOW]), 2.5 + radius / 12, 22, 4))
        self.rings.append(Ring(x, y, radius + 10, (255, 220, 150), 16, 3, follow_ground=True))
        self.sfx.play("bomb_hit")
        for g in self.ground:
            if g.alive and math.hypot(g.x - x, g.y - y) < g.radius + radius:
                g.hp -= 1
                g.flash = 6
                if g.hp <= 0:
                    g.alive = False
                    big = g.kind == "fortress"
                    self.explode(g.x, g.y, big=big, ground=True)
                    self.add_score(g.points)
                    if big:
                        for i in range(3):
                            self.drop_item(g.x + (i - 1) * 30, g.y)
                    elif g.kind == "dome" and random.random() < 0.35:
                        self.drop_item(g.x, g.y)
                    elif random.random() < 0.05:
                        self.drop_item(g.x, g.y)

    def damage_air(self, e, dmg):
        e.hp -= dmg
        e.flash = 4
        if e.hp > 0:
            self.sfx.play("hit")
            return
        e.alive = False
        self.explode(e.x, e.y, big=e.kind in ("gunship", "carrier"))
        self.add_score(e.points)
        if e.kind == "carrier":
            self.drop_item(e.x, e.y)
            if random.random() < 0.3:
                self.drop_item(e.x + 20, e.y)
        elif e.kind == "gunship":
            if random.random() < 0.6:
                self.drop_item(e.x, e.y)
        elif e.group is not None:
            g = self.groups.get(e.group)
            if g:
                g[1] += 1
                if g[1] >= g[0]:          # 편대를 전멸시키면 보너스 아이템
                    self.drop_item(e.x, e.y)
                    self.popups.append(Popup(e.x, e.y - 20, "SQUAD BONUS", YELLOW))
                    self.add_score(500)
                    del self.groups[e.group]
        elif random.random() < 0.06:
            self.drop_item(e.x, e.y)

    def collide(self):
        # 공중 사격 vs 공중 적
        for s in self.shots:
            if not s.alive:
                continue
            for e in self.air:
                if not e.alive or (s.pierce and id(e) in s.hit):
                    continue
                if abs(s.x - e.x) < e.radius + 4 and abs(s.y - e.y) < e.radius + 10:
                    if s.pierce:
                        s.hit.add(id(e))
                    else:
                        s.alive = False
                    self.damage_air(e, s.dmg)
                    if not s.pierce:
                        break

        if not self.player_alive:
            return
        p = self.player

        # 아이템 획득
        for it in self.items:
            if it.alive and math.hypot(it.x - p.x, it.y - p.y) < 24:
                it.alive = False
                self.collect(it)

        if p.invuln > 0:
            return
        for b in self.enemy_bullets:
            if math.hypot(b.x - p.x, b.y - p.y) < b.radius + p.radius:
                b.alive = False
                self.player_hit()
                return
        for e in self.air:
            if e.alive and math.hypot(e.x - p.x, e.y - p.y) < e.radius + p.radius:
                if e.kind in ("gunship", "carrier"):
                    self.damage_air(e, 2)
                else:
                    e.alive = False
                    self.explode(e.x, e.y)
                self.player_hit()
                return

    def player_hit(self):
        p = self.player
        if p.shield > 0:
            p.shield -= 1
            p.invuln = 60
            self.rings.append(Ring(p.x, p.y, 60, (120, 180, 255), 20, 4))
            self.enemy_bullets = [b for b in self.enemy_bullets if math.hypot(b.x - p.x, b.y - p.y) > 80]
            self.sfx.play("shield")
            return
        self.explode(p.x, p.y, big=True)
        self.sfx.play("player_die")
        self.player_alive = False
        self.respawn_timer = 100
        self.medal_value = 500
        self.enemy_bullets.clear()
        self.bombs.clear()

    def game_over(self):
        self.state = "over"
        self.over_timer = 0
        self.sfx.stop_bgm()
        self.sfx.play("gameover")
        if self.score > self.hiscore:
            self.hiscore = self.score
            self.save_hiscore()

    # ---------- 그리기
    def text(self, s, font, color, center):
        img = font.render(s, True, color)
        shadow = font.render(s, True, BLACK)
        r = img.get_rect(center=center)
        self.screen.blit(shadow, r.move(2, 2))
        self.screen.blit(img, r)

    def draw(self):
        scr = self.screen
        self.terrain.draw(scr)
        for c in self.craters:
            c.draw(scr)
        for g in self.ground:
            g.draw(scr, self.tick)
        for b in self.bombs:
            b.draw(scr)

        if self.state == "play" and self.player_alive:
            self.draw_sight()

        for it in self.items:
            it.draw(scr, self.item_font, self.tick)
        for s in self.shots:
            s.draw(scr)
        for e in self.air:
            e.draw(scr, self.tick)
        if self.state == "play" and self.player_alive:
            self.player.draw(scr)
        for b in self.enemy_bullets:
            b.draw(scr, self.tick)
        for p in self.particles:
            p.draw(scr)
        for r in self.rings:
            r.draw(scr)
        for p in self.popups:
            if p.life > 10 or p.life % 2:
                self.text(p.text, self.small, p.color, (int(p.x), int(p.y)))

        if self.flash_timer:
            fl = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            fl.fill((255, 255, 255, int(160 * self.flash_timer / 20)))
            scr.blit(fl, (0, 0))

        if self.state == "title":
            self.draw_title()
        else:
            self.draw_hud()
            if self.state == "over":
                self.text("GAME OVER", self.big, RED, (WIDTH // 2, HEIGHT // 2 - 30))
                self.text(f"SCORE {self.score}", self.font, WHITE, (WIDTH // 2, HEIGHT // 2 + 20))
                if self.over_timer > 60 and (self.tick // 30) % 2 == 0:
                    self.text("PRESS ENTER", self.font, YELLOW, (WIDTH // 2, HEIGHT // 2 + 60))
            elif self.paused:
                self.text("PAUSED", self.big, WHITE, (WIDTH // 2, HEIGHT // 2))

    def draw_sight(self):
        sx, sy = self.player.sight
        locked = self.sight_locked()
        color = RED if locked and (self.tick // 4) % 2 else (240, 240, 240)
        r = 8 + self.player.bomb_lv * 3
        x, y = int(sx), int(sy)
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            cx, cy = x + dx * r, y + dy * r
            pygame.draw.line(self.screen, color, (cx, cy), (cx - dx * 6, cy), 2)
            pygame.draw.line(self.screen, color, (cx, cy), (cx, cy - dy * 6), 2)
        pygame.draw.circle(self.screen, color, (x, y), 2)
        if locked:
            img = self.small.render("BOMB", True, color)
            self.screen.blit(img, (x + r + 6, y - 8))

    def draw_hud(self):
        scr = self.screen
        scr.blit(self.font.render(f"SCORE {self.score:>7}", True, WHITE), (10, 8))
        hi = self.font.render(f"HI {max(self.hiscore, self.score):>7}", True, YELLOW)
        scr.blit(hi, (WIDTH - hi.get_width() - 10, 8))
        for i in range(min(self.lives, 8)):
            draw_ship(scr, 20 + i * 24, HEIGHT - 18, 0.6)

        p = self.player
        lines = [
            (f"{WEAPON_NAMES[p.weapon]} Lv{p.level}", ITEM_INFO[{"spread": "S", "laser": "L", "homing": "H"}[p.weapon]][0]),
            (f"BOMB Lv{p.bomb_lv}  OPT {p.options}", (220, 220, 230)),
        ]
        if p.shield:
            lines.append((f"SHIELD x{p.shield}", (120, 180, 255)))
        for i, (s, c) in enumerate(reversed(lines)):
            img = self.small.render(s, True, c)
            scr.blit(img, (WIDTH - img.get_width() - 10, HEIGHT - 24 - i * 18))
        if self.sfx.ok and self.sfx.muted:
            scr.blit(self.small.render("SOUND OFF (M)", True, (200, 200, 200)), (10, 32))

    def draw_title(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 20, 160))
        self.screen.blit(overlay, (0, 0))
        self.text("SKY STRIKER", self.big, (120, 210, 255), (WIDTH // 2, 110))
        self.text("VERTICAL SCROLL SHOOTER", self.small, WHITE, (WIDTH // 2, 150))
        draw_ship(self.screen, WIDTH // 2, 200, 1.8)

        keys = [("ARROWS / WASD", "MOVE"), ("Z / SPACE", "SHOT + AUTO BOMB"), ("X / SHIFT", "GROUND BOMB"),
                ("M", "SOUND ON/OFF"), ("P / ESC", "PAUSE")]
        for i, (k, v) in enumerate(keys):
            y = 250 + i * 22
            self.screen.blit(self.small.render(k, True, YELLOW), (110, y))
            self.screen.blit(self.small.render(v, True, WHITE), (290, y))

        self.text("- ITEMS -", self.small, (200, 200, 220), (WIDTH // 2, 380))
        desc = {"P": "POWER UP", "S": "SPREAD SHOT", "L": "PIERCING LASER", "H": "HOMING MISSILE",
                "B": "BIGGER BOMB", "O": "OPTION DRONE", "G": "SHIELD", "N": "NOVA BLAST",
                "1": "EXTRA LIFE", "M": "SCORE MEDAL"}
        for i, k in enumerate(ITEM_INFO):
            col, row = i % 2, i // 2
            x = 70 + col * 200
            y = 405 + row * 28
            it = Item(k, x, y)
            it.x, it.y = x, y
            it.draw(self.screen, self.item_font, self.tick)
            self.screen.blit(self.small.render(desc[k], True, WHITE), (x + 24, y - 8))

        self.text(f"HI SCORE {self.hiscore}", self.font, YELLOW, (WIDTH // 2, 580))
        if (self.tick // 30) % 2 == 0:
            self.text("PRESS ENTER TO START", self.font, WHITE, (WIDTH // 2, 630))

    # ---------- 메인 루프
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            return False
        if event.type != pygame.KEYDOWN:
            return True
        k = event.key
        if k == pygame.K_m:
            self.sfx.toggle(self.state == "play")
            return True
        if self.state == "title":
            if k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.reset()
                self.state = "play"
                self.sfx.play("start")
                self.sfx.start_bgm()
            elif k == pygame.K_ESCAPE:
                return False
        elif self.state == "play":
            if k in (pygame.K_p, pygame.K_ESCAPE):
                self.paused = not self.paused
                if self.sfx.ok and not self.sfx.muted:
                    if self.paused:
                        pygame.mixer.pause()
                    else:
                        pygame.mixer.unpause()
            elif k in (pygame.K_x, pygame.K_LSHIFT, pygame.K_RSHIFT):
                self.drop_bomb()
        elif self.state == "over":
            if k in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.over_timer > 60:
                self.state = "title"
                self.air.clear()
                self.ground.clear()
                self.enemy_bullets.clear()
                self.items.clear()
        return True

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if not self.handle_event(event):
                    running = False
            self.update(pygame.key.get_pressed())
            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()
