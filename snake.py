"""뱀 게임 (tkinter 사용, 추가 설치 불필요)

조작: 방향키 또는 WASD로 이동, P 일시정지, R 재시작, Esc 종료
"""
import random
import tkinter as tk

CELL = 20          # 칸 크기(px)
COLS, ROWS = 30, 24
SPEED = 100        # 이동 간격(ms), 작을수록 빠름

DIRS = {
    "Up": (0, -1), "w": (0, -1),
    "Down": (0, 1), "s": (0, 1),
    "Left": (-1, 0), "a": (-1, 0),
    "Right": (1, 0), "d": (1, 0),
}


class SnakeGame:
    def __init__(self, root):
        self.root = root
        root.title("Snake")
        root.resizable(False, False)

        self.canvas = tk.Canvas(root, width=COLS * CELL, height=ROWS * CELL,
                                bg="#1e1e1e", highlightthickness=0)
        self.canvas.pack()
        self.info = tk.Label(root, font=("Consolas", 12), anchor="w")
        self.info.pack(fill="x")

        self.best = 0
        root.bind("<Key>", self.on_key)
        self.reset()
        self.tick()

    def reset(self):
        cx, cy = COLS // 2, ROWS // 2
        self.snake = [(cx, cy), (cx - 1, cy), (cx - 2, cy)]
        self.direction = (1, 0)
        self.next_dir = (1, 0)
        self.score = 0
        self.paused = False
        self.game_over = False
        self.place_food()
        self.draw()

    def place_food(self):
        free = [(x, y) for x in range(COLS) for y in range(ROWS)
                if (x, y) not in self.snake]
        self.food = random.choice(free) if free else None

    def on_key(self, event):
        key = event.keysym if event.keysym in DIRS else event.keysym.lower()
        if key in DIRS:
            d = DIRS[key]
            # 반대 방향으로는 꺾을 수 없음
            if (d[0] + self.direction[0], d[1] + self.direction[1]) != (0, 0):
                self.next_dir = d
        elif key == "p" and not self.game_over:
            self.paused = not self.paused
            self.draw()
        elif key == "r":
            self.reset()
        elif key == "escape":
            self.root.destroy()

    def tick(self):
        if not self.paused and not self.game_over:
            self.step()
            self.draw()
        self.root.after(SPEED, self.tick)

    def step(self):
        self.direction = self.next_dir
        hx, hy = self.snake[0]
        new_head = (hx + self.direction[0], hy + self.direction[1])

        eating = new_head == self.food
        body = self.snake if eating else self.snake[:-1]
        x, y = new_head
        if not (0 <= x < COLS and 0 <= y < ROWS) or new_head in body:
            self.game_over = True
            self.best = max(self.best, self.score)
            return

        self.snake.insert(0, new_head)
        if eating:
            self.score += 1
            self.place_food()
            if self.food is None:  # 판을 가득 채우면 승리
                self.game_over = True
                self.best = max(self.best, self.score)
        else:
            self.snake.pop()

    def draw(self):
        c = self.canvas
        c.delete("all")

        if self.food:
            fx, fy = self.food
            c.create_oval(fx * CELL + 3, fy * CELL + 3,
                          (fx + 1) * CELL - 3, (fy + 1) * CELL - 3,
                          fill="#e74c3c", outline="")

        for i, (x, y) in enumerate(self.snake):
            color = "#2ecc71" if i == 0 else "#27ae60"
            c.create_rectangle(x * CELL + 1, y * CELL + 1,
                               (x + 1) * CELL - 1, (y + 1) * CELL - 1,
                               fill=color, outline="")

        w, h = COLS * CELL, ROWS * CELL
        if self.game_over:
            msg = "YOU WIN!" if self.food is None else "GAME OVER"
            c.create_text(w / 2, h / 2 - 15, text=msg,
                          fill="white", font=("Consolas", 28, "bold"))
            c.create_text(w / 2, h / 2 + 20, text="R: 재시작   Esc: 종료",
                          fill="#bbbbbb", font=("Consolas", 14))
        elif self.paused:
            c.create_text(w / 2, h / 2, text="PAUSED",
                          fill="white", font=("Consolas", 28, "bold"))

        self.info.config(text=f" 점수: {self.score}   최고: {self.best}   "
                              f"(방향키/WASD 이동, P 일시정지)")


if __name__ == "__main__":
    root = tk.Tk()
    SnakeGame(root)
    root.mainloop()
