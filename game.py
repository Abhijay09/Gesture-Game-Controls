import pygame
import socket
import sys
import math
import random

# ─── NETWORK ─────────────────────────────────────────────────────────────────
UDP_IP   = "127.0.0.1"
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    sock.bind((UDP_IP, UDP_PORT))
    sock.setblocking(0)
except:
    pass

# ─── CONSTANTS ───────────────────────────────────────────────────────────────
SW, SH      = 960, 540
FPS         = 60
GRAVITY     = 0.65
WALK_SPEED  = 6
JUMP_FORCE  = -14
DASH_SPEED  = 18
DASH_DUR    = 10
DASH_CD     = 45

# ─── PALETTE ─────────────────────────────────────────────────────────────────
BG         = (5, 7, 15)
PLAT_COL   = (20, 25, 50)
PLAT_EDGE  = (60, 100, 200)
P_NORMAL   = (80, 180, 255)
P_DASH     = (255, 150, 0)
P_ATTACK   = (255, 255, 255)
ENEMY_COL  = (0, 255, 120)
BULLET_COL = (200, 255, 100)
CHECK_COL  = (0, 220, 255)

# ─── LEVEL DATA ──────────────────────────────────────────────────────────────
PLATFORMS = [
    pygame.Rect(0, 460, 500, 20),
    pygame.Rect(600, 400, 250, 16),
    pygame.Rect(950, 320, 250, 16),
    pygame.Rect(1300, 420, 350, 16),
    pygame.Rect(1750, 350, 300, 16),
    pygame.Rect(2150, 280, 200, 16),
    pygame.Rect(2150, 480, 200, 16),
    pygame.Rect(2500, 400, 400, 16),
    pygame.Rect(3000, 320, 300, 16),
    pygame.Rect(3400, 450, 800, 16),
    pygame.Rect(4300, 350, 300, 16),
    pygame.Rect(4700, 280, 400, 16),
    pygame.Rect(5200, 400, 300, 16),
    pygame.Rect(5600, 320, 300, 16),
    pygame.Rect(6100, 440, 1200, 20),
]

for i in range(0, 8000, 1500):
    PLATFORMS.append(pygame.Rect(i, 520, 900, 20))

CHECKPOINTS = [60, 1800, 3500, 5000, 6200]
WIN_X = 7200

# ─── UTILITIES ───────────────────────────────────────────────────────────────
def make_vignette():
    surf = pygame.Surface((SW, SH), pygame.SRCALPHA)
    for i in range(0, SH, 12):
        for j in range(0, SW, 12):
            dist = math.hypot(j - SW/2, i - SH/2) / (SW/1.8)
            alpha = int(min(255, dist**3 * 255))
            pygame.draw.rect(surf, (0, 0, 0, alpha), (j, i, 12, 12))
    return surf

# ─── CLASSES ─────────────────────────────────────────────────────────────────
class Bullet:
    def __init__(self, x, y, angle):
        self.x, self.y = float(x), float(y)
        self.vx = math.cos(angle) * 4.5
        self.vy = math.sin(angle) * 4.5
        self.rect = pygame.Rect(x, y, 8, 8)
        self.life = 200

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.rect.topleft = (self.x, self.y)
        self.life -= 1

class Enemy:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 32, 32)
        self.fire_cd = random.randint(30, 90)

    def update(self, px, py, bullets, sx):
        if abs(self.rect.x - sx) > SW + 200: return
        self.fire_cd -= 1
        if self.fire_cd <= 0:
            ang = math.atan2(py - self.rect.centery, px - self.rect.centerx)
            bullets.append(Bullet(self.rect.centerx, self.rect.centery, ang))
            self.fire_cd = 110

class Player:
    def __init__(self):
        self.spawn = [60.0, 380.0]
        self.reset_to_spawn()
        self.rect = pygame.Rect(self.x, self.y, 22, 34)
        self.facing = 1
        self.df = 0
        self.dcd = 0
        self.coyote = 0
        self.jbuf = 0
        self.atk_frame = 0

    def reset_to_spawn(self):
        self.x, self.y = self.spawn[0], self.spawn[1]
        self.vx = self.vy = 0.0
        self.on_gnd = False

    def get_attack_rect(self):
        """Returns the current hitbox for the sword swing."""
        if self.atk_frame > 0:
            # Hitbox appears in front of the player based on facing direction
            if self.facing > 0:
                return pygame.Rect(self.rect.right, self.rect.y - 10, 45, 54)
            else:
                return pygame.Rect(self.rect.left - 45, self.rect.y - 10, 45, 54)
        return None

    def update(self, move, action, bullets):
        if action == "DASH" and self.dcd == 0 and self.df == 0:
            self.df = DASH_DUR
            self.dcd = DASH_CD
            self.vy = 0
        if action == "JUMP": self.jbuf = 8
        if action == "ATTACK" and self.atk_frame == 0: 
            self.atk_frame = 12 # Attack lasts 12 frames
        
        if self.dcd > 0: self.dcd -= 1
        if self.atk_frame > 0: self.atk_frame -= 1

        if self.df > 0:
            self.vx = self.facing * DASH_SPEED
            self.df -= 1
        else:
            target_vx = 0
            if move == "LEFT":  target_vx = -WALK_SPEED; self.facing = -1
            if move == "RIGHT": target_vx = WALK_SPEED;  self.facing = 1
            self.vx = target_vx

        if self.df == 0:
            self.vy = min(self.vy + GRAVITY, 18)
        
        if self.on_gnd: self.coyote = 6
        if self.coyote > 0: self.coyote -= 1
        if self.jbuf > 0: self.jbuf -= 1

        if self.jbuf > 0 and self.coyote > 0:
            self.vy = JUMP_FORCE
            self.coyote = 0
            self.jbuf = 0

        self.x += self.vx
        self.rect.x = int(self.x)
        for p in PLATFORMS:
            if self.rect.colliderect(p):
                if self.vx > 0: self.rect.right = p.left
                elif self.vx < 0: self.rect.left = p.right
                self.x = float(self.rect.x)

        self.on_gnd = False
        self.y += self.vy
        self.rect.y = int(self.y)
        for p in PLATFORMS:
            if self.rect.colliderect(p):
                if self.vy > 0:
                    self.rect.bottom = p.top
                    self.vy = 0
                    self.on_gnd = True
                elif self.vy < 0:
                    self.rect.top = p.bottom
                    self.vy = 0
                self.y = float(self.rect.y)

        if self.y > SH + 300: self.die(bullets)

    def die(self, bullets):
        self.reset_to_spawn()
        bullets.clear()

# ─── MAIN ────────────────────────────────────────────────────────────────────
def main():
    pygame.init()
    screen = pygame.display.set_mode((SW, SH))
    pygame.display.set_caption("Neon Runner")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 16)

    vignette = make_vignette()
    player = Player()
    
    enemies = [
        Enemy(1400, 380), Enemy(2200, 240), Enemy(2800, 360),
        Enemy(3800, 410), Enemy(4800, 240), Enemy(5800, 280), Enemy(6500, 400)
    ]
    bullets = []
    
    scroll_x = 0.0
    won = False
    move_input = "IDLE"
    action_input = "IDLE"

    while True:
        try:
            while True:
                data, _ = sock.recvfrom(512)
                raw = data.decode().split("_")
                if len(raw) >= 2:
                    move_input, action_input = raw[0], raw[1]
        except: pass

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:  move_input = "LEFT"
                if event.key == pygame.K_RIGHT: move_input = "RIGHT"
                if event.key == pygame.K_UP:    action_input = "JUMP"
                if event.key == pygame.K_x:     action_input = "DASH"
                if event.key == pygame.K_z:     action_input = "ATTACK"
                if event.key == pygame.K_r:
                    player.spawn = [60.0, 380.0]
                    player.die(bullets)
                    enemies = [Enemy(1400, 380), Enemy(2200, 240), Enemy(2800, 360), 
                               Enemy(3800, 410), Enemy(4800, 240), Enemy(5800, 280), Enemy(6500, 400)]
                    won = False
            if event.type == pygame.KEYUP:
                if event.key in (pygame.K_LEFT, pygame.K_RIGHT): move_input = "IDLE"
                if event.key in (pygame.K_UP, pygame.K_x, pygame.K_z): action_input = "IDLE"

        if not won:
            player.update(move_input, action_input, bullets)
            if action_input in ["JUMP", "DASH", "ATTACK"]: action_input = "IDLE"

            for cx in CHECKPOINTS:
                if abs(player.x - cx) < 30: player.spawn = [float(cx), player.y]

            # ─── ATTACK COLLISION LOGIC ───
            atk_rect = player.get_attack_rect()
            
            for e in enemies[:]:
                e.update(player.x, player.y, bullets, scroll_x)
                if atk_rect and atk_rect.colliderect(e.rect):
                    enemies.remove(e) # Kill enemy
            
            for b in bullets[:]:
                b.update()
                if atk_rect and atk_rect.colliderect(b.rect):
                    bullets.remove(b) # Destroy/Deflect bullet
                elif b.rect.colliderect(player.rect):
                    player.die(bullets)
                    break
                elif b.life <= 0: bullets.remove(b)

            if player.x > WIN_X: won = True

        scroll_x += (player.x - scroll_x - 300) * 0.1
        screen.fill(BG)
        
        # Draw grid
        for i in range(0, SW + 100, 100):
            off = i - (scroll_x * 0.5) % 100
            pygame.draw.line(screen, (15, 20, 40), (off, 0), (off, SH))

        # Platforms
        for p in PLATFORMS:
            rx = p.x - int(scroll_x)
            if -p.w < rx < SW:
                pygame.draw.rect(screen, PLAT_COL, (rx, p.y, p.w, p.h))
                pygame.draw.rect(screen, PLAT_EDGE, (rx, p.y, p.w, 2))

        # Enemies
        for e in enemies:
            rx = e.rect.x - int(scroll_x)
            pygame.draw.rect(screen, ENEMY_COL, (rx, e.rect.y, 32, 32), 2)
            pygame.draw.rect(screen, ENEMY_COL, (rx+12, e.rect.y+12, 8, 8))

        # Bullets
        for b in bullets:
            rx = b.rect.x - int(scroll_x)
            pygame.draw.rect(screen, BULLET_COL, (rx, b.rect.y, 8, 8))

        # Player
        prx = player.rect.x - int(scroll_x)
        p_col = P_DASH if player.df > 0 else (P_ATTACK if player.atk_frame > 0 else P_NORMAL)
        pygame.draw.rect(screen, p_col, (prx, player.rect.y, player.rect.w, player.rect.h))
        
        # ─── DRAW ATTACK SLASH ───
        if player.atk_frame > 0:
            atk_visual_rect = player.get_attack_rect()
            atk_visual_rect.x -= int(scroll_x)
            # Draw a bright arc/slash effect
            pygame.draw.rect(screen, P_ATTACK, atk_visual_rect, 1)
            # Inner "slash" line
            line_x = atk_visual_rect.centerx
            pygame.draw.line(screen, P_ATTACK, (line_x, atk_visual_rect.top), (line_x, atk_visual_rect.bottom), 2)

        # Eye
        eye_x = prx + (14 if player.facing > 0 else 4)
        pygame.draw.rect(screen, BG, (eye_x, player.rect.y + 8, 4, 4))

        screen.blit(vignette, (0, 0))
        dist_txt = font.render(f"PROGRESS: {int(player.x)}/{WIN_X} | ENEMIES: {len(enemies)}", True, (70, 90, 140))
        screen.blit(dist_txt, (20, 20))

        if won:
            msg = font.render("GAME FINISHED - PRESS R TO RESTART", True, P_ATTACK)
            screen.blit(msg, (SW//2 - msg.get_width()//2, SH//2))

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()
