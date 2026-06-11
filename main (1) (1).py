"""
五子棋A*智能对弈系统 - 步时限时（每步30秒）
支持人机对弈和人人对弈，超时自动判负
"""
import tkinter as tk
from tkinter import messagebox
import time
import heapq
import threading


# ==================== 棋盘管理模块 ====================
class GobangBoard:
    """15x15五子棋棋盘管理"""
    
    def __init__(self, size=15):
        self.size = size
        self.board = [[0 for _ in range(size)] for _ in range(size)]
        self.move_history = []
        self.last_move = None
        self.winner = None
        
    def reset(self):
        """重置棋盘"""
        self.board = [[0 for _ in range(self.size)] for _ in range(self.size)]
        self.move_history = []
        self.last_move = None
        self.winner = None
        
    def is_valid_move(self, x, y):
        """检查落子是否合法"""
        if not (0 <= x < self.size and 0 <= y < self.size):
            return False
        if self.board[x][y] != 0:
            return False
        if self.winner is not None:
            return False
        return True
    
    def place_piece(self, x, y, player):
        """落子"""
        if not self.is_valid_move(x, y):
            return False
        
        self.board[x][y] = player
        self.move_history.append((x, y, player))
        self.last_move = (x, y)
        
        if self.check_win(x, y, player):
            self.winner = player
            
        return True
    
    def check_win(self, x, y, player):
        """检查是否胜利"""
        directions = [(1, 0), (0, 1), (1, 1), (1, -1)]
        
        for dx, dy in directions:
            count = 1
            
            # 正方向
            step = 1
            while True:
                nx, ny = x + dx * step, y + dy * step
                if not (0 <= nx < self.size and 0 <= ny < self.size):
                    break
                if self.board[nx][ny] == player:
                    count += 1
                    step += 1
                else:
                    break
            
            # 反方向
            step = 1
            while True:
                nx, ny = x - dx * step, y - dy * step
                if not (0 <= nx < self.size and 0 <= ny < self.size):
                    break
                if self.board[nx][ny] == player:
                    count += 1
                    step += 1
                else:
                    break
            
            if count >= 5:
                return True
        
        return False
    
    def is_full(self):
        """检查棋盘是否已满（平局）"""
        for i in range(self.size):
            for j in range(self.size):
                if self.board[i][j] == 0:
                    return False
        return True
    
    def get_empty_positions(self):
        """获取所有空位"""
        empty = []
        for i in range(self.size):
            for j in range(self.size):
                if self.board[i][j] == 0:
                    empty.append((i, j))
        return empty
    
    def get_valid_moves_within_distance(self, distance=2):
        """获取已有棋子周围distance范围内的空位"""
        if not self.move_history:
            center = self.size // 2
            positions = []
            for i in range(center - distance, center + distance + 1):
                for j in range(center - distance, center + distance + 1):
                    if 0 <= i < self.size and 0 <= j < self.size and self.board[i][j] == 0:
                        positions.append((i, j))
            return positions
        
        occupied = [(i, j) for i in range(self.size) for j in range(self.size) if self.board[i][j] != 0]
        
        candidates = set()
        for x, y in occupied:
            for dx in range(-distance, distance + 1):
                for dy in range(-distance, distance + 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.size and 0 <= ny < self.size and self.board[nx][ny] == 0:
                        candidates.add((nx, ny))
        
        if not candidates:
            return self.get_empty_positions()
        
        return list(candidates)


# ==================== 棋局评估模块 ====================
class Evaluator:
    """棋局评估器"""
    
    PATTERNS = {
        'FIVE': 100000000,
        'ALIVE_FOUR': 100000,
        'SLEEP_FOUR': 10000,
        'ALIVE_THREE': 5000,
        'SLEEP_THREE': 800,
        'ALIVE_TWO': 200,
        'SLEEP_TWO': 50,
        'ALIVE_ONE': 10,
        'SLEEP_ONE': 2,
    }
    
    DIRECTIONS = [(1, 0), (0, 1), (1, 1), (1, -1)]
    
    def __init__(self, board_size=15):
        self.board_size = board_size
        
    def evaluate_position(self, board, x, y, player, difficulty='hard'):
        """评估在(x,y)位置落子的总分数"""
        if board[x][y] != 0:
            return 0
            
        attack_score = self.evaluate_move(board, x, y, player)
        opponent = 3 - player
        defense_score = self.evaluate_move(board, x, y, opponent)
        
        total_moves = sum(cell != 0 for row in board for cell in row)
        
        if difficulty == 'easy':
            return attack_score * 0.8 + defense_score * 0.2
        elif difficulty == 'hard':
            if total_moves < 80:
                return attack_score * 0.6 + defense_score * 0.4
            else:
                return attack_score * 0.4 + defense_score * 0.6
        else:
            if total_moves < 100:
                return attack_score * 0.7 + defense_score * 0.3
            else:
                return attack_score * 0.3 + defense_score * 0.7
    
    def evaluate_move(self, board, x, y, player):
        """评估在指定位置落子对特定玩家产生的分数"""
        board[x][y] = player
        total_score = 0
        for dx, dy in self.DIRECTIONS:
            total_score += self._evaluate_direction(board, x, y, dx, dy, player)
        board[x][y] = 0
        return total_score
    
    def _evaluate_direction(self, board, x, y, dx, dy, player):
        """评估某一方向上的棋型分数"""
        count = 1
        left_empty = 0
        right_empty = 0
        left_blocked = False
        right_blocked = False
        
        # 正向统计
        step = 1
        while True:
            nx, ny = x + dx * step, y + dy * step
            if not (0 <= nx < self.board_size and 0 <= ny < self.board_size):
                right_blocked = True
                break
            if board[nx][ny] == player:
                count += 1
                step += 1
            else:
                if board[nx][ny] == 0:
                    right_empty += 1
                else:
                    right_blocked = True
                break
        
        # 反向统计
        step = 1
        while True:
            nx, ny = x - dx * step, y - dy * step
            if not (0 <= nx < self.board_size and 0 <= ny < self.board_size):
                left_blocked = True
                break
            if board[nx][ny] == player:
                count += 1
                step += 1
            else:
                if board[nx][ny] == 0:
                    left_empty += 1
                else:
                    left_blocked = True
                break
        
        if count >= 5:
            return self.PATTERNS['FIVE']
        
        if count == 4 and not left_blocked and not right_blocked:
            return self.PATTERNS['ALIVE_FOUR']
        if count == 4 and (left_blocked or right_blocked):
            return self.PATTERNS['SLEEP_FOUR']
        if count == 3 and not left_blocked and not right_blocked:
            return self.PATTERNS['ALIVE_THREE']
        if count == 3:
            return self.PATTERNS['SLEEP_THREE']
        if count == 2 and not left_blocked and not right_blocked:
            return self.PATTERNS['ALIVE_TWO']
        if count == 2:
            return self.PATTERNS['SLEEP_TWO']
        if count == 1 and not left_blocked and not right_blocked:
            return self.PATTERNS['ALIVE_ONE']
        
        return 0


# ==================== A*算法AI模块 ====================
class AStarNode:
    """A*算法节点"""
    
    def __init__(self, x, y, g, h, parent=None):
        self.x = x
        self.y = y
        self.g = g
        self.h = h
        self.parent = parent
        self.f = g + h
    
    def __lt__(self, other):
        return self.f < other.f


class AIPlayer:
    """基于A*算法的五子棋AI"""
    
    def __init__(self, board, evaluator, player=1, difficulty='hard'):
        self.board = board
        self.evaluator = evaluator
        self.player = player
        self.difficulty = difficulty
        self.name = "黑棋(AI)" if player == 1 else "白棋(AI)"
        self._set_difficulty_params()
        
    def _set_difficulty_params(self):
        """根据难度设置AI参数"""
        if self.difficulty == 'easy':
            self.search_distance = 1
            self.max_nodes = 500
            self.max_time = 1.0
            self.refine_depth = 1
        elif self.difficulty == 'medium':
            self.search_distance = 2
            self.max_nodes = 1500
            self.max_time = 2.0
            self.refine_depth = 2
        else:
            self.search_distance = 3
            self.max_nodes = 5000
            self.max_time = 5.0
            self.refine_depth = 3
        
    def set_difficulty(self, difficulty):
        self.difficulty = difficulty
        self._set_difficulty_params()
        
    def get_best_move(self):
        start_time = time.time()
        candidates = self.board.get_valid_moves_within_distance(distance=self.search_distance)
        
        if not candidates:
            return None
            
        open_list = []
        
        for x, y in candidates:
            if time.time() - start_time > self.max_time:
                break
            g = self._calculate_g_cost(x, y)
            h = self._calculate_h_cost(x, y)
            node = AStarNode(x, y, g, h)
            heapq.heappush(open_list, node)
        
        if open_list:
            nodes_to_expand = min(self.max_nodes, len(open_list))
            best_nodes = heapq.nsmallest(min(5, nodes_to_expand), open_list)
            
            best_score = -1
            best_pos = None
            
            for node in best_nodes:
                score = self.evaluator.evaluate_position(
                    self.board.board, node.x, node.y, self.player, self.difficulty
                )
                if score > best_score:
                    best_score = score
                    best_pos = (node.x, node.y)
            
            if best_pos:
                refined_best = self._refine_best_move(best_pos[0], best_pos[1], start_time)
                if refined_best:
                    return refined_best
                return best_pos
        
        return self._greedy_best_move()
    
    def _calculate_g_cost(self, x, y):
        total_moves = len(self.board.move_history)
        step_cost = total_moves / 200.0
        
        center = self.board.size // 2
        dist_to_center = abs(x - center) + abs(y - center)
        center_cost = dist_to_center / (self.board.size * 2)
        
        min_dist_to_piece = self._min_distance_to_pieces(x, y)
        distance_cost = min(1.0, min_dist_to_piece / 10.0)
        
        if self.difficulty == 'hard':
            g = step_cost * 0.2 + center_cost * 0.4 + distance_cost * 0.4
        elif self.difficulty == 'easy':
            g = step_cost * 0.4 + center_cost * 0.2 + distance_cost * 0.4
        else:
            g = step_cost * 0.3 + center_cost * 0.3 + distance_cost * 0.4
        
        return g
    
    def _min_distance_to_pieces(self, x, y):
        min_dist = float('inf')
        for i in range(self.board.size):
            for j in range(self.board.size):
                if self.board.board[i][j] != 0:
                    dist = abs(x - i) + abs(y - j)
                    if dist < min_dist:
                        min_dist = dist
        return min_dist if min_dist != float('inf') else 0
    
    def _calculate_h_cost(self, x, y):
        score = self.evaluator.evaluate_position(
            self.board.board, x, y, self.player, self.difficulty
        )
        
        center = self.board.size // 2
        center_bonus = 1.0 - (abs(x - center) + abs(y - center)) / (self.board.size * 2)
        center_bonus = max(0, center_bonus) * 100
        
        if self.difficulty == 'hard':
            center_bonus *= 1.5
        
        total_score = score + center_bonus
        max_score = 100000000
        h = max(0, 1.0 - (total_score / max_score))
        
        return h
    
    def _refine_best_move(self, x, y, start_time):
        best_score = -1
        best_pos = None
        search_range = self.refine_depth
        
        for dx in range(-search_range, search_range + 1):
            for dy in range(-search_range, search_range + 1):
                if time.time() - start_time > self.max_time:
                    break
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.board.size and 0 <= ny < self.board.size:
                    if self.board.board[nx][ny] == 0:
                        score = self.evaluator.evaluate_position(
                            self.board.board, nx, ny, self.player, self.difficulty
                        )
                        if score > best_score:
                            best_score = score
                            best_pos = (nx, ny)
        
        return best_pos
    
    def _greedy_best_move(self):
        candidates = self.board.get_valid_moves_within_distance(distance=self.search_distance)
        best_score = -1
        best_pos = None
        
        for x, y in candidates:
            score = self.evaluator.evaluate_position(
                self.board.board, x, y, self.player, self.difficulty
            )
            if score > best_score:
                best_score = score
                best_pos = (x, y)
        
        if best_pos is None and candidates:
            best_pos = candidates[0]
        return best_pos


# ==================== GUI界面模块 ====================
class GobangGUI:
    """五子棋游戏GUI - 步时限时（每步单独计时）"""
    
    def __init__(self, board, ai_player=None):
        self.board = board
        self.ai_player = ai_player
        self.current_player = 1
        self.game_mode = "human_vs_ai"
        self.ai_first = True
        
        # 步时设置（每步单独计时）
        self.step_time_limit = 30
        self.current_step_time_left = self.step_time_limit
        self.timer_running = False
        self.timer_id = None
        self.is_ai_thinking = False
        
        # GUI参数
        self.cell_size = 30
        self.board_margin = 40
        self.piece_radius = 12
        
        self.root = tk.Tk()
        self.root.title("五子棋 - A*智能对弈系统（步时限时30秒）")
        
        board_size_px = self.board.size * self.cell_size + 2 * self.board_margin
        total_width = board_size_px + 280
        total_height = board_size_px + 120
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - total_width) // 2
        y = (screen_height - total_height) // 2
        self.root.geometry(f"{total_width}x{total_height}+{x}+{y}")
        self.root.minsize(total_width, total_height)
        self.root.resizable(True, True)
        
        # 创建主框架
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧：棋盘区域
        self.left_frame = tk.Frame(self.main_frame)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 顶部计时器栏
        self.create_timer_bar()
        
        # 棋盘画布
        self.canvas = tk.Canvas(
            self.left_frame, 
            width=board_size_px, 
            height=board_size_px,
            bg='#DEB887',
            highlightthickness=0
        )
        self.canvas.pack(pady=10)
        
        # 右侧控制面板
        self.create_control_panel()
        
        self.draw_board()
        self.canvas.bind("<Button-1>", self.on_click)
        
        self.update_status()
        self.update_move_count()
        
        # 启动游戏
        if self.game_mode == "human_vs_ai" and self.ai_first:
            self.root.after(500, self.ai_move)
        else:
            self.start_step_timer()
    
    def create_timer_bar(self):
        """创建顶部计时器栏"""
        self.timer_frame = tk.Frame(self.left_frame, bg='#2C3E50', height=70)
        self.timer_frame.pack(fill=tk.X, pady=(0, 10))
        self.timer_frame.pack_propagate(False)
        
        # 步时设置区域
        time_set_frame = tk.Frame(self.timer_frame, bg='#2C3E50')
        time_set_frame.pack(side=tk.LEFT, padx=15, pady=5)
        
        tk.Label(
            time_set_frame, 
            text="⏱️ 每步限时:",
            font=("微软雅黑", 11, "bold"),
            bg='#2C3E50',
            fg='white'
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        self.time_limit_var = tk.StringVar(value="30")
        time_spinbox = tk.Spinbox(
            time_set_frame,
            from_=10, to=120, increment=5,
            textvariable=self.time_limit_var,
            width=5,
            font=("微软雅黑", 11),
            command=self.change_step_time_limit
        )
        time_spinbox.pack(side=tk.LEFT, padx=5)
        
        tk.Label(
            time_set_frame, 
            text="秒/步",
            font=("微软雅黑", 11),
            bg='#2C3E50',
            fg='white'
        ).pack(side=tk.LEFT)
        
        # 当前步倒计时显示
        self.step_timer_frame = tk.Frame(self.timer_frame, bg='#2C3E50')
        self.step_timer_frame.pack(side=tk.LEFT, padx=30, pady=5)
        
        self.step_timer_label = tk.Label(
            self.step_timer_frame,
            text="⏰ 当前步剩余: 30秒",
            font=("微软雅黑", 14, "bold"),
            bg='#2C3E50',
            fg='#FFD700'
        )
        self.step_timer_label.pack()
        
        # AI思考时间显示
        self.ai_time_label = tk.Label(
            self.timer_frame, 
            text="🤖 AI思考: 0.00秒",
            font=("微软雅黑", 10),
            bg='#2C3E50',
            fg='#90EE90'
        )
        self.ai_time_label.pack(side=tk.RIGHT, padx=20, pady=5)
        
        # 当前回合提示
        self.turn_label_small = tk.Label(
            self.timer_frame,
            text="",
            font=("微软雅黑", 10),
            bg='#2C3E50',
            fg='#FF6B6B'
        )
        self.turn_label_small.pack(side=tk.RIGHT, padx=10, pady=5)
    
    def create_control_panel(self):
        """创建右侧控制面板"""
        right_container = tk.Frame(self.main_frame, width=260)
        right_container.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right_container.pack_propagate(False)
        
        self.control_canvas = tk.Canvas(right_container, bg='#F0F0F0', highlightthickness=0)
        scrollbar = tk.Scrollbar(right_container, orient=tk.VERTICAL, command=self.control_canvas.yview)
        self.control_canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.control_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.control_frame = tk.Frame(self.control_canvas, bg='#F0F0F0')
        self.control_canvas.create_window((0, 0), window=self.control_frame, anchor='nw', width=250)
        
        self.control_frame.bind('<Configure>', lambda e: self.control_canvas.configure(scrollregion=self.control_canvas.bbox("all")))
        
        # 标题
        title_label = tk.Label(
            self.control_frame, text="五子棋对弈系统", 
            font=("微软雅黑", 14, "bold"), bg='#F0F0F0', fg='#333333'
        )
        title_label.pack(pady=(10, 5))
        
        tk.Frame(self.control_frame, height=2, bg='#CCCCCC').pack(fill=tk.X, padx=10, pady=5)
        
        # 难度选择
        difficulty_frame = tk.LabelFrame(
            self.control_frame, text="🔥 AI难度", font=("微软雅黑", 10, "bold"),
            bg='#F0F0F0', fg='#333333', padx=10, pady=5
        )
        difficulty_frame.pack(fill=tk.X, pady=5, padx=10)
        
        self.difficulty_var = tk.StringVar(value="hard")
        
        tk.Radiobutton(
            difficulty_frame, text="🐣 简单", variable=self.difficulty_var, 
            value="easy", command=self.change_difficulty,
            bg='#F0F0F0', font=("微软雅黑", 10)
        ).pack(anchor=tk.W, pady=2)
        
        tk.Radiobutton(
            difficulty_frame, text="⚖️ 中等", variable=self.difficulty_var, 
            value="medium", command=self.change_difficulty,
            bg='#F0F0F0', font=("微软雅黑", 10)
        ).pack(anchor=tk.W, pady=2)
        
        tk.Radiobutton(
            difficulty_frame, text="🔥 困难（最强）", variable=self.difficulty_var, 
            value="hard", command=self.change_difficulty,
            bg='#F0F0F0', font=("微软雅黑", 10)
        ).pack(anchor=tk.W, pady=2)
        
        # 游戏模式
        mode_frame = tk.LabelFrame(
            self.control_frame, text="🎮 游戏模式", font=("微软雅黑", 10, "bold"),
            bg='#F0F0F0', fg='#333333', padx=10, pady=5
        )
        mode_frame.pack(fill=tk.X, pady=5, padx=10)
        
        self.mode_var = tk.StringVar(value="human_vs_ai")
        tk.Radiobutton(
            mode_frame, text="🤖 人机对弈", variable=self.mode_var, 
            value="human_vs_ai", command=self.change_mode,
            bg='#F0F0F0', font=("微软雅黑", 10)
        ).pack(anchor=tk.W, pady=2)
        tk.Radiobutton(
            mode_frame, text="👥 人人对弈", variable=self.mode_var, 
            value="human_vs_human", command=self.change_mode,
            bg='#F0F0F0', font=("微软雅黑", 10)
        ).pack(anchor=tk.W, pady=2)
        
        # 先手设置
        first_frame = tk.LabelFrame(
            self.control_frame, text="🎯 先手设置", font=("微软雅黑", 10, "bold"),
            bg='#F0F0F0', fg='#333333', padx=10, pady=5
        )
        first_frame.pack(fill=tk.X, pady=5, padx=10)
        
        self.ai_first_var = tk.BooleanVar(value=True)
        tk.Radiobutton(
            first_frame, text="AI先手", variable=self.ai_first_var, 
            value=True, command=self.change_ai_first,
            bg='#F0F0F0', font=("微软雅黑", 10)
        ).pack(anchor=tk.W, pady=2)
        tk.Radiobutton(
            first_frame, text="玩家先手", variable=self.ai_first_var, 
            value=False, command=self.change_ai_first,
            bg='#F0F0F0', font=("微软雅黑", 10)
        ).pack(anchor=tk.W, pady=2)
        
        # 游戏状态
        status_frame = tk.LabelFrame(
            self.control_frame, text="📊 游戏状态", font=("微软雅黑", 10, "bold"),
            bg='#F0F0F0', fg='#333333', padx=10, pady=5
        )
        status_frame.pack(fill=tk.X, pady=5, padx=10)
        
        self.turn_label = tk.Label(
            status_frame, text="当前回合: 黑棋", font=("微软雅黑", 11),
            bg='#F0F0F0', fg='#2196F3'
        )
        self.turn_label.pack(pady=5)
        
        self.move_count_label = tk.Label(
            status_frame, text="步数: 0", font=("微软雅黑", 10),
            bg='#F0F0F0', fg='#666666'
        )
        self.move_count_label.pack(pady=2)
        
        self.winner_label = tk.Label(
            status_frame, text="", font=("微软雅黑", 12, "bold"),
            bg='#F0F0F0', fg='#4CAF50'
        )
        self.winner_label.pack(pady=5)
        
        # 控制按钮
        button_frame = tk.Frame(self.control_frame, bg='#F0F0F0')
        button_frame.pack(fill=tk.X, pady=10, padx=10)
        
        tk.Button(
            button_frame, text="🔄 新游戏", command=self.new_game,
            bg='#4CAF50', fg='white', font=("微软雅黑", 11, "bold"),
            relief=tk.FLAT, cursor='hand2'
        ).pack(fill=tk.X, pady=3)
        
        tk.Button(
            button_frame, text="↩️ 悔棋", command=self.undo_move,
            bg='#FF9800', fg='white', font=("微软雅黑", 11, "bold"),
            relief=tk.FLAT, cursor='hand2'
        ).pack(fill=tk.X, pady=3)
        
        tk.Button(
            button_frame, text="🎲 AI帮我走", command=self.ai_help_move,
            bg='#9C27B0', fg='white', font=("微软雅黑", 11, "bold"),
            relief=tk.FLAT, cursor='hand2'
        ).pack(fill=tk.X, pady=3)
        
        # 算法说明
        info_frame = tk.LabelFrame(
            self.control_frame, text="📖 A*算法说明", font=("微软雅黑", 10, "bold"),
            bg='#F0F0F0', fg='#333333', padx=10, pady=5
        )
        info_frame.pack(fill=tk.X, pady=5, padx=10)
        
        info_text = """f(n) = g(n) + h(n)

g(n) 实际代价:
• 步数惩罚
• 中心距离
• 棋子距离

h(n) 启发代价:
• 棋型评估
• 进攻/防守
• 位置偏好

⏱️ 步时规则:
每步单独计时30秒
超时自动判负！

🎲 AI帮我走:
玩家回合点击AI帮您走棋

↩️ 悔棋规则:
• 人人对战: 悔1步
• 人机对战: 悔2步"""
        
        info_label = tk.Label(
            info_frame, text=info_text, font=("Consolas", 8), 
            justify=tk.LEFT, bg='#F0F0F0', fg='#555555'
        )
        info_label.pack(pady=5)
    
    def change_step_time_limit(self):
        """改变步时限制"""
        try:
            new_limit = int(self.time_limit_var.get())
            if 10 <= new_limit <= 120:
                self.step_time_limit = new_limit
                self.current_step_time_left = self.step_time_limit
                self.update_step_timer_display()
        except ValueError:
            pass
    
    def update_step_timer_display(self):
        """更新步时显示"""
        self.step_timer_label.config(text=f"⏰ 当前步剩余: {self.current_step_time_left}秒")
        
        if self.current_step_time_left <= 5:
            self.step_timer_label.config(fg='red')
        elif self.current_step_time_left <= 10:
            self.step_timer_label.config(fg='orange')
        else:
            self.step_timer_label.config(fg='#FFD700')
    
    def start_step_timer(self):
        """启动当前步倒计时"""
        if self.timer_running:
            self.stop_step_timer()
        
        if self.board.winner is not None:
            return
        
        self.current_step_time_left = self.step_time_limit
        self.update_step_timer_display()
        
        player_name = "黑棋" if self.current_player == 1 else "白棋"
        if self.game_mode == "human_vs_ai":
            is_ai_turn = (self.ai_first and self.current_player == 1) or \
                        (not self.ai_first and self.current_player == 2)
            if is_ai_turn:
                player_name = "AI (" + player_name + ")"
            else:
                player_name = "玩家 (" + player_name + ")"
        self.turn_label_small.config(text=f"🎯 {player_name}思考中")
        
        self.timer_running = True
        self.update_step_countdown()
    
    def stop_step_timer(self):
        """停止步时倒计时"""
        self.timer_running = False
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None
        self.turn_label_small.config(text="")
    
    def update_step_countdown(self):
        """更新步时倒计时"""
        if not self.timer_running:
            return
        
        if self.current_step_time_left <= 0:
            self.on_step_timeout()
            return
        
        self.update_step_timer_display()
        
        self.current_step_time_left -= 1
        self.timer_id = self.root.after(1000, self.update_step_countdown)
    
    def on_step_timeout(self):
        """当前步超时判负"""
        self.timer_running = False
        
        if self.board.winner is not None:
            return
        
        timeout_player = self.current_player
        winner_player = 3 - timeout_player
        
        winner_name = "黑棋" if winner_player == 1 else "白棋"
        loser_name = "黑棋" if timeout_player == 1 else "白棋"
        
        self.board.winner = winner_player
        
        self.winner_label.config(text=f"胜利者: {winner_name}（{loser_name}超时）")
        self.turn_label.config(text="游戏结束")
        
        messagebox.showwarning("超时判负", f"{loser_name}超时！\n{winner_name}获胜！")
        
        self.update_status()
    
    def draw_board(self):
        """绘制棋盘"""
        size = self.board.size
        margin = self.board_margin
        cell = self.cell_size
        
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width > 100:
            cell = min(canvas_width, canvas_height) // (size + 1)
            margin = cell
            self.cell_size = cell
            self.piece_radius = cell // 3
            self.board_margin = margin
        
        for i in range(size):
            self.canvas.create_line(
                margin + i * cell, margin,
                margin + i * cell, margin + (size - 1) * cell,
                fill="#4A3728", width=1
            )
            self.canvas.create_line(
                margin, margin + i * cell,
                margin + (size - 1) * cell, margin + i * cell,
                fill="#4A3728", width=1
            )
        
        star_positions = [(3, 3), (11, 3), (7, 7), (3, 11), (11, 11)]
        star_radius = max(3, cell // 6)
        for x, y in star_positions:
            self.canvas.create_oval(
                margin + x * cell - star_radius, margin + y * cell - star_radius,
                margin + x * cell + star_radius, margin + y * cell + star_radius,
                fill="#4A3728", outline="#4A3728"
            )
        
        for i in range(size):
            for j in range(size):
                piece = self.board.board[i][j]
                if piece != 0:
                    self.draw_piece(i, j, piece)
    
    def draw_piece(self, x, y, player):
        """绘制棋子"""
        margin = self.board_margin
        cell = self.cell_size
        cx = margin + x * cell
        cy = margin + y * cell
        radius = self.piece_radius
        
        color = "black" if player == 1 else "white"
        outline = "#333333" if player == 2 else "black"
        
        self.canvas.create_oval(
            cx - radius, cy - radius,
            cx + radius, cy + radius,
            fill=color, outline=outline, width=1
        )
        
        if self.board.last_move == (x, y):
            marker_radius = max(2, radius // 3)
            self.canvas.create_oval(
                cx - marker_radius, cy - marker_radius,
                cx + marker_radius, cy + marker_radius,
                fill="red", outline="red"
            )
    
    def on_click(self, event):
        """鼠标点击事件"""
        if self.board.winner is not None:
            messagebox.showinfo("游戏结束", "游戏已经结束，请开始新游戏！")
            return
        
        # 检查是否轮到玩家
        if self.game_mode == "human_vs_ai":
            is_player_turn = (not self.ai_first and self.current_player == 1) or \
                            (self.ai_first and self.current_player == 2)
            if not is_player_turn:
                messagebox.showinfo("提示", "现在是AI回合，请等待")
                return
        
        margin = self.board_margin
        cell = self.cell_size
        
        x = round((event.x - margin) / cell)
        y = round((event.y - margin) / cell)
        
        if not (0 <= x < self.board.size and 0 <= y < self.board.size):
            return
        
        if not self.board.is_valid_move(x, y):
            if self.board.board[x][y] != 0:
                messagebox.showinfo("提示", "这里已经有棋子了！")
            return
        
        self.stop_step_timer()
        self.make_move(x, y)
    
    def make_move(self, x, y):
        """执行落子操作"""
        self.board.place_piece(x, y, self.current_player)
        self.draw_piece(x, y, self.current_player)
        self.update_move_count()
        
        if self.board.winner is not None:
            self.stop_step_timer()
            winner_name = "黑棋" if self.board.winner == 1 else "白棋"
            if self.game_mode == "human_vs_ai":
                is_ai = (self.ai_first and self.board.winner == 1) or \
                        (not self.ai_first and self.board.winner == 2)
                if is_ai:
                    winner_name = "AI (" + winner_name + ")"
                else:
                    winner_name = "玩家 (" + winner_name + ")"
            self.winner_label.config(text=f"胜利者: {winner_name}")
            self.turn_label.config(text="游戏结束")
            messagebox.showinfo("游戏结束", f"{winner_name}获胜！")
            return
        
        if self.board.is_full():
            self.stop_step_timer()
            self.winner_label.config(text="平局！")
            self.turn_label.config(text="游戏结束")
            messagebox.showinfo("游戏结束", "平局！")
            return
        
        self.current_player = 3 - self.current_player
        self.update_status()
        
        if self.game_mode == "human_vs_ai":
            is_ai_turn = (self.ai_first and self.current_player == 1) or \
                        (not self.ai_first and self.current_player == 2)
            if is_ai_turn:
                self.root.after(100, self.ai_move)
            else:
                self.start_step_timer()
        else:
            self.start_step_timer()
    
    def ai_move(self):
        """AI走棋（AI自己的回合）"""
        if self.is_ai_thinking:
            return
        
        if self.board.winner is not None:
            return
        
        if self.game_mode == "human_vs_ai":
            is_ai_turn = (self.ai_first and self.current_player == 1) or \
                        (not self.ai_first and self.current_player == 2)
            if not is_ai_turn:
                return
        
        self.is_ai_thinking = True
        self.stop_step_timer()
        
        ai_start_time = time.time()
        self.turn_label.config(text="当前回合: AI思考中...")
        self.turn_label_small.config(text="🤖 AI思考中...")
        self.root.update()
        
        def ai_thinking():
            move = self.ai_player.get_best_move()
            self.root.after(0, lambda: self.ai_move_callback(move, ai_start_time))
        
        thread = threading.Thread(target=ai_thinking)
        thread.daemon = True
        thread.start()
    
    def ai_move_callback(self, move, start_time):
        """AI走棋回调"""
        self.is_ai_thinking = False
        
        ai_elapsed = time.time() - start_time
        self.ai_time_label.config(text=f"🤖 AI思考: {ai_elapsed:.2f}秒")
        
        if move:
            x, y = move
            if self.board.is_valid_move(x, y):
                self.make_move(x, y)
            else:
                move = self.ai_player._greedy_best_move()
                if move:
                    x, y = move
                    if self.board.is_valid_move(x, y):
                        self.make_move(x, y)
    
    def ai_help_move(self):
        """AI帮我走 - 在玩家回合帮助玩家走棋"""
        if self.board.winner is not None:
            messagebox.showinfo("提示", "游戏已经结束")
            return
        
        if self.game_mode != "human_vs_ai":
            messagebox.showinfo("提示", "AI帮我走仅适用于人机对弈模式")
            return
        
        is_player_turn = (not self.ai_first and self.current_player == 1) or \
                        (self.ai_first and self.current_player == 2)
        
        if not is_player_turn:
            messagebox.showinfo("提示", "现在是AI回合，不能使用AI帮我走")
            return
        
        if self.is_ai_thinking:
            messagebox.showinfo("提示", "AI正在思考中，请稍候")
            return
        
        self.stop_step_timer()
        
        self.turn_label.config(text="AI正在帮您走棋...")
        self.turn_label_small.config(text="🤖 AI帮您走棋中...")
        self.root.update()
        
        help_start_time = time.time()
        
        original_player = self.ai_player.player
        self.ai_player.player = self.current_player
        move = self.ai_player.get_best_move()
        self.ai_player.player = original_player
        
        help_elapsed = time.time() - help_start_time
        self.ai_time_label.config(text=f"🤖 AI帮走: {help_elapsed:.2f}秒")
        
        if move:
            x, y = move
            if self.board.is_valid_move(x, y):
                self.make_move(x, y)
                messagebox.showinfo("AI帮走", f"AI帮您在({x}, {y})落子")
            else:
                messagebox.showwarning("AI帮走失败", "AI推荐的位置无效，请手动落子")
                self.start_step_timer()
        else:
            messagebox.showwarning("AI帮走失败", "AI无法找到合适的位置，请手动落子")
            self.start_step_timer()
    
    def update_status(self):
        """更新状态显示"""
        if self.board.winner is not None:
            return
        
        turn_text = "黑棋" if self.current_player == 1 else "白棋"
        
        if self.game_mode == "human_vs_ai":
            is_ai_turn = (self.ai_first and self.current_player == 1) or \
                        (not self.ai_first and self.current_player == 2)
            if is_ai_turn:
                turn_text += " (AI)"
            else:
                turn_text += " (玩家)"
        
        self.turn_label.config(text=f"当前回合: {turn_text}")
    
    def update_move_count(self):
        """更新步数显示"""
        self.move_count_label.config(text=f"步数: {len(self.board.move_history)}")
    
    def change_difficulty(self):
        """改变AI难度"""
        new_difficulty = self.difficulty_var.get()
        if self.ai_player:
            self.ai_player.set_difficulty(new_difficulty)
            difficulty_names = {'easy': '简单', 'medium': '中等', 'hard': '困难'}
            self.turn_label.config(text=f"难度已切换为: {difficulty_names[new_difficulty]}")
            self.root.after(2000, self.update_status)
    
    def new_game(self):
        """新游戏"""
        self.stop_step_timer()
        self.is_ai_thinking = False
        self.board.reset()
        self.current_player = 1
        self.board.winner = None
        self.winner_label.config(text="")
        
        self.current_step_time_left = self.step_time_limit
        self.update_step_timer_display()
        
        self.update_status()
        self.update_move_count()
        
        self.canvas.delete("all")
        self.draw_board()
        
        self.ai_time_label.config(text="🤖 AI思考: 0.00秒")
        self.turn_label_small.config(text="")
        
        if self.game_mode == "human_vs_ai":
            if self.ai_first:
                self.root.after(500, self.ai_move)
            else:
                self.start_step_timer()
        else:
            self.start_step_timer()
    
    def undo_move(self):
        """悔棋 - 人人悔1步，人机悔2步"""
        if self.is_ai_thinking:
            messagebox.showinfo("提示", "AI正在思考，请稍后再试")
            return
        
        self.stop_step_timer()
        
        history_count = len(self.board.move_history)
        
        if history_count == 0:
            messagebox.showinfo("提示", "没有棋子可以悔棋")
            self.start_step_timer()
            return
        
        # 人人对弈模式：悔棋1步
        if self.game_mode == "human_vs_human":
            if history_count >= 1:
                # 移除最后一步
                x, y, player = self.board.move_history.pop()
                self.board.board[x][y] = 0
                self.board.last_move = None
                self.board.winner = None
                
                # 切换回悔棋前的玩家（被悔棋的玩家重新下）
                self.current_player = player
                self.winner_label.config(text="")
                
                # 刷新界面
                self.canvas.delete("all")
                self.draw_board()
                self.update_status()
                self.update_move_count()
                
                player_name = "黑棋" if self.current_player == 1 else "白棋"
                messagebox.showinfo("悔棋成功", f"已撤回1步，现在轮到{player_name}")
                
                # 重新启动计时器
                self.start_step_timer()
            else:
                messagebox.showinfo("提示", "没有棋子可以悔棋")
                self.start_step_timer()
        
        # 人机对弈模式：悔棋2步（撤回玩家和AI各一步）
        else:  # human_vs_ai
            if history_count >= 2:
                # 移除最后两步（AI的棋和玩家的棋）
                for _ in range(2):
                    if self.board.move_history:
                        x, y, _ = self.board.move_history.pop()
                        self.board.board[x][y] = 0
                
                self.board.last_move = None
                self.board.winner = None
                
                # 悔棋后轮到玩家
                if self.ai_first:
                    # AI先手：悔棋后应该是玩家回合
                    self.current_player = 2  # 白棋（玩家）
                else:
                    # 玩家先手：悔棋后应该是玩家回合
                    self.current_player = 1  # 黑棋（玩家）
                
                self.winner_label.config(text="")
                
                # 刷新界面
                self.canvas.delete("all")
                self.draw_board()
                self.update_status()
                self.update_move_count()
                
                messagebox.showinfo("悔棋成功", "已撤回2步（撤回AI和玩家各一步），现在轮到玩家")
                
                # 重新启动玩家计时器
                self.start_step_timer()
            else:
                messagebox.showinfo("提示", "无法悔棋，至少需要2步才能悔棋")
                self.start_step_timer()
    
    def change_mode(self):
        """切换游戏模式"""
        self.stop_step_timer()
        self.is_ai_thinking = False
        self.game_mode = self.mode_var.get()
        self.new_game()
        
        if self.game_mode == "human_vs_ai":
            self.ai_first = self.ai_first_var.get()
            self.ai_player.player = 1 if self.ai_first else 2
            self.change_difficulty()
            if self.ai_first:
                self.root.after(500, self.ai_move)
            else:
                self.start_step_timer()
    
    def change_ai_first(self):
        """切换AI先手"""
        self.ai_first = self.ai_first_var.get()
        if self.game_mode == "human_vs_ai":
            self.new_game()
    
    def run(self):
        """运行GUI"""
        self.root.mainloop()


# ==================== 主程序入口 ====================
def main():
    """主函数"""
    board = GobangBoard(size=15)
    evaluator = Evaluator(board_size=15)
    ai_player = AIPlayer(board, evaluator, player=1, difficulty='hard')
    gui = GobangGUI(board, ai_player)
    gui.run()


if __name__ == "__main__":
    main()