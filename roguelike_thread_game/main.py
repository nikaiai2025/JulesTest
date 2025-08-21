import pygame
import sys
import random
import time

# --- Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
BACKGROUND_COLOR = (10, 10, 30)
PLAYER_COLOR = (255, 255, 0)
PLAYER_SHIELD_COLOR = (0, 255, 255)
PLAYER_RADIUS = 5
OBSTACLE_COLOR = (100, 255, 100)
OBSTACLE_WIDTH = 20
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GOLD = (255, 215, 0)

# Game settings
PLAYER_INITIAL_Y_SPEED = 2
PLAYER_ACCELERATION = 0.1
PLAYER_MAX_Y_SPEED = 5
PLAYER_INITIAL_HP = 100
ITEM_SPAWN_CHANCE = 0.01 # Tuned
ENEMY_SPAWN_CHANCE = 0.015 # Tuned
ENEMY_DAMAGE = 10
HEAL_AMOUNT = 25
SHIELD_DURATION = 5
SPEED_DOWN_DURATION = 8
SPEED_DOWN_FACTOR = 0.5
SCORE_MULT_DURATION = 7
TUNNEL_Y_CHANGE_SPEED = 0.5

# Stage & Boss Settings
STAGE_CONFIGS = {
    1: {'scroll_speed': 2, 'gap': 200, 'boss_trigger': 4000, 'boss_params': {'color': (255, 69, 0), 'vy': 3, 'fire_rate': 0.6, 'proj_speed': 5}},
    2: {'scroll_speed': 2.5, 'gap': 180, 'boss_trigger': 4000, 'boss_params': {'color': (200, 0, 200), 'vy': 4, 'fire_rate': 0.4, 'proj_speed': 6}},
    3: {'scroll_speed': 3, 'gap': 160, 'boss_trigger': 5000, 'boss_params': {'color': (150, 150, 255), 'vy': 5, 'fire_rate': 0.25, 'proj_speed': 7}},
    'endless': {'scroll_speed': 3.5, 'gap': 150, 'speed_increase_rate': 0.0001}
}
BOSS_BATTLE_DURATION = 20
BOSS_DAMAGE = 25
PROJECTILE_DAMAGE = 15

# --- Base Classes ---
class Entity(pygame.sprite.Sprite):
    def __init__(self, game):
        super().__init__()
        self.game = game
    def update(self):
        self.rect.x -= self.game.scroll_speed
        if self.rect.right < 0: self.kill()

class Item(Entity):
    def __init__(self, game, center_pos, size):
        super().__init__(game)
        self.rect = pygame.Rect(0, 0, size, size)
        self.rect.center = center_pos
    def apply_effect(self, player): pass

class Enemy(Entity):
    def __init__(self, game, center_pos):
        super().__init__(game)
        self.damage = ENEMY_DAMAGE
    def move(self): pass
    def update(self):
        self.move()
        super().update()

# --- Specific Items ---
class HPRecoveryItem(Item):
    def __init__(self, game, center_pos):
        super().__init__(game, center_pos, 10); self.image = pygame.Surface((10, 10)); self.image.fill(RED)
    def apply_effect(self, player): player.heal(HEAL_AMOUNT)

class ShieldItem(Item):
    def __init__(self, game, center_pos):
        super().__init__(game, center_pos, 10); self.image = pygame.Surface((10, 10)); self.image.fill((0, 0, 255))
    def apply_effect(self, player): player.activate_shield(SHIELD_DURATION)

class SpeedDownItem(Item):
    def __init__(self, game, center_pos):
        super().__init__(game, center_pos, 10); self.image = pygame.Surface((10, 10)); self.image.fill((255, 165, 0))
    def apply_effect(self, player): player.activate_speed_down(SPEED_DOWN_DURATION)

class ScoreMultiplierItem(Item):
    def __init__(self, game, center_pos):
        super().__init__(game, center_pos, 12); self.image = pygame.Surface((12, 12)); self.image.fill(GOLD)
    def apply_effect(self, player): player.activate_score_multiplier(SCORE_MULT_DURATION)

class ScreenClearItem(Item):
    def __init__(self, game, center_pos):
        super().__init__(game, center_pos, 10); self.image = pygame.Surface((10, 10)); self.image.fill(WHITE)
    def apply_effect(self, player): self.game.clear_enemies_and_projectiles()

# --- Specific Enemies ---
class StaticEnemy(Enemy):
    def __init__(self, game, center_pos):
        super().__init__(game, center_pos)
        self.image = pygame.Surface((15, 15)); self.image.fill((255, 0, 255))
        self.rect = self.image.get_rect(center=center_pos)

class VerticalPatrolEnemy(Enemy):
    def __init__(self, game, center_pos, top_bound, bottom_bound):
        super().__init__(game, center_pos)
        self.image = pygame.Surface((20, 10)); self.image.fill((200, 50, 200))
        self.rect = self.image.get_rect(center=center_pos)
        self.vy = 2; self.top_bound = top_bound; self.bottom_bound = bottom_bound
    def move(self):
        self.rect.y += self.vy
        if self.rect.top < self.top_bound or self.rect.bottom > self.bottom_bound: self.vy *= -1

# --- Boss-related Classes ---
class Projectile(Entity):
    def __init__(self, game, center_pos, speed):
        super().__init__(game)
        self.image = pygame.Surface((10, 5)); self.image.fill(WHITE)
        self.rect = self.image.get_rect(center=center_pos)
        self.damage = PROJECTILE_DAMAGE
        self.speed = speed
    def update(self): self.rect.x -= self.speed

class Boss(Enemy):
    def __init__(self, game, params):
        super().__init__(game, (SCREEN_WIDTH - 50, SCREEN_HEIGHT / 2))
        self.params = params
        self.image = pygame.Surface((80, 120)); self.image.fill(params['color'])
        self.rect = self.image.get_rect(center=(SCREEN_WIDTH - 50, SCREEN_HEIGHT / 2))
        self.damage = BOSS_DAMAGE
        self.vy = params['vy']
        self.last_shot_time = time.time()

    def move(self):
        self.rect.y += self.vy
        if self.rect.top < 0 or self.rect.bottom > SCREEN_HEIGHT: self.vy *= -1

    def attack(self):
        if time.time() - self.last_shot_time > self.params['fire_rate']:
            projectile = Projectile(self.game, self.rect.center, self.params['proj_speed'])
            self.game.projectiles.add(projectile); self.game.all_sprites.add(projectile)
            self.last_shot_time = time.time()

    def update(self):
        self.move(); self.attack()
        self.rect.x -= self.game.scroll_speed
        if self.rect.left < SCREEN_WIDTH - 90: self.rect.left = SCREEN_WIDTH - 90

# --- Obstacle & Player ---
class Obstacle(Entity):
    def __init__(self, game, x, y, width, height):
        super().__init__(game)
        self.image = pygame.Surface((width, height)); self.image.fill(OBSTACLE_COLOR)
        self.rect = self.image.get_rect(topleft=(x, y))

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.radius = PLAYER_RADIUS
        self.image = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(100, SCREEN_HEIGHT / 2))

        self.y_speed = PLAYER_INITIAL_Y_SPEED; self.direction = 1
        self.hp = PLAYER_INITIAL_HP; self.is_alive = True
        self.shielded = False; self.shield_end_time = 0
        self.speed_down = False; self.speed_down_end_time = 0
        self.score_multiplier = 1; self.score_mult_end_time = 0

        self._draw_player()

    def _draw_player(self):
        self.image.fill((0,0,0,0))
        color = PLAYER_SHIELD_COLOR if self.shielded else PLAYER_COLOR
        pygame.draw.circle(self.image, color, (self.radius, self.radius), self.radius)

    def switch_direction(self): self.direction *= -1
    def take_damage(self, amount):
        if not self.shielded:
            self.hp -= amount
            if self.hp <= 0: self.hp = 0; self.is_alive = False; self.kill()
    def heal(self, amount): self.hp = min(self.hp + amount, PLAYER_INITIAL_HP)
    def activate_shield(self, duration):
        self.shielded = True; self.shield_end_time = time.time() + duration; self._draw_player()
    def activate_speed_down(self, duration):
        self.speed_down = True; self.speed_down_end_time = time.time() + duration
    def activate_score_multiplier(self, duration):
        self.score_multiplier = 2; self.score_mult_end_time = time.time() + duration

    def update(self):
        if self.shielded and time.time() > self.shield_end_time: self.shielded = False; self._draw_player()
        if self.speed_down and time.time() > self.speed_down_end_time: self.speed_down = False
        if self.score_multiplier > 1 and time.time() > self.score_mult_end_time: self.score_multiplier = 1

        max_speed = PLAYER_MAX_Y_SPEED * SPEED_DOWN_FACTOR if self.speed_down else PLAYER_MAX_Y_SPEED
        target_speed = max_speed * self.direction
        if self.y_speed < target_speed: self.y_speed = min(self.y_speed + PLAYER_ACCELERATION, target_speed)
        elif self.y_speed > target_speed: self.y_speed = max(self.y_speed - PLAYER_ACCELERATION, target_speed)
        self.rect.y += self.y_speed
        if self.rect.top < 0: self.rect.top = 0
        if self.rect.bottom > SCREEN_HEIGHT: self.rect.bottom = SCREEN_HEIGHT

# --- Game Class ---
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("ローグライク糸通しゲーム")
        self.clock = pygame.time.Clock()
        self.font_big = pygame.font.Font(None, 74)
        self.font_small = pygame.font.Font(None, 36)
        self.game_state = 'start_menu'
        self.item_types = [HPRecoveryItem, ShieldItem, SpeedDownItem, ScoreMultiplierItem, ScreenClearItem]

    def _reset_game_variables(self):
        self.score = 0
        self.current_stage = 1
        self.stage_config = STAGE_CONFIGS[self.current_stage]
        self.scroll_speed = self.stage_config['scroll_speed']
        self.boss_battle_active = False; self.boss = None
        self.all_sprites = pygame.sprite.Group(); self.obstacles = pygame.sprite.Group()
        self.items = pygame.sprite.Group(); self.enemies = pygame.sprite.Group()
        self.projectiles = pygame.sprite.Group()
        self.player = Player(); self.all_sprites.add(self.player)
        self.tunnel_center_y = SCREEN_HEIGHT / 2
        self.tunnel_y_direction = 1; self.next_obstacle_spawn_x = 0

    def _generate_world(self):
        if self.boss_battle_active: return
        self.tunnel_center_y += self.tunnel_y_direction * TUNNEL_Y_CHANGE_SPEED
        if self.tunnel_center_y < 150 or self.tunnel_center_y > SCREEN_HEIGHT - 150: self.tunnel_y_direction *= -1

        tunnel_gap = self.stage_config['gap']
        while self.next_obstacle_spawn_x < SCREEN_WIDTH + OBSTACLE_WIDTH:
            gap_top = self.tunnel_center_y - tunnel_gap / 2
            gap_bottom = self.tunnel_center_y + tunnel_gap / 2
            center_x = self.next_obstacle_spawn_x + (OBSTACLE_WIDTH / 2)
            top_obs = Obstacle(self, self.next_obstacle_spawn_x, 0, OBSTACLE_WIDTH, gap_top)
            bottom_obs = Obstacle(self, self.next_obstacle_spawn_x, gap_bottom, OBSTACLE_WIDTH, SCREEN_HEIGHT - gap_bottom)
            self.obstacles.add(top_obs, bottom_obs); self.all_sprites.add(top_obs, bottom_obs)
            if random.random() < ITEM_SPAWN_CHANCE:
                item_type = random.choice(self.item_types)
                new_item = item_type(self, (center_x, self.tunnel_center_y)); self.items.add(new_item); self.all_sprites.add(new_item)
            elif random.random() < ENEMY_SPAWN_CHANCE:
                enemy_type = random.choice([StaticEnemy, VerticalPatrolEnemy])
                new_enemy = enemy_type(self, (center_x, self.tunnel_center_y), gap_top, gap_bottom) if enemy_type == VerticalPatrolEnemy else enemy_type(self, (center_x, self.tunnel_center_y))
                self.enemies.add(new_enemy); self.all_sprites.add(new_enemy)
            self.next_obstacle_spawn_x += OBSTACLE_WIDTH
        self.next_obstacle_spawn_x -= self.scroll_speed

    def _start_boss_battle(self):
        self.boss_battle_active = True
        self.boss_battle_start_time = time.time()
        self.boss = Boss(self, self.stage_config['boss_params'])
        self.all_sprites.add(self.boss); self.enemies.add(self.boss)
        for s in list(self.obstacles) + list(self.enemies):
            if s != self.boss: s.kill()

    def _end_boss_battle(self):
        self.boss_battle_active = False
        if self.boss: self.boss.kill(); self.boss = None
        self.score = 0
        if self.current_stage in [1, 2]: self.current_stage += 1
        else: self.current_stage = 'endless'
        self.stage_config = STAGE_CONFIGS[self.current_stage]
        self.scroll_speed = self.stage_config['scroll_speed']

    def _handle_collisions(self):
        if pygame.sprite.spritecollide(self.player, self.obstacles, False): self.player.take_damage(1)
        for item in pygame.sprite.spritecollide(self.player, self.items, True): item.apply_effect(self.player)
        for enemy in pygame.sprite.spritecollide(self.player, self.enemies, False): self.player.take_damage(enemy.damage)
        if pygame.sprite.spritecollide(self.player, self.projectiles, True): self.player.take_damage(PROJECTILE_DAMAGE)

    def clear_enemies_and_projectiles(self):
        for enemy in self.enemies:
            if enemy != self.boss: enemy.kill()
        for proj in self.projectiles: proj.kill()

    def _draw_text(self, text, font, color, x, y, center=True):
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect()
        if center: text_rect.center = (x, y)
        else: text_rect.topleft = (x, y)
        self.screen.blit(text_surface, text_rect)

    # --- Frame-specific methods for each game state ---

    def _handle_events(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                return False # Signal to exit game

            if self.game_state == 'start_menu':
                if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                    self._reset_game_variables()
                    self.game_state = 'playing'

            elif self.game_state == 'playing':
                if event.type == pygame.KEYDOWN and (event.key == pygame.K_SPACE or event.key == pygame.K_UP):
                    self.player.switch_direction()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.player.switch_direction()

            elif self.game_state == 'game_over':
                if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                    self.game_state = 'start_menu'
        return True # Signal to continue game

    def _update_playing_state(self):
        if self.player.is_alive:
            score_to_add = self.scroll_speed * self.player.score_multiplier
            self.score += score_to_add
            if self.current_stage == 'endless':
                self.scroll_speed += STAGE_CONFIGS['endless']['speed_increase_rate']
            if not self.boss_battle_active and self.current_stage != 'endless' and self.score >= self.stage_config['boss_trigger']:
                self._start_boss_battle()
            if self.boss_battle_active and time.time() - self.boss_battle_start_time > BOSS_BATTLE_DURATION:
                self._end_boss_battle()
            self._generate_world()
            self.all_sprites.update()
            self._handle_collisions()
            if not self.player.is_alive:
                self.game_state = 'game_over'

    def _draw_screen(self):
        self.screen.fill(BACKGROUND_COLOR)
        if self.game_state == 'start_menu':
            self._draw_text("Roguelike Threader", self.font_big, WHITE, SCREEN_WIDTH/2, SCREEN_HEIGHT/2 - 50)
            self._draw_text("Press any key to start", self.font_small, WHITE, SCREEN_WIDTH/2, SCREEN_HEIGHT/2 + 50)

        elif self.game_state == 'playing':
            self.all_sprites.draw(self.screen)
            self._draw_playing_ui()

        elif self.game_state == 'game_over':
            self._draw_text("GAME OVER", self.font_big, RED, SCREEN_WIDTH/2, SCREEN_HEIGHT/2 - 50)
            final_stage = f"Stage Reached: {self.current_stage}"
            self._draw_text(final_stage, self.font_small, WHITE, SCREEN_WIDTH/2, SCREEN_HEIGHT/2 + 20)
            self._draw_text(f"Final Score: {int(self.score)}", self.font_small, WHITE, SCREEN_WIDTH/2, SCREEN_HEIGHT/2 + 60)
            self._draw_text("Press any key to return to menu", self.font_small, WHITE, SCREEN_WIDTH/2, SCREEN_HEIGHT/2 + 110)

        pygame.display.flip()

    def _draw_playing_ui(self):
        self._draw_text(f"HP: {int(self.player.hp)}", self.font_small, WHITE, 10, 10, center=False)
        stage_text = f"Stage: {self.current_stage}" if self.current_stage != 'endless' else "Endless"
        score_text = f"Score: {int(self.score)}"
        self._draw_text(stage_text, self.font_small, WHITE, SCREEN_WIDTH - self.font_small.size(stage_text)[0] - 10, 10, center=False)
        self._draw_text(score_text, self.font_small, WHITE, SCREEN_WIDTH - self.font_small.size(score_text)[0] - 10, 40, center=False)

        status_y_offset = 40
        if self.player.shielded:
            shield_time_left = self.player.shield_end_time - time.time()
            self._draw_text(f"Shield: {shield_time_left:.1f}s", self.font_small, PLAYER_SHIELD_COLOR, 10, status_y_offset, center=False); status_y_offset += 30
        if self.player.speed_down:
            speed_time_left = self.player.speed_down_end_time - time.time()
            self._draw_text(f"Slow: {speed_time_left:.1f}s", self.font_small, (255, 165, 0), 10, status_y_offset, center=False); status_y_offset += 30
        if self.player.score_multiplier > 1:
            mult_time_left = self.player.score_mult_end_time - time.time()
            self._draw_text(f"Score x2: {mult_time_left:.1f}s", self.font_small, GOLD, 10, status_y_offset, center=False); status_y_offset += 30

        if self.boss_battle_active:
            time_left = BOSS_BATTLE_DURATION - (time.time() - self.boss_battle_start_time)
            self._draw_text(f"SURVIVE: {max(0, time_left):.1f}s", self.font_small, RED, SCREEN_WIDTH/2, 20)

    def run(self):
        running = True
        while running:
            events = pygame.event.get()
            running = self._handle_events(events)

            if self.game_state == 'playing':
                self._update_playing_state()

            self._draw_screen()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()
