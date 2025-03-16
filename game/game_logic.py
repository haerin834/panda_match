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
        
        # 首先从数据库加载缓冲区状态，而不是创建空数组
        self.buffer = self.game_session.buffer if hasattr(self.game_session, 'buffer') and self.game_session.buffer else []
        
        # 加载移出的方块
        self.removed_tiles = self.game_session.removed_tiles if hasattr(self.game_session, 'removed_tiles') and self.game_session.removed_tiles else []
        
        # 然后加载游戏板，这样可以排除已经在缓冲区的方块
        self.board = self.load_board()
        
    def save_buffer_state(self):
        """保存缓冲区和移出方块状态到数据库"""
        self.game_session.buffer = self.buffer
        self.game_session.removed_tiles = self.removed_tiles
        self.game_session.save(update_fields=['buffer', 'removed_tiles'])

    
    def load_board(self):
        """
        Load the current game board from the database
        """
        # 只加载不在缓冲区和移出方块中的方块
        buffer_tile_ids = [tile['id'] for tile in self.buffer] if self.buffer else []
        removed_tile_ids = [tile['id'] for tile in self.removed_tiles] if self.removed_tiles else []
        excluded_tile_ids = buffer_tile_ids + removed_tile_ids
        
        tiles = Tile.objects.filter(game_session=self.game_session).exclude(tile_id__in=excluded_tile_ids)
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
        
        return board
    
    def initialize_board(self, rows=5, cols=5, layers=None):
        """
        Create a new game board with stacked tiles
        """
        # Clear any existing tiles
        Tile.objects.filter(game_session=self.game_session).delete()
        
        # 根据关卡难度确定层数
        if layers is None:
            # 基础层数为3，每增加一个难度级别，增加1层
            layers = 3 + (self.level.difficulty - 1)
            # 确保最少有3层，最多有8层
            layers = max(3, min(8, layers))
        
        # Generate new tiles with proper distribution
        board = {}
        tile_types = self.TILE_TYPES
        
        # 检查关卡是否有预定义的布局
        print(f"关卡ID: {self.level.level_id}, 难度: {self.level.difficulty}")
        print(f"关卡是否有tile_layout属性: {hasattr(self.level, 'tile_layout')}")
        print(f"关卡tile_layout是否有值: {bool(self.level.tile_layout) if hasattr(self.level, 'tile_layout') else False}")
        
        if hasattr(self.level, 'tile_layout') and self.level.tile_layout:
            # 使用预定义的布局
            print(f"使用预定义的布局，共 {len(self.level.tile_layout)} 个方块")
            
            # 统计每种类型的方块数量
            type_counts = {}
            for tile_info in self.level.tile_layout:
                tile_type = tile_info['type']
                type_counts[tile_type] = type_counts.get(tile_type, 0) + 1
            
            print("预定义布局中各类型方块数量:")
            for tile_type, count in type_counts.items():
                print(f"  {tile_type}: {count} 个 ({count % 3 == 0 and '是' or '不是'}3的倍数)")
            
            # 创建方块并添加到游戏板
            for tile_info in self.level.tile_layout:
                x = tile_info['x']
                y = tile_info['y']
                z = tile_info.get('z', 0)
                layer = tile_info.get('layer', 0)
                tile_type = tile_info['type']
                
                # 在数据库中创建方块
                tile = Tile.objects.create(
                    game_session=self.game_session,
                    tile_type=tile_type,
                    position_x=x,
                    position_y=y,
                    position_z=z,
                    layer=layer
                )
                
                # 添加到本地游戏板
                key = f"{x},{y},{layer}"
                board[key] = {
                    'id': tile.tile_id,
                    'type': tile_type,
                    'x': x,
                    'y': y,
                    'z': z,
                    'layer': layer
                }
            
            self.board = board
            self.buffer = []
            self.removed_tiles = []
            return board
        
        # 如果没有预定义布局，则生成随机布局
        print("没有预定义布局，生成随机布局")
        
        # 创建一个二维网格来跟踪每个位置的堆叠高度
        stack_heights = [[0 for _ in range(cols)] for _ in range(rows)]
        
        # 计算可用的位置总数和位置
        available_positions = []
        
        # 首先确定每个位置的堆叠高度
        for y in range(rows):
            for x in range(cols):
                # 根据关卡难度随机确定这个位置的堆叠高度
                # 难度越高，堆叠越高
                max_stack = random.randint(1, layers)
                stack_heights[y][x] = max_stack
                
                # 为每个堆叠位置创建方块
                for layer in range(max_stack):
                    # 确保每个位置的z轴值不同，以满足唯一约束
                    z_pos = layer
                    available_positions.append((x, y, layer, z_pos))
        
        # 完全重写方块分配逻辑，确保每种类型的方块数量都是3的倍数
        
        # 首先计算总位置数
        total_positions = len(available_positions)
        print(f"初始总位置数: {total_positions}")
        
        # 确保总位置数是3的倍数
        if total_positions % 3 != 0:
            # 截断到最近的3的倍数
            needed_positions = (total_positions // 3) * 3
            available_positions = available_positions[:needed_positions]
            total_positions = needed_positions
            print(f"调整后的位置数: {total_positions}")
        
        # 计算每种类型的方块应该有多少个
        # 确保每种类型的方块数量都是3的倍数
        tile_types_count = len(tile_types)
        
        # 初始化每种类型的方块数量为0
        tiles_distribution = {tile_type: 0 for tile_type in tile_types}
        
        # 计算每种类型至少应该有多少个方块（确保是3的倍数）
        base_count_per_type = (total_positions // tile_types_count) // 3 * 3
        remaining_positions = total_positions - (base_count_per_type * tile_types_count)
        
        print(f"每种类型基础方块数: {base_count_per_type}")
        print(f"剩余位置数: {remaining_positions}")
        
        # 为每种类型分配基础数量的方块
        for tile_type in tile_types:
            tiles_distribution[tile_type] = base_count_per_type
        
        # 分配剩余的位置（确保每次分配3个，保持3的倍数）
        remaining_types = list(tile_types)
        while remaining_positions >= 3:
            # 随机选择一种类型
            if not remaining_types:
                remaining_types = list(tile_types)
            tile_type = random.choice(remaining_types)
            remaining_types.remove(tile_type)
            
            # 为这种类型增加3个方块
            tiles_distribution[tile_type] += 3
            remaining_positions -= 3
        
        # 验证分配是否正确
        total_tiles = sum(tiles_distribution.values())
        print(f"总方块数: {total_tiles}, 需要的位置数: {total_positions}")
        
        if total_tiles != total_positions:
            raise ValueError(f"分配错误: 总方块数 {total_tiles} 不等于需要的位置数 {total_positions}")
        
        # 验证每种类型的方块数量是否是3的倍数
        for tile_type, count in tiles_distribution.items():
            if count % 3 != 0:
                raise ValueError(f"分配错误: 类型 {tile_type} 的方块数 {count} 不是3的倍数")
            print(f"验证通过: 类型 {tile_type} 的方块数 {count} 是3的倍数")
        
        # 创建所有方块类型的列表
        all_tiles = []
        for tile_type, count in tiles_distribution.items():
            all_tiles.extend([tile_type] * count)
        
        # 打乱方块类型
        random.shuffle(all_tiles)
        
        # 放置方块到游戏板上
        for i, (x, y, layer, z_pos) in enumerate(available_positions):
            if i >= len(all_tiles):
                break
                
            tile_type = all_tiles[i]
            
            # 在数据库中创建方块
            tile = Tile.objects.create(
                game_session=self.game_session,
                tile_type=tile_type,
                position_x=x,
                position_y=y,
                position_z=z_pos,
                layer=layer
            )
            
            # 添加到本地游戏板
            key = f"{x},{y},{layer}"
            board[key] = {
                'id': tile.tile_id,
                'type': tile_type,
                'x': x,
                'y': y,
                'z': z_pos,
                'layer': layer
            }
        
        self.board = board
        self.buffer = []
        self.removed_tiles = []
        return board

    def is_tile_accessible(self, x, y, layer):
        """
        Check if a tile is accessible (only first and second layer are accessible and not covered)
        """
        # 只有第一层和第二层的方块可以被访问
        if layer > 2:  # 修改为允许第三层(layer=2)的方块也可以被访问
            print(f"方块({x},{y},{layer})不可访问: 层级 > 2")
            return False
            
        # 检查是否有更高层级的瓦片覆盖这个位置
        # 检查所有更高层的方块
        for l in range(layer + 1, 10):  # 假设最多10层
            # 检查更高层级中是否有覆盖这个位置的瓦片
            # 一个瓦片被覆盖，如果有一个更高层级的瓦片在相同的位置
            # 或者在可能重叠这个瓦片的任意四个角落位置
            for dx, dy in [(0, 0), (-1, 0), (0, -1), (-1, -1)]:
                check_key = f"{x+dx},{y+dy},{l}"
                if check_key in self.board:
                    covering_tile = self.board[check_key]
                    print(f"方块({x},{y},{layer})被方块({covering_tile['x']},{covering_tile['y']},{covering_tile['layer']})覆盖")
                    return False
        
        # 如果是新变得可访问的方块，打印信息
        key = f"{x},{y},{layer}"
        if key in self.board:
            print(f"方块({x},{y},{layer})可访问")
        
        return True
    
    def get_tile(self, x, y, layer):
        """
        Get tile at position (x, y, layer)
        """
        key = f"{x},{y},{layer}"
        return self.board.get(key)
    

    def select_tile(self, tile_id):
        """选择一个方块并将其移动到缓冲区"""
        # 查找方块
        try:
            tile = Tile.objects.get(tile_id=tile_id, game_session=self.game_session)
            print(f"选中方块: ID={tile.tile_id}, 位置=({tile.position_x},{tile.position_y},{tile.layer}), 类型={tile.tile_type}")
        except Tile.DoesNotExist:
            print(f"找不到方块: ID={tile_id}")
            return False
        
        # 检查方块是否可访问
        if not self.is_tile_accessible(tile.position_x, tile.position_y, tile.layer):
            print(f"方块不可访问: ID={tile.tile_id}, 位置=({tile.position_x},{tile.position_y},{tile.layer})")
            return False
        
        # 检查缓冲区是否已满(7个格子)
        if len(self.buffer) >= 7:
            print("缓冲区已满，无法添加更多方块")
            return False
        
        # 添加到缓冲区
        tile_data = {
            'id': tile.tile_id,
            'type': tile.tile_type,
            'x': tile.position_x,
            'y': tile.position_y,
            'layer': tile.layer
        }
        self.buffer.append(tile_data)
        print(f"方块已添加到缓冲区: ID={tile.tile_id}, 位置=({tile.position_x},{tile.position_y},{tile.layer})")
        
        # 从方块区移除
        key = f"{tile.position_x},{tile.position_y},{tile.layer}"
        if key in self.board:
            del self.board[key]
            print(f"方块已从游戏板移除: 位置=({tile.position_x},{tile.position_y},{tile.layer})")
        
        # 记录移动
        Move.objects.create(
            game_session=self.game_session,
            tile=tile,
            action='select'
        )
        
        # 检查是否有匹配
        self.check_buffer_matches()
        
        # 保存缓冲区状态到数据库
        self.save_buffer_state()
        
        # 检查是否有新的可访问方块
        print("检查是否有新的可访问方块:")
        for board_key, board_tile in self.board.items():
            x, y, layer = map(int, board_key.split(','))
            if self.is_tile_accessible(x, y, layer):
                print(f"方块现在可访问: ID={board_tile['id']}, 位置=({x},{y},{layer}), 类型={board_tile['type']}")
        
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
        removed = self.buffer[:3]
        self.buffer = self.buffer[3:]
        
        # 将移除的方块添加到removed_tiles列表
        self.removed_tiles.extend(removed)
        
        # 保存缓冲区状态到数据库
        self.save_buffer_state()
        
        # Record action
        Move.objects.create(
            game_session=self.game_session,
            action='use_remove_tool'
        )
        
        return True
    
    def return_removed_tile(self, tile_id):
        """
        将移出的方块返回到栅栏
        """
        # 检查栅栏是否已满(7个格子)
        if len(self.buffer) >= 7:
            return False
        
        # 查找要返回的方块
        target_tile = None
        target_index = -1
        
        for i, tile in enumerate(self.removed_tiles):
            if tile['id'] == tile_id:
                target_tile = tile
                target_index = i
                break
        
        if target_tile is None:
            return False
            
        # 从移出区移除
        removed_tile = self.removed_tiles.pop(target_index)
        
        # 添加到栅栏
        self.buffer.append(removed_tile)
        
        # 保存缓冲区状态到数据库
        self.save_buffer_state()
        
        # 记录移动
        try:
            db_tile = Tile.objects.get(tile_id=tile_id)
            Move.objects.create(
                game_session=self.game_session,
                tile=db_tile,
                action='return_removed_tile'
            )
        except Tile.DoesNotExist:
            pass
        
        # 检查是否有匹配
        self.check_buffer_matches()
        
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
            key = f"{last_tile['x']},{last_tile['y']},{last_tile['layer']}"
            self.board[key] = {
                'id': tile.tile_id,
                'type': tile.tile_type,
                'x': last_tile['x'],
                'y': last_tile['y'],
                'z': tile.position_z,
                'layer': last_tile['layer']
            }
            
            # Record action
            Move.objects.create(
                game_session=self.game_session,
                tile=tile,
                action='use_withdraw_tool'
            )
            
            # 保存缓冲区状态到数据库
            self.save_buffer_state()
            
            return True
        except Tile.DoesNotExist:
            return False
    
    def use_shuffle_tool(self):
        """
        Use the shuffle tool to randomize all remaining tiles on the board
        """
        # Get all tiles in the board
        tiles = list(self.board.values())
        
        if not tiles:
            return False
        
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
        # 如果还有移出的方块，游戏未结束
        if self.removed_tiles:
            return False
            
        # 如果还有方块在游戏板上，游戏未结束
        if self.board:
            return False
        
        # 如果缓冲区为空，游戏结束
        if not self.buffer:
            return True
            
        # 检查缓冲区中是否有可能的匹配
        # 如果缓冲区中有3个或更多相同类型的方块，游戏未结束
        type_counts = {}
        for tile in self.buffer:
            type_counts[tile['type']] = type_counts.get(tile['type'], 0) + 1
        
        print(f"缓冲区中的方块类型分布: {type_counts}")
        
        # 检查是否有任何类型的方块数量不是3的倍数
        for tile_type, count in type_counts.items():
            if count % 3 != 0:
                print(f"警告: 缓冲区中类型 {tile_type} 的方块数 {count} 不是3的倍数")
                # 如果有任何类型的方块数量不是3的倍数，游戏可能无法完成
                # 但我们不在这里结束游戏，因为玩家可能还有道具可以使用
        
        # 如果有任何类型的方块数量大于等于3，游戏未结束
        if any(count >= 3 for count in type_counts.values()):
            return False
            
        # 如果缓冲区已满且没有可能的匹配，游戏卡住了
        if len(self.buffer) == 7:
            return True
            
        # 其他情况，游戏未结束
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
