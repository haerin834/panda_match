from django.db import models
from accounts.models import Player
import json

class Level(models.Model):
    """
    Level model storing level configurations
    """
    level_id = models.AutoField(primary_key=True)
    difficulty = models.IntegerField(default=1)
    tile_layout = models.JSONField(default=dict)  # Stores the initial board layout as JSON
    
    def __str__(self):
        return f"Level {self.level_id} (Difficulty: {self.difficulty})"

class GameSession(models.Model):
    """
    Game session model tracking player's game sessions
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('abandoned', 'Abandoned'),
    ]
    
    session_id = models.AutoField(primary_key=True)
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    level = models.ForeignKey(Level, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    score = models.IntegerField(default=0)
    buffer = models.JSONField(default=list)  # 使用JSONField存储缓冲区数据
    
    def __str__(self):
        return f"Session {self.session_id} - {self.player.user.username}"

class Tile(models.Model):
    """
    Tile model representing game board tiles
    """
    TILE_TYPES = [
        ('bamboo', 'Bamboo'),
        ('leaf', 'Leaf'),
        ('panda', 'Panda'),
        ('fish', 'Fish'),
        ('carrot', 'Carrot'),
        ('fire', 'Fire'),
    ]
    
    tile_id = models.AutoField(primary_key=True)
    game_session = models.ForeignKey(GameSession, on_delete=models.CASCADE)
    tile_type = models.CharField(max_length=20, choices=TILE_TYPES)
    position_x = models.IntegerField()
    position_y = models.IntegerField()
    position_z = models.IntegerField(default=0)  # For 3D effects or stacking
    layer = models.IntegerField(default=0)  # Higher numbers = higher layers
    
    class Meta:
        unique_together = ['game_session', 'position_x', 'position_y', 'position_z']
    
    def __str__(self):
        return f"Tile ({self.position_x},{self.position_y}) - {self.tile_type}"

class Move(models.Model):
    """
    Move model tracking player's moves during a game session
    """
    ACTION_CHOICES = [
        ('select', 'Select Tile'),
        ('match', 'Match Tiles'),
        ('use_remove_tool', 'Use Remove Tool'),
        ('use_withdraw_tool', 'Use Withdraw Tool'),
        ('use_shuffle_tool', 'Use Shuffle Tool'),
    ]
    
    move_id = models.AutoField(primary_key=True)
    game_session = models.ForeignKey(GameSession, on_delete=models.CASCADE)
    tile = models.ForeignKey(Tile, on_delete=models.CASCADE, null=True, blank=True)
    move_time = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    
    def __str__(self):
        return f"Move {self.move_id} - {self.action}"