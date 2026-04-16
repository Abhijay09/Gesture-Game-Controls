import pygame
import socket
import sys
import math
import random

# ─── NETWORK CONFIGURATION ───────────────────────────────────────────────────
UDP_IP   = "127.0.0.1"
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    sock.bind((UDP_IP, UDP_PORT))
    sock.setblocking(0)
except: pass

# ─── CONSTANTS ───────────────────────────────────────────────────────────────
SW, SH      = 960, 540
FPS         = 60
GRAVITY     = 0.82
FRICTION    = 0.72 
ACCEL       = 2.0
MAX_SPEED   = 8.0
JUMP_FORCE  = -15.0

# Vaporwave Palette
CLR_BG      = (10, 5, 20)
CLR_GRID    = (35, 20, 50)
CLR_P       = (255, 0, 255) # Magenta
CLR_C       = (0, 255, 255) # Cyan
CLR_W       = (255, 255, 255)
CLR_BOSS    = (255, 50, 80)
CLR_ORB     = (255, 215, 0)

# ─── WORLD DATA ──────────────────────────────────────────────────────────────
PLATFORMS = [
    pygame.Rect(-300, 480, 1600, 100), # Center Floor
    pygame.Rect(450, 320, 150, 20),
    pygame.Rect(-1300, 500, 1100, 60), # Left Wing Floor
    pygame.Rect(-600, 380, 180, 20),
    pygame.Rect(-950, 280, 180, 20),
    pygame.Rect(-1350, 180, 200, 20),
    pygame.Rect(1200, 480, 1600, 100), # Right Wing Floor
    pygame.Rect(1400, 350, 200, 20),
    pygame.Rect(1850, 240, 200, 20),
    pygame.Rect(2300, 380, 400, 20),
    pygame.Rect(510, 50, 30, 250),     # Tower Up
    pygame.Rect(450, -150, 200, 30),   # Gate Platform
]

BOSS_ROOM = [
    pygame.Rect(-100, -1200, 1400, 40), # Boss Floor
    pygame.Rect(-140, -1900, 40, 750),
    pygame.Rect(1250, -1900, 40, 750),
    pygame.Rect(-100, -1950, 1400, 50),
]

CHECKPOINTS = [
    (100, 400),    # Spawn
    (-1000, 440),  # West
    (1500, 440),   # East
    (520, -210)    # High
]

# ─── CLASSES ─────────────────────────────────────────────────────────────────

class Bullet:
    def __init__(self, x, y, ang, speed, col):
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(math.cos(ang), math.sin(ang)) * speed
        self.rect = pygame.Rect(x, y, 8, 8)
        self.col = col
        self.life = 180

    def update(self, plats):
        self.pos += self.vel
        self.rect.topleft = (self.pos.x, self.pos.y)
        self.life -= 1
        for p in plats:
            if self.rect.colliderect(p): return False
        return self.life > 0

class Player:
    def __init__(self):
        self.spawn = pygame.Vector2(100, 400)
        self.pos = pygame.Vector2(self.spawn)
        self.vel = pygame.Vector2(0, 0)
        self.rect = pygame.Rect(0, 0, 22, 36)
        
        self.hp = 3
        self.orbs = 0
        self.has_dash = False
        self.has_atk = False
        
        self.on_gnd = False
        self.coyote = 0
        self.j_buffer = 0
        self.facing = 1
        self.dash_cd = 0
        self.dash_time = 0
        self.atk_time = 0
        self.iframe = 0
        self.trail = []

    def reset(self, to_spawn=True):
        if to_spawn: self.pos = pygame.Vector2(self.spawn)
        self.vel *= 0
        self.hp = 3
        self.iframe = 60
        self.dash_time = 0
        self.atk_time = 0

    def update(self, move, action, plats):
        if self.iframe > 0: self.iframe -= 1
        if self.dash_cd > 0: self.dash_cd -= 1
        if self.atk_time > 0: self.atk_time -= 1
        if self.coyote > 0: self.coyote -= 1
        if self.j_buffer > 0: self.j_buffer -= 1

        if self.dash_time > 0:
            self.vel.x = self.facing * 18
            self.vel.y = 0
            self.dash_time -= 1
            self.trail.append([self.pos.x, self.pos.y, 8])
        else:
            if move == "LEFT":
                self.vel.x -= ACCEL
                self.facing = -1
            elif move == "RIGHT":
                self.vel.x += ACCEL
                self.facing = 1
            else:
                self.vel.x *= FRICTION
                if abs(self.vel.x) < 0.1: self.vel.x = 0
            
            if abs(self.vel.x) > MAX_SPEED: self.vel.x = (self.vel.x/abs(self.vel.x)) * MAX_SPEED
            self.vel.y += GRAVITY

        if action == "JUMP": self.j_buffer = 8
        if action == "DASH" and self.has_dash and self.dash_cd <= 0:
            self.dash_time = 10
            self.dash_cd = 45
        if action == "ATTACK" and self.has_atk and self.atk_time <= 0:
            self.atk_time = 12

        if self.j_buffer > 0 and self.coyote > 0:
            self.vel.y = JUMP_FORCE
            self.coyote = 0
            self.j_buffer = 0

        # Movement X
        self.pos.x += self.vel.x
        self.rect.topleft = (self.pos.x, self.pos.y)
        for p in plats:
            if self.rect.colliderect(p):
                if self.vel.x > 0: self.rect.right = p.left
                if self.vel.x < 0: self.rect.left = p.right
                self.pos.x = self.rect.x
                self.vel.x = 0

        # Movement Y
        self.on_gnd = False
        self.pos.y += self.vel.y
        self.rect.topleft = (self.pos.x, self.pos.y)
        for p in plats:
            if self.rect.colliderect(p):
                if self.vel.y > 0:
                    self.rect.bottom = p.top
                    self.on_gnd = True
                    self.coyote = 8
                    self.vel.y = 0
                elif self.vel.y < 0:
                    self.rect.top = p.bottom
                    self.vel.y = 0
                self.pos.y = self.rect.y

        self.trail = [[t[0], t[1], t[2]-1] for t in self.trail if t[2] > 0]

# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    pygame.init()
    screen = pygame.display.set_mode((SW, SH))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Consolas", 18, bold=True)
    
    player = Player()
    bullets = []
    enemies = [pygame.Rect(x, y, 40, 40) for x, y in [(-500, 440), (1400, 440), (2200, 440), (1800, 310)]]
    e_timers = [0] * len(enemies)
    
    orbs = [pygame.Rect(o[0], o[1], 30, 30) for o in [(-1280, 140), (2500, 340), (490, -400)]]
    up_dash = pygame.Rect(-1300, 440, 40, 40)
    up_atk  = pygame.Rect(2500, 440, 40, 40)
    gate = pygame.Rect(450, -150, 200, 30)
    
    boss_obj = None
    move_in, act_in = "IDLE", "IDLE"
    scroll = pygame.Vector2(0, 0)

    while True:
        try:
            while True: 
                data, _ = sock.recvfrom(512)
                raw = data.decode().split("_")
                if len(raw) >= 2: move_in, act_in = raw[0], raw[1]
        except: pass

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:  move_in = "LEFT"
                if event.key == pygame.K_RIGHT: move_in = "RIGHT"
                if event.key == pygame.K_UP:    act_in = "JUMP"
                if event.key == pygame.K_x:     act_in = "DASH"
                if event.key == pygame.K_z:     act_in = "ATTACK"
                if event.key == pygame.K_r:     player.spawn=(100,400); player.reset()
            if event.type == pygame.KEYUP:
                if event.key in (pygame.K_LEFT, pygame.K_RIGHT): move_in = "IDLE"
                if event.key in (pygame.K_UP, pygame.K_x, pygame.K_z): act_in = "IDLE"

        current_plats = PLATFORMS + BOSS_ROOM
        if player.orbs < 3: current_plats.append(gate)
        
        player.update(move_in, act_in, current_plats)
        if act_in in ["JUMP", "DASH", "ATTACK"]: act_in = "IDLE"

        if player.hp <= 0 or player.pos.y > 1100: player.reset()
        for cp in CHECKPOINTS:
            if player.rect.colliderect(pygame.Rect(cp[0], cp[1]-100, 40, 200)):
                player.spawn = pygame.Vector2(cp)

        if player.rect.colliderect(up_dash): player.has_dash = True; up_dash.y = 9000
        if player.rect.colliderect(up_atk):  player.has_atk = True;  up_atk.y = 9000
        for o in orbs[:]:
            if player.rect.colliderect(o): player.orbs += 1; orbs.remove(o)

        atk_rect = None
        if player.atk_time > 0:
            atk_rect = pygame.Rect(player.rect.x + (25 if player.facing > 0 else -60), player.rect.y-10, 60, 56)

        for i, e in enumerate(enemies[:]):
            e_timers[i] += 1
            if e_timers[i] > 95:
                ang = math.atan2(player.pos.y - e.y, player.pos.x - e.x)
                bullets.append(Bullet(e.centerx, e.centery, ang, 4.5, CLR_P))
                e_timers[i] = 0
            if atk_rect and e.colliderect(atk_rect):
                enemies.pop(i); e_timers.pop(i); break
            if player.rect.colliderect(e) and player.iframe == 0:
                player.hp -= 1; player.iframe = 60

        for b in bullets[:]:
            if not b.update(current_plats): bullets.remove(b); continue
            if player.rect.colliderect(b.rect) and player.iframe == 0:
                player.hp -= 1; player.iframe = 60; bullets.remove(b)

        if player.pos.y < -1200 and not boss_obj: 
            class BossData:
                def __init__(self):
                    self.rect = pygame.Rect(500, -1700, 150, 150)
                    self.hp = self.max_hp = 100
                    self.t = 0
            boss_obj = BossData()
        
        if boss_obj:
            boss_obj.t += 1
            if boss_obj.t % 60 == 0:
                for i in range(8):
                    bullets.append(Bullet(boss_obj.rect.centerx, boss_obj.rect.centery, i*math.pi/4, 4, CLR_BOSS))
            if atk_rect and boss_obj.rect.colliderect(atk_rect): boss_obj.hp -= 0.5
            if boss_obj.hp <= 0: boss_obj = None

        scroll.x += (player.pos.x - scroll.x - SW//2) * 0.1
        scroll.y += (player.pos.y - scroll.y - SH//2) * 0.1
        screen.fill(CLR_BG)
        
        for x in range(0, SW + 100, 100):
            ox = x - (scroll.x * 0.4) % 100
            pygame.draw.line(screen, CLR_GRID, (ox, 0), (ox, SH))
        
        for p in current_plats:
            pygame.draw.rect(screen, (25, 15, 40), (p.x-scroll.x, p.y-scroll.y, p.w, p.h))
            pygame.draw.rect(screen, CLR_P, (p.x-scroll.x, p.y-scroll.y, p.w, p.h), 1)

        for cp in CHECKPOINTS:
            pygame.draw.rect(screen, (0, 45, 45), (cp[0]-scroll.x, cp[1]-scroll.y-80, 30, 100))
            pygame.draw.rect(screen, CLR_C, (cp[0]-scroll.x, cp[1]-scroll.y-80, 30, 100), 1)

        for o in orbs: pygame.draw.rect(screen, CLR_ORB, (o.x-scroll.x, o.y-scroll.y, 20, 20))
        if not player.has_dash: pygame.draw.rect(screen, CLR_C, (up_dash.x-scroll.x, up_dash.y-scroll.y, 40, 40), 2)
        if not player.has_atk: pygame.draw.rect(screen, CLR_C, (up_atk.x-scroll.x, up_atk.y-scroll.y, 40, 40), 2)

        for t in player.trail:
            s = pygame.Surface((player.rect.w, player.rect.h))
            s.set_alpha(t[2] * 25); s.fill(CLR_C)
            screen.blit(s, (t[0]-scroll.x, t[1]-scroll.y))

        if player.iframe % 4 < 2:
            pygame.draw.rect(screen, CLR_W, (player.rect.x-scroll.x, player.rect.y-scroll.y, player.rect.w, player.rect.h))
        if atk_rect:
            pygame.draw.rect(screen, CLR_W, (atk_rect.x-scroll.x, atk_rect.y-scroll.y, atk_rect.w, atk_rect.h), 1)

        for e in enemies: pygame.draw.rect(screen, CLR_P, (e.x-scroll.x, e.y-scroll.y, 40, 40), 2)
        for b in bullets: pygame.draw.rect(screen, b.col, (b.rect.x-scroll.x, b.rect.y-scroll.y, 8, 8))
        
        if boss_obj:
            pygame.draw.rect(screen, CLR_BOSS, (boss_obj.rect.x-scroll.x, boss_obj.rect.y-scroll.y, 150, 150), 3)
            pygame.draw.rect(screen, CLR_BOSS, (SW//2-100, 30, (boss_obj.hp/boss_obj.max_hp)*200, 15))

        for i in range(3):
            c = CLR_BOSS if i < player.hp else (45, 30, 45)
            pygame.draw.rect(screen, c, (20 + i*35, 20, 25, 25))
        
        screen.blit(font.render(f"ORBS: {player.orbs}/3", True, CLR_W), (20, 60))
        if player.orbs == 3 and player.pos.y > 0:
            screen.blit(font.render("ACCESS GRANTED: MONOLITH OPEN", True, CLR_C), (SW//2-140, 100))

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()
