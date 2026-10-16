#!/usr/bin/env python3
"""Onyx Nibble — full-colour Python 3 neon snake arcade for ElbowOS."""
import math, os, random, subprocess, sys

RECORD = "--record" in sys.argv or os.environ.get("ELBOWOS_RECORD") == "1"
PLAY = "--play" in sys.argv
if RECORD or not PLAY:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

W, H, FPS, SECS = 1080, 1920, 30, 15
OUT = os.environ.get("ELBOWOS_MP4", "/home/workdir/artifacts/ONYX_NIBBLE_ElbowOS.mp4")
TITLE, HANDLE = "ONYX NIBBLE", "x.com/ElbowOS"

CELL = 36
COLS, ROWS = W // CELL, (H - 280) // CELL  # leave room for UI
OFFSET_Y = 180

BG = (8, 6, 18)
GRID = (22, 16, 40)
SNAKE_HEAD = (64, 255, 180)
SNAKE_BODY = (0, 200, 140)
ORB = (255, 80, 220)
ORB2 = (80, 220, 255)
GOLD = (255, 210, 60)
WHITE = (240, 240, 255)
MAG = (255, 40, 140)
CYAN = (40, 220, 255)

DIRS = [(0, -1), (1, 0), (0, 1), (-1, 0)]  # up right down left

class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        flags = 0 if PLAY else pygame.HIDDEN
        try:
            self.screen = pygame.display.set_mode((W, H), flags)
        except pygame.error:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            pygame.display.quit()
            pygame.display.init()
            self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption(TITLE)
        self.font_lg = pygame.font.SysFont("DejaVu Sans", 72, bold=True)
        self.font = pygame.font.SysFont("DejaVu Sans", 42, bold=True)
        self.font_sm = pygame.font.SysFont("DejaVu Sans", 28)
        self.clock = pygame.time.Clock()
        self.reset()

    def reset(self):
        self.score = self.combo = self.t = self.flash = 0
        mid_c, mid_r = COLS // 2, ROWS // 2
        self.snake = [(mid_c, mid_r), (mid_c - 1, mid_r), (mid_c - 2, mid_r)]
        self.dir = 1  # right
        self.grow = 0
        self.orbs = []
        self.spawn_orbs(6)
        self.move_timer = 0
        self.speed = 4  # frames per move

    def spawn_orbs(self, n):
        occupied = set(self.snake)
        while len(self.orbs) < n:
            pos = (random.randint(1, COLS - 2), random.randint(1, ROWS - 2))
            if pos not in occupied and pos not in [o[0] for o in self.orbs]:
                col = random.choice([ORB, ORB2, GOLD])
                self.orbs.append([pos, col, random.uniform(0.8, 1.2)])

    def autoplay(self):
        # Simple AI: prefer direction toward nearest orb, avoid wall/self
        if not self.orbs:
            self.spawn_orbs(4)
            return
        head = self.snake[0]
        nearest = min(self.orbs, key=lambda o: abs(o[0][0] - head[0]) + abs(o[0][1] - head[1]))
        tx, ty = nearest[0]
        preferred = []
        if tx > head[0]:
            preferred.append(1)
        elif tx < head[0]:
            preferred.append(3)
        if ty > head[1]:
            preferred.append(2)
        elif ty < head[1]:
            preferred.append(0)
        # try preferred first, then any safe
        candidates = preferred + [d for d in range(4) if d not in preferred]
        for d in candidates:
            if (d + 2) % 4 == self.dir:  # no reverse
                continue
            nx = head[0] + DIRS[d][0]
            ny = head[1] + DIRS[d][1]
            if 0 <= nx < COLS and 0 <= ny < ROWS and (nx, ny) not in self.snake[:-1]:
                self.dir = d
                return

    def tick(self):
        self.t += 1
        self.flash = max(0, self.flash - 1)
        self.move_timer += 1
        if self.move_timer < self.speed:
            return
        self.move_timer = 0
        hx, hy = self.snake[0]
        dx, dy = DIRS[self.dir]
        nx, ny = hx + dx, hy + dy
        # wrap or die? wrap for fun
        nx %= COLS
        ny %= ROWS
        if (nx, ny) in self.snake:
            self.score = max(0, self.score - 50)
            self.combo = 0
            self.flash = 10
            self.reset()
            return
        self.snake.insert(0, (nx, ny))
        ate = False
        for i, orb in enumerate(self.orbs):
            if orb[0] == (nx, ny):
                self.score += 25 + self.combo * 5
                self.combo += 1
                self.grow += 2
                self.flash = 6
                self.orbs.pop(i)
                ate = True
                break
        if not ate and self.grow <= 0:
            self.snake.pop()
        else:
            self.grow = max(0, self.grow - 1)
        if len(self.orbs) < 4:
            self.spawn_orbs(random.randint(2, 4))
        if self.score > 200 and self.speed > 2:
            self.speed = 3

    def draw(self, surf):
        surf.fill(BG)
        # grid
        for c in range(COLS + 1):
            pygame.draw.line(surf, GRID, (c * CELL, OFFSET_Y), (c * CELL, OFFSET_Y + ROWS * CELL), 1)
        for r in range(ROWS + 1):
            pygame.draw.line(surf, GRID, (0, OFFSET_Y + r * CELL), (W, OFFSET_Y + r * CELL), 1)
        # orbs
        for (ox, oy), col, pulse in self.orbs:
            px = ox * CELL + CELL // 2
            py = OFFSET_Y + oy * CELL + CELL // 2
            rad = int(12 + 4 * math.sin(self.t * 0.2 + pulse * 10))
            pygame.draw.circle(surf, col, (px, py), rad)
            pygame.draw.circle(surf, WHITE, (px, py), rad, 2)
        # snake
        for i, (sx, sy) in enumerate(self.snake):
            px = sx * CELL + CELL // 2
            py = OFFSET_Y + sy * CELL + CELL // 2
            col = SNAKE_HEAD if i == 0 else SNAKE_BODY
            size = CELL // 2 - 2 if i == 0 else CELL // 2 - 4
            pygame.draw.circle(surf, col, (px, py), size)
            if i == 0:
                # eyes
                ex = px + DIRS[self.dir][0] * 8
                ey = py + DIRS[self.dir][1] * 8
                pygame.draw.circle(surf, WHITE, (int(ex), int(ey)), 4)
        if self.flash:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((255, 80, 220, 40))
            surf.blit(ov, (0, 0))
        # UI
        title = self.font_lg.render(TITLE, True, CYAN)
        surf.blit(title, title.get_rect(center=(W // 2, 70)))
        sub = self.font_sm.render(HANDLE, True, MAG)
        surf.blit(sub, sub.get_rect(center=(W // 2, 130)))
        sc = self.font.render(f"SCORE  {self.score}", True, WHITE)
        cb = self.font_sm.render(f"STREAK  x{self.combo}   LEN  {len(self.snake)}", True, GOLD)
        hint = self.font_sm.render("arrows nibble  space pause", True, CYAN)
        surf.blit(sc, sc.get_rect(center=(W // 2, H - 140)))
        surf.blit(cb, cb.get_rect(center=(W // 2, H - 90)))
        surf.blit(hint, hint.get_rect(center=(W // 2, H - 46)))

    def play_interactive(self):
        running = True
        paused = False
        while running:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT or (ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE):
                    running = False
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_SPACE:
                        paused = not paused
                    elif not paused:
                        if ev.key in (pygame.K_UP, pygame.K_w) and self.dir != 2:
                            self.dir = 0
                        elif ev.key in (pygame.K_RIGHT, pygame.K_d) and self.dir != 3:
                            self.dir = 1
                        elif ev.key in (pygame.K_DOWN, pygame.K_s) and self.dir != 0:
                            self.dir = 2
                        elif ev.key in (pygame.K_LEFT, pygame.K_a) and self.dir != 1:
                            self.dir = 3
            if not paused:
                self.tick()
            self.draw(self.screen)
            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()

    def record(self):
        frames = FPS * SECS
        cmd = [
            "ffmpeg", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
            "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "20", "-preset", "fast", "-movflags", "+faststart",
            OUT,
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        canvas = pygame.Surface((W, H))
        try:
            for i in range(frames):
                self.autoplay()
                self.tick()
                self.draw(canvas)
                proc.stdin.write(pygame.image.tostring(canvas, "RGB"))
                if i % 30 == 0:
                    print(f"frame {i}/{frames}", flush=True)
        finally:
            proc.stdin.close()
            err = proc.stderr.read().decode("utf-8", "ignore")
            rc = proc.wait()
        if rc != 0:
            raise SystemExit(f"ffmpeg failed ({rc}):\n{err[-1200:]}")
        print("wrote", OUT)
        pygame.quit()

def main():
    g = Game()
    if PLAY and not RECORD:
        g.play_interactive()
    else:
        g.record()

if __name__ == "__main__":
    main()
