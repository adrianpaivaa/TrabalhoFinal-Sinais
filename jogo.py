import pygame
import numpy as np
import sounddevice as sd
import queue
import random
import os
import json
import math

# --- INICIALIZAÇÃO BÁSICA ---
pygame.init()
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Flappy Voice")
clock = pygame.time.Clock()

# Criar o sprite do pássaro usando desenho vetorial
def create_bird_sprite():
    # Criar superfícies para os frames de animação
    frames = []
    sizes = [(40, 40)] * 2  # Dois frames do mesmo tamanho
    
    for size in sizes:
        surf = pygame.Surface(size, pygame.SRCALPHA)
        
        # Corpo do pássaro
        pygame.draw.ellipse(surf, (255, 200, 0), (5, 5, 30, 30))  # Corpo amarelo
        
        # Olho
        pygame.draw.circle(surf, (255, 255, 255), (28, 15), 6)  # Branco do olho
        pygame.draw.circle(surf, (0, 0, 0), (30, 15), 3)  # Pupila
        
        # Bico
        pygame.draw.polygon(surf, (255, 140, 0), [(35, 15), (35, 22), (40, 18)])
        
        frames.append(surf)
    
    # Segundo frame com asa levantada
    pygame.draw.ellipse(frames[1], (230, 180, 0), (8, 15, 20, 8))
    
    return frames

class Bird:
    def __init__(self, x, y):
        self.frames = create_bird_sprite()
        self.current_frame = 0
        self.animation_speed = 0.15
        self.animation_time = 0
        self.rect = pygame.Rect(x, y, 40, 40)
        self.angle = 0
        self.target_angle = 0
    
    def update(self, vy):
        # Atualizar animação
        self.animation_time += self.animation_speed
        self.current_frame = int(self.animation_time) % len(self.frames)
        
        # Calcular ângulo baseado na velocidade vertical
        self.target_angle = math.degrees(math.atan2(vy * 0.2, 1))
        # Suavizar a rotação
        self.angle += (self.target_angle - self.angle) * 0.1
        self.angle = max(-30, min(45, self.angle))
    
    def draw(self, surface):
        # Rotacionar a imagem
        rotated = pygame.transform.rotate(self.frames[self.current_frame], -self.angle)
        # Manter o centro da imagem no mesmo lugar após a rotação
        rect = rotated.get_rect(center=self.rect.center)
        surface.blit(rotated, rect)

# Criar pássaro
bird = Bird(100, SCREEN_HEIGHT // 2)

# --- CORES E FONTES ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
PLAYER_COLOR = (255, 200, 0)
BACKGROUND_COLOR = (20, 24, 82)  # Céu noturno
STARS_COLOR = (255, 255, 240)
GRASS_COLOR = (34, 139, 34)  # Verde escuro para grama
OBSTACLE_COLOR = (110, 220, 190)
SPECTROMETER_COLOR = (120, 255, 140)
MENU_COLOR = (16, 20, 66)  # Menu mais escuro
BUTTON_COLOR = (70, 95, 180)
BUTTON_HOVER_COLOR = (90, 115, 200)

# Carregar fonte personalizada ou usar uma fonte padrão estilizada
try:
    font_title = pygame.font.Font("freesansbold.ttf", 74)  # Fonte padrão mais bold
except:
    font_title = pygame.font.SysFont('Arial', 74, bold=True)

font_score = pygame.font.SysFont('Arial', 48, bold=True)
font_menu = pygame.font.SysFont('Arial', 36, bold=True)
font_debug = pygame.font.SysFont('Consolas', 18)

# --- CLASSES DE CENÁRIO ---
class Cloud:
    def __init__(self):
        self.width = random.randint(80, 160)
        self.height = random.randint(40, 60)
        self.x = random.randint(0, SCREEN_WIDTH)
        self.y = random.randint(50, SCREEN_HEIGHT // 3)
        self.speed = random.uniform(0.2, 0.5)
        
    def move(self):
        self.x -= self.speed
        if self.x + self.width < 0:
            self.x = SCREEN_WIDTH
            self.y = random.randint(50, SCREEN_HEIGHT // 3)

    def draw(self, surface):
        # Desenhar uma nuvem simples 2D
        cloud_color = (180, 180, 200, 100)  # Cor suave com transparência
        
        # Base da nuvem
        cloud_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        cloud_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        pygame.draw.ellipse(cloud_surface, cloud_color, (0, 0, self.width, self.height))
        
        # Detalhes arredondados
        pygame.draw.ellipse(cloud_surface, cloud_color, 
                          (self.width * 0.2, -self.height * 0.2, self.width * 0.3, self.height))
        pygame.draw.ellipse(cloud_surface, cloud_color, 
                          (self.width * 0.5, -self.height * 0.1, self.width * 0.3, self.height))
        
        surface.blit(cloud_surface, cloud_rect)

class Star:
    def __init__(self):
        self.x = random.randint(0, SCREEN_WIDTH)
        self.y = random.randint(0, SCREEN_HEIGHT - 100)
        self.size = random.randint(1, 3)
        self.brightness = random.randint(100, 255)
        self.twinkle_speed = random.uniform(0.02, 0.05)
        self.time = random.random() * 6.28  # Random start phase

    def update(self):
        self.time += self.twinkle_speed
        self.brightness = 155 + int(100 * np.sin(self.time))

    def draw(self, surface):
        color = (min(255, self.brightness), min(255, self.brightness), min(255, self.brightness))
        pygame.draw.circle(surface, color, (self.x, self.y), self.size)

# Criar nuvens e estrelas
clouds = [Cloud() for _ in range(6)]
stars = [Star() for _ in range(50)]

# --- CARREGAR OU CRIAR ARQUIVO DE HIGH SCORE ---
HIGHSCORE_FILE = "highscore.json"
def load_highscore():
    try:
        with open(HIGHSCORE_FILE, 'r') as f:
            return json.load(f)['highscore']
    except:
        return 0

def save_highscore(score):
    with open(HIGHSCORE_FILE, 'w') as f:
        json.dump({'highscore': score}, f)

highscore = load_highscore()

# --- ESTADOS DO JOGO ---
MENU = "menu"
PLAYING = "playing"
GAME_OVER = "game_over"
game_state = MENU

# --- CLASSES DE INTERFACE ---
class Button:
    def __init__(self, x, y, width, height, text):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.is_hovered = False
        self.pulse = 0
        self.pulse_speed = 0.1

    def draw(self, surface):
        # Efeito de pulso para o botão
        self.pulse = (self.pulse + self.pulse_speed) % (2 * np.pi)
        pulse_value = (np.sin(self.pulse) + 1) * 0.5 * 20

        # Cores do botão com gradiente
        color = BUTTON_HOVER_COLOR if self.is_hovered else BUTTON_COLOR
        
        # Desenhar o botão com brilho
        glow_rect = self.rect.inflate(pulse_value if self.is_hovered else 4, pulse_value if self.is_hovered else 4)
        pygame.draw.rect(surface, (*color, 128), glow_rect, border_radius=12)
        pygame.draw.rect(surface, color, self.rect, border_radius=12)
        pygame.draw.rect(surface, WHITE, self.rect, width=2, border_radius=12)
        
        # Texto do botão com sombra
        text_surface = font_menu.render(self.text, True, WHITE)
        text_shadow = font_menu.render(self.text, True, BLACK)
        text_rect = text_surface.get_rect(center=self.rect.center)
        
        surface.blit(text_shadow, (text_rect.x + 2, text_rect.y + 2))
        surface.blit(text_surface, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
            return False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False

# --- CONFIGURAÇÕES VISUAIS ---
class ParticleSystem:
    def __init__(self):
        self.particles = []

    def create_particle(self, x, y, color):
        particle = {
            'x': x,
            'y': y,
            'dx': random.uniform(-2, 2),
            'dy': random.uniform(-2, 2),
            'lifetime': 30,
            'color': color,
            'size': random.randint(2, 4)
        }
        self.particles.append(particle)

    def update(self):
        for particle in self.particles[:]:
            particle['x'] += particle['dx']
            particle['y'] += particle['dy']
            particle['lifetime'] -= 1
            if particle['lifetime'] <= 0:
                self.particles.remove(particle)

    def draw(self, surface):
        for particle in self.particles:
            alpha = int((particle['lifetime'] / 30) * 255)
            color = list(particle['color'])
            if len(color) == 3:
                color.append(alpha)
            s = pygame.Surface((particle['size'] * 2, particle['size'] * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, color, (particle['size'], particle['size']), particle['size'])
            surface.blit(s, (int(particle['x'] - particle['size']), int(particle['y'] - particle['size'])))

particle_system = ParticleSystem()

# --- CONFIGURAÇÕES DE ÁUDIO ---
audio_queue = queue.Queue()
SAMPLE_RATE = 44100
BLOCK_SIZE = 2048
NOISE_THRESHOLD = 0.01
ANALYSIS_SIZE = BLOCK_SIZE * 2
audio_accumulator = np.array([], dtype=np.float32)
fft_data = np.array([]) 

def audio_callback(indata, frames, time_, status):
    audio_queue.put(indata.copy())

stream = sd.InputStream(channels=1, callback=audio_callback, samplerate=SAMPLE_RATE, blocksize=BLOCK_SIZE)
stream.start()


# --- CONFIGURAÇÕES DO JOGADOR E FÍSICA ---
player_vy = 0
GRAVITY = 0.15  # Reduzido para cair mais devagar
LIFT_FORCE = -1.2  # Reduzido para subir mais suavemente
VOLUME_SENSITIVITY = 15  # Reduzido para ter mais controle
MAX_VELOCITY = 5  # Limitar a velocidade máxima

# Atualizar a posição do pássaro para corresponder ao retângulo de colisão
bird.rect.y = SCREEN_HEIGHT // 2

# --- CONFIGURAÇÕES DOS OBSTÁCULOS E JOGO ---
obstacles = []
OBSTACLE_WIDTH = 70
OBSTACLE_SPEED = 4
GAP_HEIGHT = 200
OBSTACLE_FREQUENCY = 2000
last_obstacle_time = 0

score = 0
game_over = False


def create_obstacle():
    gap_center_y = random.randint(GAP_HEIGHT, SCREEN_HEIGHT - GAP_HEIGHT)
    top_rect = pygame.Rect(SCREEN_WIDTH, 0, OBSTACLE_WIDTH, gap_center_y - GAP_HEIGHT // 2)
    bottom_rect = pygame.Rect(SCREEN_WIDTH, gap_center_y + GAP_HEIGHT // 2, OBSTACLE_WIDTH, SCREEN_HEIGHT)
    return {'top': top_rect, 'bottom': bottom_rect, 'passed': False}

# --- FUNÇÕES DE DESENHO ---
def draw_obstacle(surface, rect):
    # Desenhar obstáculo com cor sólida
    pygame.draw.rect(surface, OBSTACLE_COLOR, rect)

def draw_background():
    # Desenhar céu gradiente
    sky_rect = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    for i in range(SCREEN_HEIGHT):
        alpha = i / SCREEN_HEIGHT
        color = (
            int(BACKGROUND_COLOR[0] * (1 - alpha * 0.3)),
            int(BACKGROUND_COLOR[1] * (1 - alpha * 0.3)),
            int(BACKGROUND_COLOR[2] * (1 - alpha * 0.3))
        )
        pygame.draw.line(sky_rect, color, (0, i), (SCREEN_WIDTH, i))
    screen.blit(sky_rect, (0, 0))
    
    # Desenhar estrelas
    for star in stars:
        star.update()
        star.draw(screen)
    
    # Desenhar nuvens
    for cloud in clouds:
        cloud.move()
        cloud.draw(screen)
    
    # Desenhar grama estática
    grass_height = 50
    grass_rect = pygame.Rect(0, SCREEN_HEIGHT - grass_height, SCREEN_WIDTH, grass_height)
    pygame.draw.rect(screen, GRASS_COLOR, grass_rect)
    
    # Linha de divisão suave entre grama e céu
    pygame.draw.line(screen, (44, 159, 44), 
                    (0, SCREEN_HEIGHT - grass_height),
                    (SCREEN_WIDTH, SCREEN_HEIGHT - grass_height), 2)

def draw_menu():
    draw_background()
    
    # Título com efeito de pulso e brilho
    title_text = "FLAPPY VOICE"
    pulse = (pygame.time.get_ticks() * 0.004) % (2 * np.pi)
    scale = 1.0 + np.sin(pulse) * 0.05
    
    # Renderizar título com efeito de gradiente
    for i in range(4, -1, -1):
        color = (255 - i*20, 200 - i*20, 0)
        title_surface = font_title.render(title_text, True, color)
        title_rect = title_surface.get_rect()
        title_rect.center = (SCREEN_WIDTH//2, SCREEN_HEIGHT//4)
        title_rect = title_rect.inflate(i*2*scale, i*2*scale)
        screen.blit(title_surface, title_rect)
    
    # High Score com efeito de brilho
    highscore_text = f"High Score: {highscore}"
    highscore_surface = font_menu.render(highscore_text, True, WHITE)
    highscore_shadow = font_menu.render(highscore_text, True, BLACK)
    highscore_rect = highscore_surface.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//3))
    
    screen.blit(highscore_shadow, (highscore_rect.x + 2, highscore_rect.y + 2))
    screen.blit(highscore_surface, highscore_rect)
    
    # Botões
    start_button.draw(screen)
    quit_button.draw(screen)
    
    # Instruções com efeito de fade
    alpha = (np.sin(pygame.time.get_ticks() * 0.003) + 1) * 0.5 * 255
    instructions = font_debug.render("Use sua voz para controlar a altura do pássaro!", True, WHITE)
    instructions_surface = pygame.Surface(instructions.get_size(), pygame.SRCALPHA)
    instructions_surface.fill((255, 255, 255, int(alpha)))
    instructions.set_alpha(int(alpha))
    screen.blit(instructions, (SCREEN_WIDTH//2 - instructions.get_width()//2, SCREEN_HEIGHT - 50))

def draw_game_over():
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 128))
    screen.blit(overlay, (0, 0))
    
    # Game Over com efeito de pulso
    pulse = (pygame.time.get_ticks() * 0.004) % (2 * np.pi)
    scale = 1.0 + np.sin(pulse) * 0.05
    
    game_over_text = font_title.render("FIM DE JOGO", True, WHITE)
    game_over_rect = game_over_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 100))
    game_over_rect = game_over_rect.inflate(10*scale, 10*scale)
    screen.blit(game_over_text, game_over_rect)
    
    score_text = font_score.render(f"Pontuação: {score}", True, WHITE)
    highscore_text = font_menu.render(f"Recorde: {highscore}", True, WHITE)
    restart_text = font_debug.render("Pressione ESPAÇO para reiniciar", True, WHITE)
    
    screen.blit(score_text, (SCREEN_WIDTH//2 - score_text.get_width()//2, SCREEN_HEIGHT//2))
    screen.blit(highscore_text, (SCREEN_WIDTH//2 - highscore_text.get_width()//2, SCREEN_HEIGHT//2 + 50))
    screen.blit(restart_text, (SCREEN_WIDTH//2 - restart_text.get_width()//2, SCREEN_HEIGHT//2 + 100))

# Criação dos botões do menu
start_button = Button(SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT//2, 200, 50, "JOGAR")
quit_button = Button(SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT//2 + 70, 200, 50, "SAIR")

# --- LOOP PRINCIPAL DO JOGO ---
rms = 0
fft_data_for_viz = np.array([])

running = True
while running:
    # 1. TRATAR EVENTOS
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        if game_state == MENU:
            if start_button.handle_event(event):
                game_state = PLAYING
                score = 0
                obstacles = []
                bird.rect.y = SCREEN_HEIGHT // 2
                player_vy = 0
            elif quit_button.handle_event(event):
                running = False
                
        elif game_state == GAME_OVER:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                game_state = PLAYING
                score = 0
                obstacles = []
                bird.rect.y = SCREEN_HEIGHT // 2
                player_vy = 0

    # 2. PROCESSAR ÁUDIO
    rms = 0
    while not audio_queue.empty():
        audio_data = audio_queue.get_nowait()
        audio_accumulator = np.concatenate((audio_accumulator, audio_data.flatten()))

    if len(audio_accumulator) >= ANALYSIS_SIZE:
        analysis_block = audio_accumulator[:ANALYSIS_SIZE]
        audio_accumulator = audio_accumulator[ANALYSIS_SIZE:]
        
        # Calcular FFT para visualização
        fft_values = np.abs(np.fft.rfft(analysis_block))
        fft_values = np.log10(fft_values + 1) * 10
        fft_data = np.clip(fft_values, 0, 50)
        
        rms = np.sqrt(np.mean(analysis_block**2))

    if game_state == PLAYING:
        # 3. ATUALIZAR FÍSICA DO JOGADOR
        # Aplicar gravidade com suavização
        player_vy += GRAVITY
        
        # Controle de voz com suavização
        if rms > NOISE_THRESHOLD:
            # Calcular força de elevação com base no volume
            lift = LIFT_FORCE - (rms * VOLUME_SENSITIVITY)
            # Aplicar suavização ao movimento
            lift = lift * 0.7  # Suavizar a força
            player_vy += lift
            
            # Adicionar partículas quando o jogador sobe
            for _ in range(3):
                particle_system.create_particle(
                    bird.rect.centerx - 10,
                    bird.rect.centery + 10,
                    (*PLAYER_COLOR, 255)
                )
        
        # Limitar a velocidade máxima
        player_vy = max(-MAX_VELOCITY, min(MAX_VELOCITY, player_vy))
        
        # Aplicar movimento com amortecimento
        bird.rect.y += player_vy
        
        # Atualizar animação do pássaro
        bird.update(player_vy)

        if bird.rect.top < 0:
            bird.rect.top = 0
            player_vy = 0
        if bird.rect.bottom > SCREEN_HEIGHT:
            bird.rect.bottom = SCREEN_HEIGHT
            player_vy = 0

        # 4. GERAR E MOVER OBSTÁCULOS
        current_time = pygame.time.get_ticks()
        if current_time - last_obstacle_time > OBSTACLE_FREQUENCY:
            obstacles.append(create_obstacle())
            last_obstacle_time = current_time

        for obstacle in obstacles:
            obstacle['top'].x -= OBSTACLE_SPEED
            obstacle['bottom'].x -= OBSTACLE_SPEED

        obstacles = [obs for obs in obstacles if obs['top'].right > 0]
        
        # 5. VERIFICAR COLISÃO E PONTUAÇÃO
        for obstacle in obstacles:
            if bird.rect.colliderect(obstacle['top']) or bird.rect.colliderect(obstacle['bottom']):
                game_state = GAME_OVER
                if score > highscore:
                    highscore = score
                    save_highscore(highscore)
            
            if not obstacle['passed'] and obstacle['top'].centerx < bird.rect.centerx:
                obstacle['passed'] = True
                score += 1
                # Adicionar partículas quando pontua
                for _ in range(10):
                    particle_system.create_particle(
                        bird.rect.centerx,
                        bird.rect.centery,
                        SPECTROMETER_COLOR
                    )

    # Atualizar sistema de partículas
    particle_system.update()

    # Renderização
    if game_state == MENU:
        draw_menu()
    else:
        draw_background()
        
        # Desenhar obstáculos
        for obstacle in obstacles:
            draw_obstacle(screen, obstacle['top'])
            draw_obstacle(screen, obstacle['bottom'])
        
        # Desenhar o pássaro
        bird.draw(screen)
        
        # Desenhar sistema de partículas
        particle_system.draw(screen)

        # Desenhar pontuação com sombra
        score_text = font_score.render(str(score), True, WHITE)
        score_shadow = font_score.render(str(score), True, BLACK)
        score_pos = (SCREEN_WIDTH / 2 - score_text.get_width() / 2, 50)
        screen.blit(score_shadow, (score_pos[0] + 2, score_pos[1] + 2))
        screen.blit(score_text, score_pos)

        # Desenhar o espectrômetro com efeito de suavização
        bar_width = 4
        for i, value in enumerate(fft_data[::5]):
            bar_x = 10 + i * bar_width
            bar_height = value * 3
            
            rect_to_draw = (bar_x, int(SCREEN_HEIGHT - bar_height), bar_width, int(bar_height))
            pygame.draw.rect(screen, (*SPECTROMETER_COLOR, 200), rect_to_draw)
            
            # Adicionar brilho no topo das barras
            glow_rect = (bar_x, int(SCREEN_HEIGHT - bar_height), bar_width, 5)
            pygame.draw.rect(screen, WHITE, glow_rect)

        if game_state == GAME_OVER:
            draw_game_over()

    pygame.display.flip()
    clock.tick(60)

stream.stop()
stream.close()
pygame.quit()
