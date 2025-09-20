"""
Project: Infernal
Version: 1.0
Author(s): Lukáš Patejdl, Michal Babka, Jáchym Nácovský
Description: A 2D action game built with pygame. The game features a player, enemies, boss encounters, upgrade mechanics, and room generation.
"""

import pygame
import random
import math
import sys
from typing import List

# -------------------------
# Global Constants
# -------------------------
class Constants:
    # Global game window settings
    GAME_WIDTH = 800
    GAME_HEIGHT = 700
    GAME_FPS = 60
    GAME_TILE_SIZE = 40
    DEFAULT_SAVE_ZONE_RANGE = 70

    # Movement
    DIAGONAL_MOVEMENT_FACTOR = 1 / math.sqrt(2)

    # Background offsets (for drawing background image)
    BACKGROUND_X_OFFSET = -2
    BACKGROUND_Y_OFFSET = 0

    # Mouse buttons
    MOUSE_LEFT_BUTTON = 1

    # Timing and animation
    TWO_PI = math.pi * 2

    # Heart drawing positions (for health display)
    HEART_INITIAL_X = 10
    HEART_Y = 5

    # Welcome screen prompt offset
    WELCOME_PROMPT_Y_OFFSET = 240

    # Room inner wall margins (using multipliers of TILE_SIZE)
    INNER_WALL_MARGIN = 2
    INNER_WALL_MULTIPLIER = 3

    # Enemy spawn margin (using multipliers of TILE_SIZE)
    ENEMY_SPAWN_MARGIN = 2


# -------------------------
# Forward Declaration for Type Hinting
# -------------------------
class Game:
    pass


# -------------------------
# Player Class
# -------------------------
class Player(pygame.sprite.Sprite):
    """
    The Player class handles the player character including movement, animations,
    shooting, taking damage, and upgrades.
    """

    MAX_HEALTH: int = 21
    MAX_DAMAGE: int = 10
    MIN_SHOOT_COOLDOWN: int = 1
    MAX_SPEED: int = 15
    INITIAL_HEALTH = 3
    INITIAL_SHOOT_COOLDOWN = 20
    DIAGONAL_MOVEMENT_FACTOR = Constants.DIAGONAL_MOVEMENT_FACTOR
    BLINK_SPEED = 3  # Used to control blinking speed when immune
    ANIMATION_SPEED = 0.1
    IMMUNITY_DURATION_SECONDS = (
        1  # Duration in seconds for which player is immune after damage
    )
    PLAYER_SCALE_FACTOR = 0.3
    PLAYER_ANIMATION_SPEED_INCREMENT = 0.1
    PLAYER_TIME_FACTOR_DIVISOR = 200.0  # Divisor for timing animations
    PLAYER_MIN_ALPHA = 100  # Minimum alpha value during blink
    PLAYER_MAX_ALPHA = 255  # Maximum alpha value during blink

    SHOOT_SOUND = None

    DAMAGED_SOUND = None

    @staticmethod
    def set_shoot_sound() -> None:
        """Set enemy dead sound."""
        Player.SHOOT_SOUND = pygame.mixer.Sound("audio/shoot.mp3")
        Player.SHOOT_SOUND.set_volume(0.1)

    @staticmethod
    def set_damaged_sound() -> None:
        """Set enemy dead sound."""
        Player.DAMAGED_SOUND = pygame.mixer.Sound("audio/recive_damage.mp3")
        Player.DAMAGED_SOUND.set_volume(0.2)

    def __init__(self, x: int, y: int, game: Game) -> None:
        """
        Initialize the player with starting position, load animations, and set initial attributes.
        """
        super().__init__()
        self.game = game


        # Load and scale player images for animations (normal and damaged)
        self.moves: List[List[pygame.Surface]] = []
        # Normal walking animation
        self.moves.append(
            [
                pygame.transform.rotozoom(
                    pygame.image.load(
                        "graphics/player/player_walk_1.png"
                    ).convert_alpha(),
                    0,
                    Player.PLAYER_SCALE_FACTOR,
                ),
                pygame.transform.rotozoom(
                    pygame.image.load(
                        "graphics/player/player_walk_2.png"
                    ).convert_alpha(),
                    0,
                    Player.PLAYER_SCALE_FACTOR,
                ),
            ]
        )

        # Damaged walking animation
        self.moves.append(
            [
                pygame.transform.rotozoom(
                    pygame.image.load(
                        "graphics/player/player_walk_1_damaged.png"
                    ).convert_alpha(),
                    0,
                    Player.PLAYER_SCALE_FACTOR,
                ),
                pygame.transform.rotozoom(
                    pygame.image.load(
                        "graphics/player/player_walk_2_damaged.png"
                    ).convert_alpha(),
                    0,
                    Player.PLAYER_SCALE_FACTOR,
                ),
            ]
        )

        # Initialize attributes
        self.damage: int = 1
        self.earned_points: int = 0
        self.image: pygame.Surface = self.moves[0][0]
        self.rect: pygame.Rect = self.image.get_rect(center=(x, y))
        self.shoot_cooldown: int = 0
        self.is_immune: bool = False
        self.immunity_timer: int = 0
        self.playerMoveIndex: float = 0  # Index for current animation frame
        self.move_set: int = 0  # 0 = normal, 1 = damaged animation set
        self.speed: float = 0  # Will be set later
        self.max_health: int = self.INITIAL_HEALTH
        self.current_health: int = self.INITIAL_HEALTH
        self.shoot_cooldown_set: int = self.INITIAL_SHOOT_COOLDOWN
        self.immunity_duration: int = self.IMMUNITY_DURATION_SECONDS * game.FPS

    def player_animation(self) -> None:
        """
        Update the player's animation frame.
        If immune, apply a blinking effect by adjusting the frame's opacity.
        """
        self.playerMoveIndex += Player.PLAYER_ANIMATION_SPEED_INCREMENT
        if self.playerMoveIndex >= len(self.moves[self.move_set]):
            self.playerMoveIndex = 0

        # Retrieve the current animation frame
        current_frame: pygame.Surface = self.moves[self.move_set][
            int(self.playerMoveIndex)
        ]

        if self.is_immune:
            t: float = (
                pygame.time.get_ticks() / Player.PLAYER_TIME_FACTOR_DIVISOR
            )  # Time factor for oscillation
            alpha: int = int(
                Player.PLAYER_MIN_ALPHA
                + (Player.PLAYER_MAX_ALPHA - Player.PLAYER_MIN_ALPHA)
                * (0.5 + 0.5 * math.sin(Player.BLINK_SPEED * t * Constants.TWO_PI))
            )
            # Create a copy and set its transparency without altering position/size
            frame_with_alpha: pygame.Surface = current_frame.copy()
            frame_with_alpha.set_alpha(alpha)
            self.image = frame_with_alpha
        else:
            self.image = current_frame

    def update(self, walls: pygame.sprite.Group) -> None:
        """
        Update player state: movement, collision with walls, and immunity timer.
        """
        if self.is_immune:
            self.immunity_timer -= 1
            if self.immunity_timer <= 0:
                self.is_immune = False
                self.move_set = 0  # Return to normal animation set
                self.image = self.moves[0][int(self.playerMoveIndex)]

        # Handle movement based on key presses
        keys = pygame.key.get_pressed()
        dx: float = 0
        dy: float = 0

        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx = -self.speed
            self.player_animation()
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx = self.speed
            self.player_animation()
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy = -self.speed
            self.player_animation()
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy = self.speed
            self.player_animation()

        # Normalize diagonal movement so it isn't faster than horizontal/vertical movement
        if dx != 0 and dy != 0:
            dx *= Player.DIAGONAL_MOVEMENT_FACTOR
            dy *= Player.DIAGONAL_MOVEMENT_FACTOR

        # Move horizontally and resolve collisions with walls
        self.rect.x += dx
        wall_hit = pygame.sprite.spritecollide(self, walls, False)
        for wall in wall_hit:
            if dx > 0:
                self.rect.right = wall.rect.left
            elif dx < 0:
                self.rect.left = wall.rect.right

        # Move vertically and resolve collisions with walls
        self.rect.y += dy
        wall_hit = pygame.sprite.spritecollide(self, walls, False)
        for wall in wall_hit:
            if dy > 0:
                self.rect.bottom = wall.rect.top
            elif dy < 0:
                self.rect.top = wall.rect.bottom

        # Keep player within game boundaries
        self.rect.x = max(0, min(self.game.WIDTH - self.rect.width, self.rect.x))
        self.rect.y = max(0, min(self.game.HEIGHT - self.rect.height, self.rect.y))

        # Update shoot cooldown
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1

    def shoot(self, bullets: pygame.sprite.Group) -> None:
        """
        Create and fire a bullet if the shooting cooldown has expired.
        The bullet travels from the player toward the mouse position.
        """
        if self.shoot_cooldown == 0:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            dx: float = mouse_x - self.rect.centerx
            dy: float = mouse_y - self.rect.centery
            dist: float = math.hypot(dx, dy)
            if dist == 0:
                return
            dx, dy = dx / dist, dy / dist  # Normalize direction vector
            bullet = Bullet(self.rect.centerx, self.rect.centery, dx, dy, self.game)
            Player.SHOOT_SOUND.play()
            bullets.add(bullet)
            self.shoot_cooldown = self.shoot_cooldown_set

    def take_damage(self) -> None:
        """
        Decrease player's health when taking damage.
        If in a boss room (based on current level), use boss damage; otherwise, use enemy damage.
        Then enable temporary immunity.
        """
        if not self.is_immune:
            Player.DAMAGED_SOUND.play()
            if ((Room.get_reached_level() + 1) % Enemy.BOSS_LEVEL_INTERVAL) == 0:
                self.current_health -= int(BossEnemy.get_damage())
            else:
                self.current_health -= int(Enemy.get_damage())
            self.is_immune = True
            self.immunity_timer = self.immunity_duration

    def blink(self) -> None:
        """
        Update the player's image with a blinking effect during immunity.
        """
        self.move_set = 1  # Switch to damaged animation set
        current_frame: pygame.Surface = self.moves[self.move_set][
            int(self.playerMoveIndex) % len(self.moves[self.move_set])
        ]
        t: float = pygame.time.get_ticks() / Player.PLAYER_TIME_FACTOR_DIVISOR
        alpha: int = int(
            Player.PLAYER_MIN_ALPHA
            + (Player.PLAYER_MAX_ALPHA - Player.PLAYER_MIN_ALPHA)
            * (0.5 + 0.5 * math.sin(Player.BLINK_SPEED * t * Constants.TWO_PI))
        )
        image_with_alpha: pygame.Surface = current_frame.copy()
        image_with_alpha.set_alpha(alpha)
        self.image = image_with_alpha

    def resetLocation(self) -> None:
        """
        Reset player's position to the center of the game window.
        """
        self.rect.center = (self.game.WIDTH // 2, self.game.HEIGHT // 2)

    def set_current_health(self, number: int) -> None:
        """Set player's current health without exceeding maximum health."""
        self.current_health = min(self.max_health, number)

    def heal(self, number: int) -> None:
        """Increase player's health by a given amount without exceeding maximum health."""
        self.current_health = min(self.max_health, self.current_health + number)

    def set_max_health(self, number: int) -> None:
        """
        Set maximum health of the player and adjust current health if needed.
        """
        self.max_health = min(Player.MAX_HEALTH, number)
        self.current_health = min(self.current_health, self.max_health)

    def increase_health(self, number: int) -> None:
        """
        Increase the maximum health of the player.
        """
        self.max_health = min(Player.MAX_HEALTH, self.max_health + number)

    def set_damage(self, number: int) -> None:
        """Set the player's damage value."""
        self.damage = min(Player.MAX_DAMAGE, number)

    def get_damage(self):
        """Return the player's current damage value."""
        return self.damage

    def increase_damage(self, number: int) -> None:
        """Increase player's damage by a given amount."""
        self.damage = min(Player.MAX_DAMAGE, self.damage + number)

    def decrease_shoot_cooldown(self, number: int) -> None:
        """Decrease the player's shooting cooldown."""
        self.shoot_cooldown_set = max(
            Player.MIN_SHOOT_COOLDOWN, self.shoot_cooldown_set - number
        )

    def increase_speed(self, number: int) -> None:
        """Increase the player's movement speed."""
        self.speed = min(Player.MAX_SPEED, self.speed + number)

    def set_speed(self, number: int) -> None:
        """Set the player's movement speed."""
        self.speed = min(Player.MAX_SPEED, number)

    def set_points(self, number: int) -> None:
        """Set the player's score to a specified number."""
        self.earned_points = number

    def add_points(self, number: int) -> None:
        """Add points to the player's score."""
        self.earned_points += number

    def get_points(self) -> int:
        """Return the player's current score."""
        return self.earned_points

    def increase_bullet_speed(self, number: int) -> None:
        """Increase the bullet speed by invoking the Bullet class method."""
        Bullet.increase_bullet_speed(number)


# -------------------------
# Bullet Class
# -------------------------
class Bullet(pygame.sprite.Sprite):
    """
    The Bullet class represents projectiles fired by the player.
    It handles bullet movement, collision detection, and lifetime.
    """

    MAX_BULLET_SPEED: int = 30
    DEFAULT_BULLET_SPEED = 7
    CURRENT_BULLET_SPEED = 7
    INITIAL_LIFETIME = 60
    BULLET_SCALE_FACTOR = 0.12

    @staticmethod
    def set_bullet_speed(number: int) -> None:
        """
        Set the bullet speed, ensuring it does not exceed the maximum allowed.
        """
        Bullet.CURRENT_BULLET_SPEED = min(Bullet.MAX_BULLET_SPEED, number)

    @staticmethod
    def increase_bullet_speed(number: int) -> None:
        """
        Increase bullet speed while capping at the maximum bullet speed.
        """
        Bullet.CURRENT_BULLET_SPEED = min(
            Bullet.MAX_BULLET_SPEED, Bullet.CURRENT_BULLET_SPEED + number
        )

    def __init__(self, x: int, y: int, dx: float, dy: float, game: Game) -> None:
        """
        Initialize a bullet at position (x, y) with a direction (dx, dy).
        """
        super().__init__()
        self.game = game
        # Load and scale the bullet image
        self.image: pygame.Surface = pygame.transform.rotozoom(
            pygame.image.load("graphics/bullets/bullet.png").convert_alpha(),
            0,
            Bullet.BULLET_SCALE_FACTOR,
        )
        self.rect: pygame.Rect = self.image.get_rect(center=(x, y))
        # Set bullet velocity
        self.dx: float = dx * Bullet.CURRENT_BULLET_SPEED
        self.dy: float = dy * Bullet.CURRENT_BULLET_SPEED
        self.lifetime: int = Bullet.INITIAL_LIFETIME

    def update(
        self, walls: pygame.sprite.Group, enemies: pygame.sprite.Group, player: Player
    ) -> None:
        """
        Update bullet's position, check for collisions with walls and enemies,
        and reduce lifetime. Kill the bullet if conditions are met.
        """
        self.rect.x += self.dx
        self.rect.y += self.dy
        self.lifetime -= 1

        # Collision with walls
        if pygame.sprite.spritecollide(self, walls, False):
            self.kill()

        # Collision with enemies
        hits = pygame.sprite.spritecollide(self, enemies, False)
        for enemy in hits:
            enemy.health -= player.get_damage()
            self.kill()
            break

        # Remove bullet if off-screen or lifetime has expired
        if (
            self.rect.right < 0
            or self.rect.left > self.game.WIDTH
            or self.rect.bottom < 0
            or self.rect.top > self.game.HEIGHT
            or self.lifetime <= 0
        ):
            self.kill()


# -------------------------
# Enemy Class
# -------------------------
class Enemy(pygame.sprite.Sprite):
    """
    The Enemy class represents a basic enemy with movement, animation,
    and health management.
    """

    max_health: int = 3
    MAX_SPEED: int = 20
    MAX_DAMAGE: int = 5
    damage: int = 1
    speed: float = 3
    POINTS: int = 5  # Points awarded to player when enemy is destroyed
    BOSS_LEVEL_INTERVAL = 4
    DIRECTION_RANDOMNESS_RANGE = 0.5  # Adds randomness to enemy movement
    MOVEMENT_CHANGE_INTERVAL = (30, 90)
    DEFAULT_DAMAGE = 1
    ENEMY_MOVEMENT_CHANGE_MIN = 30
    ENEMY_MOVEMENT_CHANGE_MAX = 90
    ENEMY_SCALE_FACTOR = 0.3
    ENEMY_ANIMATION_SPEED_INCREMENT = 0.1
    DEAD_ENEMY_SOUND = None

    @staticmethod
    def set_sound() -> None:
        """Set enemy dead sound."""
        Enemy.DEAD_ENEMY_SOUND = pygame.mixer.Sound("audio/dead_enemy.mp3")
        Enemy.DEAD_ENEMY_SOUND.set_volume(0.2)

    @staticmethod
    def get_damage() -> int:
        """Return the current damage value of an enemy."""
        return Enemy.damage

    @staticmethod
    def increase_damage(number: int) -> None:
        """Increase enemy damage by a given number (up to MAX_DAMAGE)."""
        Enemy.damage = min(Enemy.MAX_DAMAGE, Enemy.damage + number)

    @staticmethod
    def set_damage(number: int) -> None:
        """Set the enemy damage to a specific value (capped by MAX_DAMAGE)."""
        Enemy.damage = min(Enemy.MAX_DAMAGE, number)

    @staticmethod
    def set_speed(number: float) -> None:
        """Set the enemy speed (capped by MAX_SPEED)."""
        Enemy.speed = min(Enemy.MAX_SPEED, number)

    @staticmethod
    def increase_speed(number: float) -> None:
        """Increase enemy speed by a given number (capped by MAX_SPEED)."""
        Enemy.speed = min(Enemy.MAX_SPEED, Enemy.speed + number)

    @staticmethod
    def get_speed() -> float:
        """Return the current enemy speed."""
        return Enemy.speed

    @staticmethod
    def set_max_health(number: int) -> None:
        """Set the maximum health of the enemy."""
        Enemy.max_health = number

    @staticmethod
    def increase_max_health(number: int) -> None:
        """Increase the enemy's maximum health by a given number."""
        Enemy.max_health += number

    def __init__(self, x: int, y: int, game: Game) -> None:
        """
        Initialize an enemy at position (x, y), load animations, and set starting attributes.
        """
        super().__init__()

        # Load enemy animation frames and scale images
        self.moves: List[pygame.Surface] = [
            pygame.transform.rotozoom(
                pygame.image.load("graphics/enemies/bat_1.png").convert_alpha(),
                0,
                Enemy.ENEMY_SCALE_FACTOR,
            ),
            pygame.transform.rotozoom(
                pygame.image.load("graphics/enemies/bat_2.png").convert_alpha(),
                0,
                Enemy.ENEMY_SCALE_FACTOR,
            ),
        ]

        self.game = game
        self.rect: pygame.Rect = self.moves[0].get_rect(center=(x, y))
        self.speed: float = Enemy.get_speed()
        self.move_timer: int = 0  # Timer for when to change movement direction
        self.dx: float = 0  # Horizontal velocity component
        self.dy: float = 0  # Vertical velocity component
        self.image: pygame.Surface = self.moves[0]
        self.enemyMoveIndex: float = 0  # Animation frame index
        self.health: int = Enemy.max_health

    def update(self, player: Player, walls: pygame.sprite.Group) -> None:
        """
        Update enemy movement toward the player with added randomness,
        handle collisions with walls, update animation, and check for death.
        """
        if self.move_timer <= 0:
            # Calculate normalized direction vector toward the player
            dx: float = player.rect.centerx - self.rect.centerx
            dy: float = player.rect.centery - self.rect.centery
            dist: float = math.hypot(dx, dy)
            if dist != 0:
                dx, dy = dx / dist, dy / dist
            # Add randomness to the direction
            dx += random.uniform(
                -Enemy.DIRECTION_RANDOMNESS_RANGE, Enemy.DIRECTION_RANDOMNESS_RANGE
            )
            dy += random.uniform(
                -Enemy.DIRECTION_RANDOMNESS_RANGE, Enemy.DIRECTION_RANDOMNESS_RANGE
            )
            dist = math.hypot(dx, dy)
            if dist != 0:
                dx, dy = dx / dist, dy / dist
            self.dx, self.dy = dx * self.speed, dy * self.speed
            self.move_timer = random.randint(
                Enemy.ENEMY_MOVEMENT_CHANGE_MIN, Enemy.ENEMY_MOVEMENT_CHANGE_MAX
            )
        else:
            self.move_timer -= 1

        # Update enemy animation
        self.enemy_animation()

        # Horizontal movement and wall collision
        self.rect.x += self.dx
        wall_hit = pygame.sprite.spritecollide(self, walls, False)
        for wall in wall_hit:
            if self.dx > 0:
                self.rect.right = wall.rect.left
            elif self.dx < 0:
                self.rect.left = wall.rect.right
            self.dx *= -1  # Reverse horizontal direction upon collision

        # Vertical movement and wall collision
        self.rect.y += self.dy
        wall_hit = pygame.sprite.spritecollide(self, walls, False)
        for wall in wall_hit:
            if self.dy > 0:
                self.rect.bottom = wall.rect.top
            elif self.dy < 0:
                self.rect.top = wall.rect.bottom
            self.dy *= -1  # Reverse vertical direction upon collision

        # If health is zero or below, award points to player and remove enemy
        if int(self.health) <= 0:
            player.add_points(Enemy.POINTS)
            Enemy.DEAD_ENEMY_SOUND.play()
            self.kill()

    def enemy_animation(self) -> None:
        """
        Update the enemy animation frame for smooth transitions.
        """
        self.enemyMoveIndex += Enemy.ENEMY_ANIMATION_SPEED_INCREMENT
        if self.enemyMoveIndex >= len(self.moves):
            self.enemyMoveIndex = 0
        self.image = self.moves[int(self.enemyMoveIndex)]


# -------------------------
# Boss Enemy Class
# -------------------------
class BossEnemy(Enemy):
    """
    The BossEnemy class extends the basic Enemy with unique attributes, scaling health and damage,
    and distinct animations.
    """

    max_health: int = 30
    MAX_SPEED: int = 20
    MAX_DAMAGE: int = 10
    damage: int = 5
    speed: float = 1
    POINTS: int = 100  # Points awarded when the boss is defeated
    BOSS_HEALTH_SCALING = 3
    DAMAGE_SCALING_DIVISOR = 4
    BOSS_SCALE_FACTOR = 0.5

    @staticmethod
    def get_speed() -> float:
        """
        Calculate and return the boss's speed based on a scaling factor of the base enemy speed.
        """
        return min(
            BossEnemy.MAX_SPEED, BossEnemy.speed + int(1 / 3 * Enemy.get_speed())
        )

    def __init__(self, x: int, y: int, game: Game) -> None:
        """
        Initialize the boss enemy by calling the Enemy constructor,
        then override attributes and load boss-specific animations.
        """
        super().__init__(x, y, game)
        # Load boss-specific images and scale them
        self.moves = [
            pygame.transform.rotozoom(
                pygame.image.load("graphics/enemies/phoenix1.png").convert_alpha(),
                0,
                BossEnemy.BOSS_SCALE_FACTOR,
            ),
            pygame.transform.rotozoom(
                pygame.image.load("graphics/enemies/phoenix2.png").convert_alpha(),
                0,
                BossEnemy.BOSS_SCALE_FACTOR,
            ),
        ]
        self.speed = BossEnemy.get_speed()
        # Scale health and damage based on current level
        self.health = (
            BossEnemy.max_health
            + BossEnemy.BOSS_HEALTH_SCALING * Room.get_reached_level()
        )
        self.damage = min(
            BossEnemy.MAX_DAMAGE,
            BossEnemy.damage
            * ((Room.get_reached_level() + 1) / BossEnemy.DAMAGE_SCALING_DIVISOR),
        )
        self.rect = self.moves[0].get_rect(center=(x, y))

    @staticmethod
    def get_damage() -> int:
        """Return the current damage value of the boss."""
        return BossEnemy.damage


# -------------------------
# Wall Class
# -------------------------
class Wall(pygame.sprite.Sprite):
    """
    The Wall class represents static obstacles in the game.
    Walls are drawn using a tiled texture.
    """

    texture = None  # Shared texture among all wall instances

    @classmethod
    def load_texture(cls) -> None:
        """Load the wall texture if it has not been loaded already."""
        if cls.texture is None:
            cls.texture = pygame.image.load("graphics/walls/rock2.png").convert()

    def __init__(self, x: int, y: int, width: int, height: int) -> None:
        """
        Initialize a wall at position (x, y) with specified width and height.
        """
        super().__init__()
        Wall.load_texture()  # Ensure texture is loaded once
        # Create a surface with transparency for the wall
        self.image: pygame.Surface = pygame.Surface((width, height), pygame.SRCALPHA)

        # Tile the texture over the entire surface
        tex_width, tex_height = Wall.texture.get_size()
        for i in range(0, width, tex_width):
            for j in range(0, height, tex_height):
                self.image.blit(Wall.texture, (i, j))

        self.rect: pygame.Rect = self.image.get_rect(topleft=(x, y))


# -------------------------
# Room Class
# -------------------------
class Room:
    """
    The Room class generates the game level, including outer walls,
    randomly placed inner walls, and enemy spawning areas.
    """

    POINTS: int = 10  # Points awarded when completing the room
    reached_level: int = 0  # Tracks the current level
    outer_walls: pygame.sprite.Group = None  # Outer walls shared among all rooms
    WALL_VARIATION_RANGE = 3
    ENEMY_SPAWN_SAFE_MULTIPLIER = 2
    BOSS_ROOM_ENEMY_COUNT = 1
    DEFAULT_ROOM_LEVEL = 0

    # Wall placement constants based on TILE_SIZE
    INNER_WALL_MARGIN = Constants.INNER_WALL_MARGIN
    INNER_WALL_MULTIPLIER = Constants.INNER_WALL_MULTIPLIER

    @staticmethod
    def set_reached_level(number: int) -> None:
        """Set the reached level to a specific number."""
        Room.reached_level = number

    @staticmethod
    def increase_reached_level(number: int) -> None:
        """Increment the reached level by a given number."""
        Room.reached_level += number

    @staticmethod
    def get_reached_level() -> int:
        """Return the current reached level."""
        return Room.reached_level

    def __init__(self, save_zone_range: int, game: Game) -> None:
        """
        Initialize a room by creating outer walls (if not already created)
        and generating inner walls and enemy placements.
        """
        self.game = game
        self.walls: pygame.sprite.Group = pygame.sprite.Group()
        self.enemies: pygame.sprite.Group = pygame.sprite.Group()
        self.NUMBER_OF_WALLS: int = 3  # Base count for inner walls
        self.NUMBER_OF_ENEMIES_BASE: int = 1  # Base count for enemies

        # Create outer walls once and add them to the room
        if Room.outer_walls is None:
            Room.outer_walls = pygame.sprite.Group()
            Room.outer_walls.add(Wall(0, 0, game.WIDTH, game.TILE_SIZE))  # Top wall
            Room.outer_walls.add(
                Wall(0, game.HEIGHT - game.TILE_SIZE, game.WIDTH, game.TILE_SIZE)
            )  # Bottom wall
            Room.outer_walls.add(Wall(0, 0, game.TILE_SIZE, game.HEIGHT))  # Left wall
            Room.outer_walls.add(
                Wall(game.WIDTH - game.TILE_SIZE, 0, game.TILE_SIZE, game.HEIGHT)
            )  # Right wall

        self.walls.add(Room.outer_walls)

        # Generate inner walls and spawn enemies
        self.create_room(save_zone_range)

    def create_room(self, save_zone_range: int) -> None:
        """
        Create a room layout with inner walls and enemies.
        Walls are placed avoiding a safe zone in the center.
        Enemies are spawned outside an extended safe zone.
        """
        # Define safe zone for walls in the center
        safe_zone: pygame.Rect = pygame.Rect(
            self.game.WIDTH // 2 - save_zone_range,
            self.game.HEIGHT // 2 - save_zone_range,
            save_zone_range * 2,
            save_zone_range * 2,
        )

        # Place random inner walls avoiding the safe zone
        walls_random: int = random.randint(
            self.NUMBER_OF_WALLS, self.NUMBER_OF_WALLS + Room.WALL_VARIATION_RANGE
        )
        for _ in range(walls_random):
            valid_wall: bool = False
            while not valid_wall:
                x: int = random.randint(
                    self.game.TILE_SIZE * Room.INNER_WALL_MARGIN,
                    self.game.WIDTH - self.game.TILE_SIZE * Room.INNER_WALL_MULTIPLIER,
                )
                y: int = random.randint(
                    self.game.TILE_SIZE * Room.INNER_WALL_MARGIN,
                    self.game.HEIGHT - self.game.TILE_SIZE * Room.INNER_WALL_MULTIPLIER,
                )
                width: int = random.choice(
                    [
                        self.game.TILE_SIZE,
                        self.game.TILE_SIZE * 2,
                        self.game.TILE_SIZE * 3,
                    ]
                )
                height: int = random.choice(
                    [
                        self.game.TILE_SIZE,
                        self.game.TILE_SIZE * 2,
                        self.game.TILE_SIZE * 3,
                    ]
                )
                candidate_rect: pygame.Rect = pygame.Rect(x, y, width, height)
                if not candidate_rect.colliderect(safe_zone) and not any(
                    candidate_rect.colliderect(wall.rect) for wall in self.walls
                ):
                    valid_wall = True
                    self.walls.add(Wall(x, y, width, height))

        # Define extended safe zone for enemy spawning
        enemy_safe_zone: pygame.Rect = pygame.Rect(
            self.game.WIDTH // 2 - save_zone_range * Room.ENEMY_SPAWN_SAFE_MULTIPLIER,
            self.game.HEIGHT // 2 - save_zone_range * Room.ENEMY_SPAWN_SAFE_MULTIPLIER,
            save_zone_range
            * Room.ENEMY_SPAWN_SAFE_MULTIPLIER
            * Room.ENEMY_SPAWN_SAFE_MULTIPLIER,
            save_zone_range
            * Room.ENEMY_SPAWN_SAFE_MULTIPLIER
            * Room.ENEMY_SPAWN_SAFE_MULTIPLIER,
        )

        boss: bool = False
        boss_spawned: bool = False

        # Determine number of enemies based on level
        enemies_random: int = random.randint(
            self.NUMBER_OF_ENEMIES_BASE + int(Room.reached_level / 2),
            self.NUMBER_OF_ENEMIES_BASE + 2 + int(Room.reached_level / 2),
        )

        # Spawn boss every fourth room
        if ((Room.get_reached_level() + 1) % Enemy.BOSS_LEVEL_INTERVAL) == 0:
            boss = True
            enemies_random = self.BOSS_ROOM_ENEMY_COUNT

        # Spawn enemies ensuring they do not fall in the safe zone or collide with walls
        for _ in range(enemies_random):
            if boss_spawned:
                break
            valid_position: bool = False
            while not valid_position:
                x: int = random.randint(
                    self.game.TILE_SIZE * Constants.ENEMY_SPAWN_MARGIN,
                    self.game.WIDTH
                    - self.game.TILE_SIZE * Constants.ENEMY_SPAWN_MARGIN,
                )
                y: int = random.randint(
                    self.game.TILE_SIZE * Constants.ENEMY_SPAWN_MARGIN,
                    self.game.HEIGHT
                    - self.game.TILE_SIZE * Constants.ENEMY_SPAWN_MARGIN,
                )
                # Create temporary enemy for collision checking
                if boss:
                    temp_enemy = BossEnemy(x, y, self.game)
                    boss_spawned = True
                else:
                    temp_enemy = Enemy(x, y, self.game)

                enemy_rect: pygame.Rect = temp_enemy.rect
                if not enemy_rect.colliderect(enemy_safe_zone) and not any(
                    enemy_rect.colliderect(wall.rect) for wall in self.walls
                ):
                    valid_position = True
                    self.enemies.add(temp_enemy)


# -------------------------
# Upgrade Class
# -------------------------
class Upgrade(pygame.Rect):
    """
    The Upgrade class creates an on-screen upgrade option.
    When the player clicks on the upgrade rectangle, the corresponding player method is activated.
    """

    UI_SPACING = 20
    UPGRADE_WIDTH = 240
    UPGRADE_HEIGHT = 550
    IMAGE_OFFSET_Y = 70
    TEXT_OFFSET_Y = 70
    NUMBER_FONT_SIZE = 90
    BORDER_THICKNESS = 10
    UPGRADE_IMAGE_SCALE = 0.7
    NUMBER_OFFSET_Y = 140
    UPGRADE_PANEL_Y = 85

    def __init__(
        self,
        screen: pygame.Surface,
        number: int,
        player: Player,
        function_name: str,
        function_number: int,
    ) -> None:
        """
        Initialize the upgrade rectangle with fixed position, size, and assigned function.
        """
        super().__init__(
            self.UI_SPACING + number * (self.UPGRADE_WIDTH + self.UI_SPACING),
            Upgrade.UPGRADE_PANEL_Y,
            self.UPGRADE_WIDTH,
            self.UPGRADE_HEIGHT,
        )
        self.screen = screen
        self.player = player
        self.function_name = function_name
        self.function_number = function_number

    def activate(self) -> None:
        """
        Activate the upgrade by invoking the associated player method with the specified upgrade value.
        """
        method = getattr(self.player, self.function_name)
        method(self.function_number)

    def draw(self) -> None:
        """
        Draw the upgrade rectangle, its border, an image representing the upgrade, and text showing the function name and value.
        """
        # Create a transparent surface for drawing the upgrade border
        border_thickness: int = Upgrade.BORDER_THICKNESS
        upgrade_surface: pygame.Surface = pygame.Surface(
            (self.width, self.height), pygame.SRCALPHA
        )
        upgrade_surface.fill((0, 0, 0, 0))  # Transparent background

        # Load the texture for the border
        border_image_original: pygame.Surface = pygame.image.load(
            "graphics/walls/rock2.png"
        ).convert_alpha()

        # Create horizontal and vertical borders by scaling the texture
        border_width: int = border_image_original.get_width()
        horizontal_border: pygame.Surface = pygame.transform.scale(
            border_image_original, (border_width, border_thickness)
        )
        border_height: int = border_image_original.get_height()
        vertical_border: pygame.Surface = pygame.transform.scale(
            border_image_original, (border_thickness, border_height)
        )

        # Tile horizontal borders along the top and bottom edges
        for x in range(0, self.width, horizontal_border.get_width()):
            upgrade_surface.blit(horizontal_border, (x, 0))
            upgrade_surface.blit(horizontal_border, (x, self.height - border_thickness))

        # Tile vertical borders along the left and right edges
        for y in range(0, self.height, vertical_border.get_height()):
            upgrade_surface.blit(vertical_border, (0, y))
            upgrade_surface.blit(vertical_border, (self.width - border_thickness, y))

        # Blit the upgrade surface onto the main screen at the upgrade rectangle's position
        self.screen.blit(upgrade_surface, (self.left, self.top))

        # Choose upgrade image based on the function name using pattern matching
        match self.function_name:
            case "increase_damage":
                image_path = "graphics/bullets/bullet.png"
            case "increase_health":
                image_path = "graphics/player/goat2.png"
            case "heal":
                image_path = "graphics/player/goat1.png"
            case "decrease_shoot_cooldown":
                image_path = "graphics/bullets/bullet.png"
            case "increase_speed":
                image_path = "graphics/player/player_walk_2.png"
            case "increase_bullet_speed":
                image_path = "graphics/bullets/bullet.png"

        # Load, scale, and position the upgrade image
        image: pygame.Surface = pygame.image.load(image_path).convert_alpha()
        image = pygame.transform.rotozoom(image, 0, Upgrade.UPGRADE_IMAGE_SCALE)
        image_rect: pygame.Rect = image.get_rect(
            center=(self.centerx, self.centery - Upgrade.IMAGE_OFFSET_Y)
        )
        self.screen.blit(image, image_rect)

        # Render and position the upgrade function name text
        text_to_render: str = self.function_name.replace("_", " ")
        padding: int = 10
        available_width: int = self.width - 2 * padding
        font_size: int = 50
        font: pygame.font.Font = pygame.font.Font(None, font_size)
        text_width, _ = font.size(text_to_render)
        while text_width > available_width and font_size > 10:
            font_size -= 1
            font = pygame.font.Font(None, font_size)
            text_width, _ = font.size(text_to_render)
        text_surface: pygame.Surface = font.render(
            text_to_render, True, (255, 255, 255)
        )
        text_rect: pygame.Rect = text_surface.get_rect(
            center=(self.centerx, self.centery + Upgrade.TEXT_OFFSET_Y)
        )
        self.screen.blit(text_surface, text_rect)

        # Render and position the upgrade value (number)
        font = pygame.font.Font(None, Upgrade.NUMBER_FONT_SIZE)
        number_out: pygame.Surface = font.render(
            f"{self.function_number}", True, (255, 255, 255)
        )
        number_out_rect: pygame.Rect = number_out.get_rect(
            center=(
                self.centerx,
                self.centery + Upgrade.NUMBER_OFFSET_Y + text_rect.height,
            )
        )
        self.screen.blit(number_out, number_out_rect)


# -------------------------
# Game Class
# -------------------------
class Game:
    """
    The Game class manages overall game state, including the main loop, screen rendering,
    level progression, and handling user input for upgrades.
    """

    DEFAULT_SAVE_ZONE_RANGE = Constants.DEFAULT_SAVE_ZONE_RANGE
    INITIAL_ENEMY_SPEED = 1.5
    INITIAL_ENEMY_HEALTH = 3
    HEART_SPACING = 25
    UPGRADE_CHECK_INTERVAL = 1  # Frequency (in levels) to trigger upgrade selection
    ENEMY_HEALTH_INCREASE = 0.4
    ENEMY_SPEED_SMALL_INC = 0.1
    ENEMY_SPEED_LARGE_INC = 0.4
    ENEMY_DAMAGE_INCREASE = 0.2
    HEART_SPACING_FACTOR = 1.5
    LEVEL_INTERVAL_FOR_ENEMY_STATS = 2
    DEATH_TEXT_OFFSET_Y = 150
    WELCOME_PLAYER_OFFSET_Y = 30
    WELCOME_TEXT_Y_OFFSET = 70
    SCORE_TEXT_Y_OFFSET = 145
    UPGRADE_DRAW_DELAY_MS = 500
    HEART_SPACING_STEP = 25
    PLAYER_SCALE_FACTOR = 1.5

    # Color definitions
    WHITE: tuple = (255, 255, 255)

    @staticmethod
    def end_game() -> None:
        """Quit the game and exit."""
        pygame.quit()
        sys.exit(0)

    def __init__(self) -> None:
        """
        Initialize the game window, load resources (background, banners, hearts),
        and set up the initial game state.
        """
        self.WIDTH: int = Constants.GAME_WIDTH
        self.HEIGHT: int = Constants.GAME_HEIGHT
        self.FPS: int = Constants.GAME_FPS
        self.TILE_SIZE: int = Constants.GAME_TILE_SIZE
        self.can_upgrade: bool = False
        self.difficulty: int = 0
        self.save_zone_range: int = Game.DEFAULT_SAVE_ZONE_RANGE

        pygame.init()
        self.screen: pygame.Surface = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("Infernal")
        pygame.display.set_icon(pygame.image.load('graphics/icon/icon.png'))
        self.clock: pygame.time.Clock = pygame.time.Clock()

        # Load and scale the background image
        self.background_image: pygame.Surface = pygame.image.load(
            "graphics/background/ground.png"
        ).convert()
        self.background_image = pygame.transform.rotozoom(self.background_image, 0, 0.2)

        # Load and scale the health banner image
        self.hp_banner: pygame.Surface = pygame.image.load(
            "graphics/background/banner.png"
        ).convert_alpha()
        self.hp_banner = pygame.transform.scale(self.hp_banner, (800, 50))

        # Load, scale, and store heart images for health display
        self.heart_full: pygame.Surface = pygame.image.load(
            "graphics/player/goat1.png"
        ).convert_alpha()
        self.heart_empty: pygame.Surface = pygame.image.load(
            "graphics/player/goat2.png"
        ).convert_alpha()
        self.heart_full = pygame.transform.scale(self.heart_full, (40, 40))
        self.heart_empty = pygame.transform.scale(self.heart_empty, (40, 40))

        self.save_zone_range = Constants.DEFAULT_SAVE_ZONE_RANGE
        bg_music = pygame.mixer.Sound("audio/background_music.mp3")
        bg_music.set_volume(0.05)
        bg_music.play(loops=-1)
        self.setup_game()

    def setup_game(self) -> None:
        """
        Initialize or reset the game state, including player, bullets, room, sprites and sound.
        """
        Bullet.set_bullet_speed(Bullet.DEFAULT_BULLET_SPEED)
        Enemy.set_speed(self.INITIAL_ENEMY_SPEED)
        Room.set_reached_level(Room.DEFAULT_ROOM_LEVEL)
        Enemy.set_max_health(self.INITIAL_ENEMY_HEALTH)
        Enemy.set_damage(Enemy.DEFAULT_DAMAGE)
        Player.set_damaged_sound()
        Player.set_shoot_sound()
        Enemy.set_sound()

        # Create the player in the center of the screen
        self.player: Player = Player(self.WIDTH // 2, self.HEIGHT // 2, self)
        self.player.set_points(0)
        self.player.set_speed(3)

        # Initialize groups for bullets, room elements, and all sprites
        self.bullets: pygame.sprite.Group = pygame.sprite.Group()
        self.room: Room = Room(self.save_zone_range, self)
        self.all_sprites: pygame.sprite.Group = pygame.sprite.Group()
        self.all_sprites.add(self.player)
        self.all_sprites.add(self.room.walls)
        self.all_sprites.add(self.room.enemies)

    def welcome_screen(self) -> None:
        """
        Display the welcome screen with a title, background, and prompt to begin the game.
        """
        welcome_font: pygame.font.Font = pygame.font.Font(None, 100)
        self.screen.blit(
            self.background_image,
            (Constants.BACKGROUND_X_OFFSET, Constants.BACKGROUND_Y_OFFSET),
        )

        text: pygame.Surface = welcome_font.render("WELCOME", True, self.WHITE)
        text_rect: pygame.Rect = text.get_rect(
            center=(self.WIDTH // 2, Game.WELCOME_TEXT_Y_OFFSET)
        )
        self.screen.blit(text, text_rect)

        # Display a static player image on the welcome screen
        player_stand: pygame.Surface = pygame.image.load(
            "graphics/player/player_walk_2.png"
        ).convert_alpha()
        player_stand = pygame.transform.rotozoom(
            player_stand, 0, Game.PLAYER_SCALE_FACTOR
        )
        player_stand_rect: pygame.Rect = player_stand.get_rect(
            center=(self.WIDTH // 2, self.HEIGHT // 2 - Game.WELCOME_PLAYER_OFFSET_Y)
        )
        self.screen.blit(player_stand, player_stand_rect)

        welcome_font = pygame.font.Font(None, 90)
        prompt: pygame.Surface = welcome_font.render(
            "Press SPACE to begin", True, self.WHITE
        )
        prompt_rect: pygame.Rect = prompt.get_rect(
            center=(
                self.WIDTH // 2,
                self.HEIGHT // 2 + Constants.WELCOME_PROMPT_Y_OFFSET,
            )
        )
        self.screen.blit(prompt, prompt_rect)

        pygame.display.update()

    def death_screen(self, player: Player) -> None:
        """
        Display the death screen with the player's final score and a prompt to restart.
        """
        death_font: pygame.font.Font = pygame.font.Font(None, 100)
        self.screen.blit(
            self.background_image,
            (Constants.BACKGROUND_X_OFFSET, Constants.BACKGROUND_Y_OFFSET),
        )

        text: pygame.Surface = death_font.render("YOU DIED", True, self.WHITE)
        text_rect: pygame.Rect = text.get_rect(
            center=(self.WIDTH // 2, self.HEIGHT // 2 - Game.DEATH_TEXT_OFFSET_Y)
        )
        self.screen.blit(text, text_rect)

        score: pygame.Surface = death_font.render(
            f"SCORE: {player.get_points()}", True, self.WHITE
        )
        score_rect: pygame.Rect = score.get_rect(
            center=(
                self.WIDTH // 2,
                self.HEIGHT // 2 - Game.SCORE_TEXT_Y_OFFSET + text_rect.height,
            )
        )
        self.screen.blit(score, score_rect)

        death_font = pygame.font.Font(None, 90)
        prompt: pygame.Surface = death_font.render("Press SPACE to", True, self.WHITE)
        prompt_rect: pygame.Rect = prompt.get_rect(
            center=(self.WIDTH // 2, self.HEIGHT // 2 + 50)
        )
        self.screen.blit(prompt, prompt_rect)

        prompt2: pygame.Surface = death_font.render("PLAY AGAIN", True, self.WHITE)
        prompt_rect2: pygame.Rect = prompt2.get_rect(
            center=(self.WIDTH // 2, self.HEIGHT // 2 + 55 + prompt_rect.height)
        )
        self.screen.blit(prompt2, prompt_rect2)

        pygame.display.update()

    def start(self, welcome: bool) -> None:
        """
        Start the game by displaying the welcome or death screen,
        then wait for the player to press SPACE to begin.
        """
        while True:
            if welcome:
                self.welcome_screen()
            else:
                self.death_screen(self.player)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    Game.end_game()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.setup_game()
                        self.run()

    def new_level(self) -> None:
        """
        Progress to a new level by updating enemy attributes, regenerating the room,
        and triggering an upgrade if the level meets the criteria.
        """
        # Adjust enemy stats for level progression
        if Room.get_reached_level() % Game.LEVEL_INTERVAL_FOR_ENEMY_STATS:
            Enemy.increase_max_health(self.ENEMY_HEALTH_INCREASE)
            if Enemy.get_speed() < 5:
                Enemy.increase_speed(self.ENEMY_SPEED_LARGE_INC)
            else:
                Enemy.increase_speed(self.ENEMY_SPEED_SMALL_INC)
            Enemy.increase_damage(self.ENEMY_DAMAGE_INCREASE)

        Room.increase_reached_level(1)
        self.player.add_points(Room.POINTS)
        self.room = Room(self.save_zone_range, self)
        self.all_sprites.empty()
        self.bullets.empty()
        self.all_sprites.add(self.player)
        self.all_sprites.add(self.room.walls)
        self.all_sprites.add(self.room.enemies)
        self.player.resetLocation()
        self.player.immunity_timer = 0

        # Check if upgrade option should be activated
        if (Room.get_reached_level() + 1) % (self.difficulty + 1) == 0:
            self.can_upgrade = True
            pygame.display.flip()
            self.upgrade()

    def balanced_randint(self, lower: int, upper: int) -> int:
        """
        Return a random integer between lower and upper, ensuring upper > lower.
        """
        if lower >= upper:
            upper = lower + 1
        return random.randint(lower, upper)

    def get_upgrade_rects(self) -> List[Upgrade]:
        """
        Create three random upgrade options with associated functions and values.
        Returns a list of Upgrade objects.
        """
        functions: List[str] = [
            "increase_damage",
            "increase_health",
            "heal",
            "decrease_shoot_cooldown",
            "increase_speed",
            "increase_bullet_speed",
        ]
        upgrade_rects: List[Upgrade] = []
        for i in range(3):
            chosen_function: str = random.choice(functions)
            functions.remove(chosen_function)

            # Calculate upgrade value based on function and current level
            match chosen_function:
                case "increase_damage":
                    lower = max(1, int(Room.get_reached_level() / 2))
                    upper = max(2, int(Room.get_reached_level() / 2))
                    number = self.balanced_randint(lower, upper)
                case "increase_health":
                    lower = max(1, int(Room.get_reached_level() / 2))
                    upper = max(2, int(Room.get_reached_level() / 2))
                    number = self.balanced_randint(lower, upper)
                case "heal":
                    lower = max(2, int(Room.get_reached_level() / 2))
                    upper = max(4, int(Room.get_reached_level()))
                    number = self.balanced_randint(lower, upper)
                case "decrease_shoot_cooldown":
                    lower = max(1, int(Room.get_reached_level() / 2))
                    upper = lower
                    number = self.balanced_randint(lower, upper)
                case "increase_speed":
                    lower = max(1, int(Room.get_reached_level() / 2))
                    upper = max(2, int(Room.get_reached_level()))
                    number = self.balanced_randint(lower, upper)
                case "increase_bullet_speed":
                    lower = max(1, int(Room.get_reached_level() / 2))
                    upper = max(2, int(Room.get_reached_level() / 3))
                    number = self.balanced_randint(lower, upper)
            upgrade_rects.append(
                Upgrade(self.screen, i, self.player, chosen_function, number)
            )
        return upgrade_rects

    def draw_upgrade_rects(self, upgrade_rects: List[Upgrade]) -> None:
        """
        Display upgrade options on the screen with a prompt.
        Each upgrade rectangle is drawn with a slight delay.
        """
        font: pygame.font.Font = pygame.font.Font(None, 75)
        prompt: pygame.Surface = font.render("Choose upgrade", True, self.WHITE)
        prompt_rect: pygame.Rect = prompt.get_rect(center=(self.WIDTH // 2, 35))
        self.screen.blit(prompt, prompt_rect)
        pygame.display.update()

        for upgrade_rect in upgrade_rects:
            pygame.time.delay(Game.UPGRADE_DRAW_DELAY_MS)
            upgrade_rect.draw()
            pygame.display.update()

        pygame.event.clear()

    def upgrade(self) -> None:
        """
        Present upgrade options to the player and wait for the player to select one.
        """
        upgrade_rects: List[Upgrade] = self.get_upgrade_rects()
        self.draw_upgrade_rects(upgrade_rects)

        while self.can_upgrade:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    Game.end_game()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    for upgrade_rect in upgrade_rects:
                        if upgrade_rect.collidepoint(event.pos):
                            upgrade_rect.activate()
                            self.can_upgrade = False

    def run(self) -> None:
        """
        Main game loop:
        - Process events (movement, shooting)
        - Update game objects
        - Handle collisions
        - Render graphics and UI elements
        """
        running: bool = True
        while running:
            self.clock.tick(self.FPS)
            # Process user events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    Game.end_game()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == Constants.MOUSE_LEFT_BUTTON:
                        self.player.shoot(self.bullets)

            # Draw background
            self.screen.blit(
                self.background_image,
                (Constants.BACKGROUND_X_OFFSET, Constants.BACKGROUND_Y_OFFSET),
            )

            # Update game objects
            self.player.update(self.room.walls)
            self.bullets.update(self.room.walls, self.room.enemies, self.player)
            self.room.enemies.update(self.player, self.room.walls)

            # Check collision between player and enemies to apply damage
            if pygame.sprite.spritecollide(self.player, self.room.enemies, False):
                self.player.take_damage()

            # Advance level if all enemies are defeated
            if len(self.room.enemies) == 0:
                self.new_level()

            # Draw sprites and bullets
            self.all_sprites.draw(self.screen)
            self.bullets.draw(self.screen)

            # Draw health banner and hearts (full and empty)
            banner_pos: tuple = (5, 5)
            self.screen.blit(self.hp_banner, banner_pos)

            draw_position: float = 0
            for i in range(int(self.player.current_health)):
                self.screen.blit(
                    self.heart_full,
                    (
                        Constants.HEART_INITIAL_X
                        + draw_position * Game.HEART_SPACING_STEP,
                        Constants.HEART_Y,
                    ),
                )
                draw_position += Game.HEART_SPACING_FACTOR

            for i in range(int(self.player.max_health - self.player.current_health)):
                self.screen.blit(
                    self.heart_empty,
                    (
                        Constants.HEART_INITIAL_X
                        + draw_position * Game.HEART_SPACING_STEP,
                        Constants.HEART_Y,
                    ),
                )
                draw_position += Game.HEART_SPACING_FACTOR

            # If player is immune, show blinking effect
            if self.player.is_immune:
                self.player.blink()

            # End game loop if player's health drops below 1
            if self.player.current_health < 1:
                running = False

            pygame.display.flip()

        # After game loop, show death screen and option to restart
        self.start(False)


# -------------------------
# Main Entry Point
# -------------------------
if __name__ == "__main__":
    game_instance = Game()
    game_instance.start(True)
