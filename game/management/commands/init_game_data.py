import json
import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import Player
from game.models import Level
from leaderboard.models import Leaderboard
from django.utils import timezone

class Command(BaseCommand):
    help = 'Initialize the game with sample data'

    def handle(self, *args, **options):
        self.stdout.write('Initializing game data...')
        
        # Create levels
        self.create_levels()
        
        # Create sample admin user if it doesn't exist
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='adminpassword'
            )
            Player.objects.create(user=admin_user, score=0, level_progress=1)
            self.stdout.write(self.style.SUCCESS(f'Created admin user: {admin_user.username}'))
        
        self.stdout.write(self.style.SUCCESS('Game data initialized successfully!'))
    
    def create_levels(self):
        """Create game levels"""
        # Check if levels already exist
        if Level.objects.exists():
            self.stdout.write('Levels already exist, skipping...')
            return
        
        # Create 10 levels with increasing difficulty
        for i in range(1, 11):
            # Generate a tile layout based on level difficulty
            tile_layout = self.generate_tile_layout(i)
            
            Level.objects.create(
                level_id=i,
                difficulty=min(5, (i + 1) // 2),  # Difficulty from 1-5
                tile_layout=tile_layout
            )
            
            self.stdout.write(f'Created Level {i}')
    
    def generate_tile_layout(self, level):
        """Generate a tile layout for a level"""
        # Define board size based on level
        rows = min(8, 4 + level // 2)
        cols = min(8, 4 + level // 2)
        
        # Available tile types
        tile_types = ['bamboo', 'leaf', 'panda', 'fish', 'carrot', 'fire']
        
        # Generate layout
        layout = []
        for y in range(rows):
            for x in range(cols):
                # Ensure we have at least 3 of each type for matching
                layout.append({
                    'x': x,
                    'y': y,
                    'type': random.choice(tile_types)
                })
        
        # Ensure there are at least 3 of each tile type
        tile_counts = {tile_type: 0 for tile_type in tile_types}
        for tile in layout:
            tile_counts[tile['type']] += 1
        
        # Replace tiles if needed to ensure minimum counts
        for tile_type, count in tile_counts.items():
            if count < 3:
                # Find random tiles to replace
                replacements_needed = 3 - count
                for _ in range(replacements_needed):
                    # Find a tile type with extra tiles
                    extra_types = [t for t, c in tile_counts.items() if c > 3]
                    if not extra_types:
                        break
                    
                    replace_type = random.choice(extra_types)
                    
                    # Find a tile of that type to replace
                    for tile in layout:
                        if tile['type'] == replace_type:
                            tile['type'] = tile_type
                            tile_counts[replace_type] -= 1
                            tile_counts[tile_type] += 1
                            break
        
        return layout