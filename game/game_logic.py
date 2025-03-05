import random
import json
from .models import GameSession, Tile, Move, Level

class GameBoard:
    """
    Class to manage the game board and game logic
    """
    TILE_TYPES = ['bamboo', 'leaf', 'panda', 'fish', 'carrot', 'fire']
    
    def __init__(self, game_session):
        self.game_session = game_session
        self.level = game_session.level
        self.board = self.load_board()
        
        # 从数据库加载缓冲区状态，而不是创建空数组
        self.buffer = self.game_session.buffer if hasattr(self.game_session, 'buffer') and self.game_session.buffer else []
        self.removed_tiles = []
        
    def save_buffer_state(self):
        """保存缓冲区状态到数据库"""
        self.game_session.buffer = self.buffer
        self.game_session.save(update_fields=['buffer'])

    
    def load_board(self):
        """
        Load the current game board from the database
        """
        tiles = Tile.objects.filter(game_session=self.game_session)
        board = {}
        
        for tile in tiles:
            key = f"{tile.position_x},{tile.position_y},{tile.layer}"
            board[key] = {
                'id': tile.tile_id,
                'type': tile.tile_type,
                'x': tile.position_x,
                'y': tile.position_y,
                'z': tile.position_z,
                'layer': tile.layer
            }
        
        # DON'T reset the buffer here - commented out if this line exists
        # self.buffer = []
        
        return board
    
    def initialize_board(self, rows=5, cols=5, layers=3):
        """
        Create a new game board with stacked tiles
        """
        # Clear any existing tiles
        Tile.objects.filter(game_session=self.game_session).delete()
        
        # Generate new tiles with proper distribution
        # (ensuring we have multiples of 3 for each type)
        board = {}
        tile_types = self.TILE_TYPES
        
        # Calculate total tiles needed
        total_positions = rows * cols * layers
        tiles_per_type = total_positions // len(tile_types)
        
        # Create a list of all tile types (ensuring multiples of 3)
        all_tiles = []
        for tile_type in tile_types:
            # Add tiles in multiples of 3
            count = tiles_per_type
            if count % 3 != 0:
                count += (3 - (count % 3))  # Round up to multiple of 3
            all_tiles.extend([tile_type] * count)
        
        # Shuffle the tile types
        random.shuffle(all_tiles)
        
        # Place tiles on the board
        tile_index = 0
        used_positions = set()  # Keep track of positions already used
        
        for layer in range(layers):
            for y in range(rows):
                for x in range(cols):
                    # Skip some positions in higher layers (more gaps in higher layers)
                    if layer > 0 and random.random() < (0.2 * layer):
                        continue
                    
                    # Skip if we've run out of tiles
                    if tile_index >= len(all_tiles):
                        break
                    
                    # Create a unique position identifier
                    position_key = f"{x},{y},{0}"  # We're using position_z=0 for all
                    
                    # Skip if this position is already used
                    if position_key in used_positions:
                        continue
                    
                    used_positions.add(position_key)
                    
                    tile_type = all_tiles[tile_index]
                    tile_index += 1
                    
                    # Create tile in database
                    tile = Tile.objects.create(
                        game_session=self.game_session,
                        tile_type=tile_type,
                        position_x=x,
                        position_y=y,
                        position_z=0,
                        layer=layer
                    )
                    
                    # Add to local board
                    key = f"{x},{y},{layer}"
                    board[key] = {
                        'id': tile.tile_id,
                        'type': tile_type,
                        'x': x,
                        'y': y,
                        'z': 0,
                        'layer': layer
                    }
        
        self.board = board
        self.buffer = []
        self.removed_tiles = []
        return board

    def is_tile_accessible(self, x, y, layer):
        """
        Check if a tile is accessible (not covered by higher layers than layer+2)
        """
        # 检查是否有更高层级的瓦片覆盖这个位置
        # 只检查比当前层+2更高的层，允许两层都可见
        for l in range(layer + 2, 10):  # 假设最多10层
            # 检查更高层级中是否有覆盖这个位置的瓦片
            # 一个瓦片被覆盖，如果有一个更高层级的瓦片在相同的位置
            # 或者在可能重叠这个瓦片的任意四个角落位置
            for dx, dy in [(0, 0), (-1, 0), (0, -1), (-1, -1)]:
                check_key = f"{x+dx},{y+dy},{l}"
                if check_key in self.board:
                    return False
        
        return True
    
    def get_tile(self, x, y, layer):
        """
        Get tile at position (x, y, layer)
        """
        key = f"{x},{y},{layer}"
        return self.board.get(key)
    
    def save_buffer_state(self):
        """保存缓冲区状态到数据库"""
        self.game_session.buffer = self.buffer
        self.game_session.save(update_fields=['buffer'])

    def select_tile(self, tile_id):
        """选择一个方块并将其移动到缓冲区"""
        # 查找方块
        try:
            tile = Tile.objects.get(tile_id=tile_id, game_session=self.game_session)
        except Tile.DoesNotExist:
            return False
        
        # 检查方块是否可访问
        if not self.is_tile_accessible(tile.position_x, tile.position_y, tile.layer):
            return False
        
        # 检查缓冲区是否已满(7个格子)
        if len(self.buffer) >= 7:
            return False
        
        # 添加到缓冲区
        tile_data = {
            'id': tile.tile_id,
            'type': tile.tile_type
        }
        self.buffer.append(tile_data)
        
        print("Buffer after adding tile:", self.buffer)
        
        # 从方块区移除
        key = f"{tile.position_x},{tile.position_y},{tile.layer}"
        if key in self.board:
            del self.board[key]
        
        # 记录移动
        Move.objects.create(
            game_session=self.game_session,
            tile=tile,
            action='select'
        )
        
        # 检查是否有匹配
        self.check_buffer_matches()
        
        # 重要：保存缓冲区状态到数据库
        self.save_buffer_state()
        
        return True

    def check_buffer_matches(self):
        """
        Check for matches in the buffer (3 adjacent same-type tiles)
        """
        
        print("Checking buffer matches. Current buffer:", self.buffer)
        
        i = 0
        while i <= len(self.buffer) - 3:
            if (self.buffer[i]['type'] == self.buffer[i+1]['type'] == self.buffer[i+2]['type']):
                # Found a match
                matched_tiles = self.buffer[i:i+3]
                
                # Remove matched tiles from buffer
                self.buffer = self.buffer[:i] + self.buffer[i+3:]
                
                # Record match move
                Move.objects.create(
                    game_session=self.game_session,
                    action='match'
                )
                
                # Update score
                self.game_session.score += 10
                self.game_session.save()
                
                # Delete tiles from database
                for matched in matched_tiles:
                    Tile.objects.filter(tile_id=matched['id']).delete()
                
                # Continue checking from the beginning
                i = 0
            else:
                i += 1
    
    def use_remove_tool(self):
        """
        Use the remove tool to take out the first three tiles from buffer
        """
        if len(self.buffer) < 3:
            return False
        
        # Remove first three tiles from buffer
        self.removed_tiles = self.buffer[:3]
        self.buffer = self.buffer[3:]
        
        # Record action
        Move.objects.create(
            game_session=self.game_session,
            action='use_remove_tool'
        )
        
        return True
    
    def use_withdraw_tool(self):
        """
        Use the withdraw tool to return the most recent tile to its original position
        """
        if not self.buffer:
            return False
        
        # Get the last tile from buffer
        last_tile = self.buffer.pop()
        
        # Find the tile in database
        try:
            tile = Tile.objects.get(tile_id=last_tile['id'])
            
            # Return to board
            key = f"{tile.position_x},{tile.position_y},{tile.layer}"
            self.board[key] = {
                'id': tile.tile_id,
                'type': tile.tile_type,
                'x': tile.position_x,
                'y': tile.position_y,
                'z': tile.position_z,
                'layer': tile.layer
            }
            
            # Record action
            Move.objects.create(
                game_session=self.game_session,
                tile=tile,
                action='use_withdraw_tool'
            )
            
            return True
        except Tile.DoesNotExist:
            return False
    
    def use_shuffle_tool(self):
        """
        Use the shuffle tool to randomize all remaining tiles on the board
        """
        # Get all tiles in the board
        tiles = list(self.board.values())
        
        # Shuffle the tile types
        tile_types = [tile['type'] for tile in tiles]
        random.shuffle(tile_types)
        
        # Update tiles with new types
        for i, tile in enumerate(tiles):
            db_tile = Tile.objects.get(tile_id=tile['id'])
            db_tile.tile_type = tile_types[i]
            db_tile.save()
            
            # Update local board
            key = f"{tile['x']},{tile['y']},{tile['layer']}"
            self.board[key]['type'] = tile_types[i]
        
        # Record action
        Move.objects.create(
            game_session=self.game_session,
            action='use_shuffle_tool'
        )
        
        return True
    
    def is_game_over(self):
        """
        Check if the game is over (board is empty or no more possible matches)
        """
        # If there are no more tiles on the board, game is over
        if not self.board:
            return True
        
        # Get all accessible tiles
        accessible_tiles = []
        for key, tile in self.board.items():
            x, y, layer = map(int, key.split(','))
            if self.is_tile_accessible(x, y, layer):
                accessible_tiles.append(tile)
        
        # If no accessible tiles and buffer is full, game might be stuck
        if not accessible_tiles and len(self.buffer) == 7:
            # Check if there are 3 of the same type in the buffer
            type_counts = {}
            for tile in self.buffer:
                type_counts[tile['type']] = type_counts.get(tile['type'], 0) + 1
            
            # If no type has at least 3 tiles, game is stuck
            if not any(count >= 3 for count in type_counts.values()):
                return True
        
        # Still have accessible tiles, game is not over
        return False
    
    def complete_level(self):
        """
        Mark level as completed
        """
        self.game_session.status = 'completed'
        self.game_session.save()
        
        # Update player's level progress if needed
        player = self.game_session.player
        if player.level_progress <= self.level.level_id:
            player.level_progress = self.level.level_id + 1
            player.save()
        
        return True