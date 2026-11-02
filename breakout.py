"""실행: python breakout.py (Python 표준 라이브러리만 사용)"""

import math
import random
import tkinter as tk


class Breakout:
    WIDTH, HEIGHT = 800, 600
    PADDLE_WIDTH, PADDLE_HEIGHT = 110, 14
    BALL_RADIUS = 9
    BALL_SPEED = 6

    def __init__(self, root):
        self.root = root
        root.title("블록깨기 | tkinter")
        root.resizable(False, False)
        self.canvas = tk.Canvas(
            root, width=self.WIDTH, height=self.HEIGHT,
            bg="#101827", highlightthickness=0,
        )
        self.canvas.pack()
        self.keys = set()
        root.bind("<KeyPress>", self.key_down)
        root.bind("<KeyRelease>", lambda event: self.keys.discard(event.keysym))
        root.bind("<FocusOut>", lambda event: self.keys.clear())
        self.reset()
        self.tick()

    def reset(self):
        self.canvas.delete("all")
        self.keys.clear()
        self.score, self.lives = 0, 3
        self.state = "ready"
        self.hud = self.canvas.create_text(
            20, 22, anchor="w", fill="white", font=("맑은 고딕", 14, "bold")
        )
        self.canvas.create_text(
            self.WIDTH / 2, self.HEIGHT - 18, fill="#94a3b8",
            text="← → / A D: 이동    Space: 시작·일시정지    R: 다시 시작",
            font=("맑은 고딕", 11),
        )
        self.bricks = []
        colors = ["#f87171", "#fb923c", "#facc15", "#4ade80", "#38bdf8"]
        gap, columns, margin = 8, 10, 35
        brick_width = (self.WIDTH - margin * 2 - gap * (columns - 1)) / columns
        for row, color in enumerate(colors):
            for col in range(columns):
                x = margin + col * (brick_width + gap)
                y = 65 + row * 32
                brick = self.canvas.create_rectangle(
                    x, y, x + brick_width, y + 24, fill=color, outline=""
                )
                self.bricks.append(brick)
        self.paddle_x = (self.WIDTH - self.PADDLE_WIDTH) / 2
        self.paddle_y = self.HEIGHT - 65
        self.paddle = self.canvas.create_rectangle(
            self.paddle_x, self.paddle_y,
            self.paddle_x + self.PADDLE_WIDTH, self.paddle_y + self.PADDLE_HEIGHT,
            fill="#e2e8f0", outline="",
        )
        self.ball = self.canvas.create_oval(0, 0, 0, 0, fill="white", outline="")
        self.message = self.canvas.create_text(
            self.WIDTH / 2, 340, fill="white", justify="center",
            font=("맑은 고딕", 20, "bold"),
        )
        self.attach_ball()
        self.update_hud()
        self.show_message("블록깨기\nSpace 키를 눌러 시작하세요")

    def show_message(self, text):
        self.canvas.itemconfigure(self.message, text=text)
        self.canvas.tag_raise(self.message)

    def update_hud(self):
        self.canvas.itemconfigure(self.hud, text=f"점수: {self.score}    목숨: {self.lives}")

    def draw_ball(self):
        r = self.BALL_RADIUS
        self.canvas.coords(self.ball, self.x - r, self.y - r, self.x + r, self.y + r)

    def attach_ball(self):
        self.x = self.paddle_x + self.PADDLE_WIDTH / 2
        self.y = self.paddle_y - self.BALL_RADIUS - 2
        self.vx = random.choice((-3.0, 3.0))
        self.vy = -math.sqrt(self.BALL_SPEED ** 2 - self.vx ** 2)
        self.draw_ball()

    def key_down(self, event):
        key = event.keysym
        # 길게 누를 때 발생하는 자동 반복으로 상태가 여러 번 바뀌지 않게 한다.
        if key in self.keys:
            return
        self.keys.add(key)
        if key.lower() == "r":
            self.reset()
        elif key == "space":
            if self.state in ("ready", "paused"):
                self.state = "playing"
                self.show_message("")
            elif self.state == "playing":
                self.state = "paused"
                self.show_message("일시정지\nSpace 키로 계속")

    def move_paddle(self):
        direction = int(bool(self.keys & {"Right", "d", "D"}))
        direction -= int(bool(self.keys & {"Left", "a", "A"}))
        self.paddle_x = max(0, min(
            self.WIDTH - self.PADDLE_WIDTH, self.paddle_x + direction * 8
        ))
        self.canvas.coords(
            self.paddle, self.paddle_x, self.paddle_y,
            self.paddle_x + self.PADDLE_WIDTH, self.paddle_y + self.PADDLE_HEIGHT,
        )

    def move_ball(self):
        # 이동을 작은 단계로 나누어 얇은 블록을 통과하는 현상을 방지한다.
        steps = math.ceil(self.BALL_SPEED / 3)
        r = self.BALL_RADIUS
        for _ in range(steps):
            old_x, old_y = self.x, self.y
            self.x += self.vx / steps
            self.y += self.vy / steps
            if self.x < r:
                self.x, self.vx = r, abs(self.vx)
            elif self.x > self.WIDTH - r:
                self.x, self.vx = self.WIDTH - r, -abs(self.vx)
            if self.y < r + 40:
                self.y, self.vy = r + 40, abs(self.vy)

            if (self.vy > 0 and old_y + r <= self.paddle_y
                    and self.y + r >= self.paddle_y
                    and self.x + r >= self.paddle_x
                    and self.x - r <= self.paddle_x + self.PADDLE_WIDTH):
                self.y = self.paddle_y - r
                offset = (self.x - self.paddle_x - self.PADDLE_WIDTH / 2)
                offset = max(-1, min(1, offset / (self.PADDLE_WIDTH / 2)))
                angle = offset * math.radians(65)
                self.vx = self.BALL_SPEED * math.sin(angle)
                self.vy = -self.BALL_SPEED * math.cos(angle)

            for brick in self.bricks:
                left, top, right, bottom = self.canvas.coords(brick)
                if (self.x + r > left and self.x - r < right
                        and self.y + r > top and self.y - r < bottom):
                    if old_y + r <= top:
                        self.y, self.vy = top - r, -abs(self.vy)
                    elif old_y - r >= bottom:
                        self.y, self.vy = bottom + r, abs(self.vy)
                    elif old_x + r <= left:
                        self.x, self.vx = left - r, -abs(self.vx)
                    else:
                        self.x, self.vx = right + r, abs(self.vx)
                    self.canvas.delete(brick)
                    self.bricks.remove(brick)
                    self.score += 10
                    self.update_hud()
                    break

            if not self.bricks:
                self.state = "won"
                self.show_message("모든 블록을 깼습니다!\nR 키로 다시 시작")
                break
            if self.y - r > self.HEIGHT:
                self.lives -= 1
                self.update_hud()
                if self.lives:
                    self.state = "ready"
                    self.attach_ball()
                    self.show_message("Space 키를 눌러 다시 도전하세요")
                else:
                    self.state = "over"
                    self.show_message(f"게임 오버! 점수: {self.score}\nR 키로 다시 시작")
                break
        self.draw_ball()

    def tick(self):
        if self.state in ("ready", "playing"):
            self.move_paddle()
            if self.state == "ready":
                self.attach_ball()
            else:
                self.move_ball()
        self.root.after(16, self.tick)


if __name__ == "__main__":
    window = tk.Tk()
    Breakout(window)
    window.mainloop()
