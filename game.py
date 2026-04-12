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
except:
    pass 

# --- 2. CONSTANTS ---
SCREEN_W, SCREEN_H = 800, 600
GRAVITY = 0.8
WALK_SPEED = 8
DASH_SPEED = 18 
JUMP_FORCE = -20

# Colors
BG_COLOR = (20, 20, 30)
PLAT_COLOR = (50, 50, 70)
GRASS_TOP = (0, 200, 100)
SPIKE_COLOR = (255, 50, 50)
CHECKPOINT_COL = (255, 255, 0)

class Spike:
    def __init__(self, x, y, width):
        self.rect = pygame.Rect(x, y, width, 20)

class BreakableBox:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 70, 70)
        self.alive = True

class Checkpoint:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 60, 100)
        self.activated = False

class Player:
    def __init__(self):
        self.rect = pygame.Rect(100, 300, 40, 60)
        self.vel_x = 0
        self.vel_y = 0
        self.is_grounded = False
        self.facing_right = True
        self.respawn_point = (100, 300)
        self.is_attacking = False

    def reset_to_checkpoint(self):
        self.rect.topleft = self.respawn_point
        self.vel_x = 0
        self.vel_y = 0

    def update(self, move, action, platforms, boxes, spikes):
        # 1. Gravity
        self.vel_y += GRAVITY
        
        # 2. Instant Input
        speed = DASH_SPEED if action == "ATTACK" else WALK_SPEED
        self.is_attacking = (action == "ATTACK")
        
        if move == "LEFT":
            self.vel_x = -speed
            self.facing_right = False
        elif move == "RIGHT":
            self.vel_x = speed
            self.facing_right = True
        else:
            self.vel_x = 0 # Zero Slipperiness

        if action == "JUMP" and self.is_grounded:
            self.vel_y = JUMP_FORCE
            self.is_grounded = False

        # 3. Horizontal Movement & Wall Collisions
        self.rect.x += self.vel_x
        for p in platforms:
            if self.rect.colliderect(p):
                if self.vel_x > 0: self.rect.right = p.left
                if self.vel_x < 0: self.rect.left = p.right

        # 4. Vertical Movement & Floor Collisions
        self.is_grounded = False
        self.rect.y += self.vel_y
        for p in platforms:
            if self.rect.colliderect(p):
                if self.vel_y > 0: # Landing
                    self.rect.bottom = p.top
                    self.vel_y = 0
                    self.is_grounded = True
                elif self.vel_y < 0: # Ceiling
                    self.rect.top = p.bottom
                    self.vel_y = 0
        
        for b in boxes:
            if b.alive and self.rect.colliderect(b.rect):
                if self.vel_y > 0:
                    self.rect.bottom = b.rect.top
                    self.vel_y = 0
                    self.is_grounded = True

        # 5. Death Checks (Spikes or Falling)
        for s in spikes:
            if self.rect.colliderect(s.rect):
                self.reset_to_checkpoint()
        
        if self.rect.y > SCREEN_H + 500: # Fell into pit
            self.reset_to_checkpoint()

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock = pygame.time.Clock()
    player = Player()
    
    # --- LEVEL GENERATION (Side-Scroller Style) ---
    platforms = [pygame.Rect(0, 450, 800, 200)] # Starting Zone
    checkpoints = [Checkpoint(100, 350)]
    spikes = []
    boxes = []

    last_end_x = 800
    last_y = 450
    
    # Generate a linear horizontal level
    for i in range(40):
        # Gap between platforms
        gap = random.randint(150, 300)
        
        # Next platform stats
        p_width = random.randint(400, 700) # MUCH LARGER
        # Vertical shift (limited to ensure you can always jump up)
        last_y = max(150, min(last_y + random.randint(-150, 150), 500))
        
        # THE NO-HEAD-BONK RULE: 
        # New X starts AFTER the old X ends.
        new_x = last_end_x + gap
        plat = pygame.Rect(new_x, last_y, p_width, 300)
        platforms.append(plat)
        
        # Add Spikes in the gaps or on platforms
        if random.random() > 0.6:
            spikes.append(Spike(new_x + 100, last_y - 20, 100))
        
        # Add Boxes
        if random.random() > 0.5:
            boxes.append(BreakableBox(new_x + 300, last_y - 70))
            
        # Checkpoints every few platforms
        if i % 5 == 0:
            checkpoints.append(Checkpoint(new_x + 50, last_y - 100))
            
        last_end_x = new_x + p_width

    # Final Win Goal
    win_flag = pygame.Rect(last_end_x - 200, last_y - 200, 100, 200)

    scroll_x = 0
    current_move, current_action = "IDLE", "IDLE"

    while True:
        try:
            data, _ = sock.recvfrom(1024)
            msg = data.decode().split("_")
            current_move, current_action = msg[0], msg[1]
        except: pass

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()

        player.update(current_move, current_action, platforms, boxes, spikes)

        # Attack
        if player.is_attacking:
            sword = player.rect.inflate(100, 100)
            for b in boxes:
                if sword.colliderect(b.rect): b.alive = False

        # Checkpoints
        for cp in checkpoints:
            if player.rect.colliderect(cp.rect):
                player.respawn_point = (cp.rect.x + 20, cp.rect.y + 20)
                cp.activated = True

        # CAMERA: Smooth Horizontal Follow
        scroll_x += (player.rect.x - scroll_x - 200) * 0.1

        if player.rect.colliderect(win_flag):
            print("LEVEL COMPLETE!"); pygame.quit(); sys.exit()

        # --- DRAWING ---
        screen.fill(BG_COLOR)
        
        # All game objects must be drawn with "- scroll_x"
        for p in platforms:
            pygame.draw.rect(screen, PLAT_COLOR, (p.x - scroll_x, p.y, p.w, p.h))
            pygame.draw.rect(screen, GRASS_TOP, (p.x - scroll_x, p.y, p.w, 10))
            
        for s in spikes:
            # Draw Spikes as simple red rectangles/triangles
            pygame.draw.rect(screen, SPIKE_COLOR, (s.rect.x - scroll_x, s.rect.y, s.rect.w, s.rect.h))
            
        for cp in checkpoints:
            c = (0, 255, 0) if cp.activated else CHECKPOINT_COL
            pygame.draw.rect(screen, c, (cp.rect.x - scroll_x, cp.rect.y, 10, 100))
            
        for b in boxes:
            if b.alive:
                pygame.draw.rect(screen, (100, 50, 0), (b.rect.x - scroll_x, b.rect.y, b.rect.w, b.rect.h))

        # Goal
        pygame.draw.rect(screen, (255, 215, 0), (win_flag.x - scroll_x, win_flag.y, win_flag.w, win_flag.h), 5)

        # Player
        p_col = (255, 100, 100) if not player.is_attacking else (255, 255, 255)
        pygame.draw.rect(screen, p_col, (player.rect.x - scroll_x, player.rect.y, player.rect.w, player.rect.h))

        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()
