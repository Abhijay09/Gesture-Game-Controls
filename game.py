import pygame
import socket
import sys
import random

# --- 1. NETWORK SETUP ---
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    sock.bind((UDP_IP, UDP_PORT))
    sock.setblocking(0)
except: pass

# --- 2. CONSTANTS & VISUALS ---
SCREEN_W, SCREEN_H = 800, 600
GRAVITY = 0.8
WALK_SPEED = 9
DASH_SPEED = 20 
JUMP_FORCE = -22

# Colors (Neon Palette)
BG_DARK = (10, 10, 15)
PLAYER_GLOW = (0, 255, 255)
PLATFORM_COLOR = (20, 20, 30)
GRASS_GLOW = (0, 255, 100)
SPIKE_GLOW = (255, 30, 80)
BOX_GLOW = (255, 150, 0)

# --- 3. JUICE SYSTEMS ---

class Particle:
    def __init__(self, x, y, color):
        self.x, self.y = x, y
        self.vx = random.uniform(-2, 2)
        self.vy = random.uniform(-2, 2)
        self.life = 255
        self.color = color
        self.size = random.randint(2, 6)

    def draw(self, surface, scroll_x):
        self.x += self.vx
        self.y += self.vy
        self.life -= 10
        if self.life > 0:
            s = pygame.Surface((self.size, self.size))
            s.set_alpha(self.life)
            s.fill(self.color)
            surface.blit(s, (self.x - scroll_x, self.y))

def draw_glow(surface, rect, color, radius):
    """Simulates a bloom/glow shader effect"""
    glow_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for i in range(radius, 0, -5):
        alpha = int(150 * (1 - i / radius))
        pygame.draw.ellipse(glow_surf, (*color, alpha), (radius-i, radius-i, i*2, i*2))
    surface.blit(glow_surf, (rect.centerx - radius, rect.centery - radius), special_flags=pygame.BLEND_RGB_ADD)

# --- 4. GAME OBJECTS ---

class Player:
    def __init__(self):
        self.rect = pygame.Rect(100, 300, 30, 50)
        self.vel_x = 0
        self.vel_y = 0
        self.is_grounded = False
        self.facing_right = True
        self.respawn_point = (100, 300)
        self.is_attacking = False
        self.shake_amount = 0

    def reset_to_checkpoint(self):
        self.rect.topleft = self.respawn_point
        self.vel_x = 0
        self.vel_y = 0

    def update(self, move, action, platforms, boxes, spikes, particles):
        self.vel_y += GRAVITY
        speed = DASH_SPEED if action == "ATTACK" else WALK_SPEED
        self.is_attacking = (action == "ATTACK")
        
        if move == "LEFT": self.vel_x = -speed; self.facing_right = False
        elif move == "RIGHT": self.vel_x = speed; self.facing_right = True
        else: self.vel_x = 0

        if action == "JUMP" and self.is_grounded:
            self.vel_y = JUMP_FORCE
            self.is_grounded = False
            for _ in range(5): particles.append(Particle(self.rect.centerx, self.rect.bottom, (255,255,255)))

        self.rect.x += self.vel_x
        for p in platforms:
            if self.rect.colliderect(p):
                if self.vel_x > 0: self.rect.right = p.left
                if self.vel_x < 0: self.rect.left = p.right
        
        self.is_grounded = False
        self.rect.y += self.vel_y
        for p in platforms:
            if self.rect.colliderect(p):
                if self.vel_y > 0:
                    self.rect.bottom = p.top
                    self.vel_y = 0
                    self.is_grounded = True
                elif self.vel_y < 0:
                    self.rect.top = p.bottom
                    self.vel_y = 0

        for s in [s.rect for s in spikes]:
            if self.rect.colliderect(s): self.reset_to_checkpoint(); self.shake_amount = 20

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock = pygame.time.Clock()
    
    # Pre-render Vignette for Post-Processing
    vignette = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    for i in range(SCREEN_W):
        alpha = int(255 * (i / SCREEN_W))
        pygame.draw.circle(vignette, (0, 0, 0, alpha), (SCREEN_W//2, SCREEN_H//2), SCREEN_W - i, 1)

    player = Player()
    particles = []
    
    # Generate Level
    platforms = [pygame.Rect(0, 450, 1000, 400)]
    checkpoints = []
    spikes = []
    boxes = []
    last_end_x = 1000
    last_y = 450
    
    for i in range(40):
        gap = random.randint(200, 350)
        p_width = random.randint(500, 900)
        last_y = max(200, min(last_y + random.randint(-150, 150), 500))
        new_x = last_end_x + gap
        platforms.append(pygame.Rect(new_x, last_y, p_width, 400))
        if random.random() > 0.5: spikes.append(type('S',(),{'rect':pygame.Rect(new_x+200, last_y-15, 120, 15)}))
        if i % 4 == 0: checkpoints.append(type('C',(),{'rect':pygame.Rect(new_x+50, last_y-80, 10, 80), 'activated':False}))
        last_end_x = new_x + p_width

    scroll_x = 0
    current_move, current_action = "IDLE", "IDLE"

    while True:
        try:
            data, _ = sock.recvfrom(1024)
            current_move, current_action = data.decode().split("_")
        except: pass

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()

        player.update(current_move, current_action, platforms, [], spikes, particles)

        # Screen Shake decay
        if player.shake_amount > 0: player.shake_amount -= 1

        # Camera
        scroll_x += (player.rect.x - scroll_x - 200) * 0.1
        render_offset_x = scroll_x + (random.randint(-player.shake_amount, player.shake_amount) if player.shake_amount > 0 else 0)

        # Draw
        screen.fill(BG_DARK)
        
        # 1. PARALLAX STARS
        random.seed(42)
        for _ in range(100):
            px = (random.randint(0, 3000) - render_offset_x * 0.2) % SCREEN_W
            py = random.randint(0, SCREEN_H)
            pygame.draw.circle(screen, (70, 70, 100), (int(px), py), 1)

        # 2. RENDER PLATFORMS
        for p in platforms:
            pygame.draw.rect(screen, PLATFORM_COLOR, (p.x - render_offset_x, p.y, p.w, p.h))
            pygame.draw.rect(screen, GRASS_GLOW, (p.x - render_offset_x, p.y, p.w, 4))
            if random.random() > 0.99: # Random glow flickers
                 draw_glow(screen, p, GRASS_GLOW, 40)

        # 3. SPIKES
        for s in spikes:
            pygame.draw.rect(screen, SPIKE_GLOW, (s.rect.x - render_offset_x, s.rect.y, s.rect.w, s.rect.h))
            draw_glow(screen, s.rect, SPIKE_GLOW, 30)

        # 4. PLAYER & GLOW
        p_rect_onscreen = pygame.Rect(player.rect.x - render_offset_x, player.rect.y, player.rect.w, player.rect.h)
        draw_glow(screen, player.rect.move(-render_offset_x, 0), PLAYER_GLOW, 60)
        pygame.draw.rect(screen, PLAYER_GLOW, p_rect_onscreen, border_radius=4)
        
        if player.is_attacking:
            # Attack slash effect
            slash_rect = pygame.Rect(player.rect.right if player.facing_right else player.rect.left-80, player.rect.y-20, 80, 80)
            draw_glow(screen, slash_rect.move(-render_offset_x, 0), (255,255,255), 80)
            player.shake_amount = 5

        # 5. PARTICLES
        for p in particles[:]:
            p.draw(screen, render_offset_x)
            if p.life <= 0: particles.remove(p)

        # 6. POST-PROCESSING: VIGNETTE
        screen.blit(vignette, (0,0), special_flags=pygame.BLEND_RGBA_SUB)

        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()
