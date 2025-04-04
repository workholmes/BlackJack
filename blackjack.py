import os
import csv
import random
import json
import time
import datetime
from typing import Dict, List, Optional, Any
from plugins import *
from common.log import logger
from bridge.context import ContextType, Context
from bridge.reply import Reply, ReplyType
from channel.chat_message import ChatMessage
import plugins

from .player import BJPlayer
from .blackjack_game import BJGame, Card

@plugins.register(
    name="BlackJack",
    desc="21点赌场游戏",
    version="0.2.0",
    author="assistant",
    desire_priority=0
)
class BlackJack(Plugin):
    # 标准字段列表
    STANDARD_FIELDS = [
        'user_id', 'session_id', 'nickname', 'chips', 'level', 'exp', 
        'total_wins', 'total_losses', 'total_draws', 'last_checkin', 
        'blackjack_count', 'ready_status', 'current_bet', 'cards'
    ]
    
    # 游戏状态相关变量
    game_instances = {}  # 群聊ID -> 游戏实例
    ready_players = {}   # 群聊ID -> 准备好的玩家ID列表
    
    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        
        try:
            # 初始化数据目录
            self.data_dir = os.path.join(os.path.dirname(__file__), "data")
            os.makedirs(self.data_dir, exist_ok=True)
            
            # 初始化玩家数据文件
            self.player_file = os.path.join(self.data_dir, "bjplayers.csv")
            
            # 创建玩家数据文件（如果不存在）
            if not os.path.exists(self.player_file):
                with open(self.player_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=self.STANDARD_FIELDS)
                    writer.writeheader()
            
            # 恢复游戏会话（如果有）
            self._restore_game_sessions()
            
            logger.info("[BlackJack] 插件初始化完成")
        except Exception as e:
            logger.error(f"[BlackJack] 初始化出错: {e}")
            raise
            
    def _restore_game_sessions(self):
        """恢复游戏会话"""
        # 这个方法将从文件中加载任何之前保存的游戏会话
        # 简单起见，当前版本不实现持久化游戏状态
        pass
        
    def on_handle_context(self, e_context: EventContext):
        """处理上下文事件"""
        if e_context['context'].type != ContextType.TEXT:
            return
            
        content = e_context['context'].content.strip()
        msg: ChatMessage = e_context['context']['msg']
        
        # 获取会话ID和用户信息
        isgroup = e_context["context"].get("isgroup")
        
        if isgroup:
            # 群消息
            user_id = msg.actual_user_id 
            nickname = msg.actual_user_nickname
            # 从econtext获取session_id
            session_id = e_context.econtext["context"]["session_id"]
            # 清理session_id中可能的分隔符
            if "@@" in session_id:
                session_id = session_id.split("@@")[0]
            # 获取群聊ID
            group_id = e_context.econtext["context"]["receiver"]
        else:
            # 私聊消息
            user_id = msg.from_user_id
            nickname = msg.from_user_nickname
            # 私聊时，使用receiver作为session_id
            session_id = e_context.econtext["context"]["receiver"]
            group_id = None
        
        if not session_id:
            return "无法获取您的会话ID，请确保ID已设置"
            
        logger.debug(f"[BlackJack] 当前用户信息 - session_id: {session_id}, user_id: {user_id}, nickname: {nickname}, group_id: {group_id}")
        
        # 命令处理
        cmd_handlers = {
            "BlackJack注册": lambda s, u, n, g: self.register_player(s, u, n),
            "21点注册": lambda s, u, n, g: self.register_player(s, u, n),
            "BlackJack签到": lambda s, u, n, g: self.daily_checkin(s),
            "21点签到": lambda s, u, n, g: self.daily_checkin(s),
            "BlackJack状态": lambda s, u, n, g: self.get_player_status(s),
            "21点状态": lambda s, u, n, g: self.get_player_status(s),
            "BlackJack排行榜": lambda s, u, n, g: self.show_leaderboard(s, content),
            "21点排行榜": lambda s, u, n, g: self.show_leaderboard(s, content),
            "BlackJack菜单": lambda s, u, n, g: self.game_help(),
            "21点菜单": lambda s, u, n, g: self.game_help(),
            "BlackJack规则": lambda s, u, n, g: self.game_rules(),
            "21点规则": lambda s, u, n, g: self.game_rules(),
            "BlackJack准备": lambda s, u, n, g: self.player_ready(s, n, g),
            "21点准备": lambda s, u, n, g: self.player_ready(s, n, g),
            "开始BlackJack": lambda s, u, n, g: self.start_game(s, g),
            "开始21点": lambda s, u, n, g: self.start_game(s, g),
            "21点开始": lambda s, u, n, g: self.start_game(s, g),
            "下注": lambda s, u, n, g: self.place_bet(s, content, g),
            "要牌": lambda s, u, n, g: self.hit(s, g),
            "停牌": lambda s, u, n, g: self.stand(s, g),
            "加倍": lambda s, u, n, g: self.double_down(s, g),
            "分牌": lambda s, u, n, g: self.split(s, g),
            "查看牌局": lambda s, u, n, g: self.show_game_state(s, g),
            "清理BlackJack": lambda s, u, n, g: self.reset_blackjack_game(s, g),
            "清理21点": lambda s, u, n, g: self.reset_blackjack_game(s, g),
            "重置BlackJack": lambda s, u, n, g: self.reset_all_data(s, u),
            "重置21点": lambda s, u, n, g: self.reset_all_data(s, u),
            "BJStatus": lambda s, u, n, g: self.show_debug_status(s, g)
        }
        
        # 查找命令
        cmd = content.split()[0] if content.split() else ""
        
        # 特殊处理下注无空格情况
        if content.startswith("下注") and len(content) > 2 and not content.startswith("下注 "):
            reply = self.place_bet(session_id, content, group_id)
            e_context['reply'] = Reply(ReplyType.TEXT, reply)
            e_context.action = EventAction.BREAK_PASS
        elif cmd in cmd_handlers:
            reply = cmd_handlers[cmd](session_id, user_id, nickname, group_id)
            e_context['reply'] = Reply(ReplyType.TEXT, reply)
            e_context.action = EventAction.BREAK_PASS
        else:
            # 尝试进行大小写不敏感匹配
            cmd_lower = cmd.lower()
            found = False
            for command in cmd_handlers:
                if command.lower() == cmd_lower:
                    reply = cmd_handlers[command](session_id, user_id, nickname, group_id)
                    e_context['reply'] = Reply(ReplyType.TEXT, reply)
                    e_context.action = EventAction.BREAK_PASS
                    found = True
                    break
            if not found:
                e_context.action = EventAction.CONTINUE
            
    def register_player(self, session_id, user_id=None, nickname=None):
        """注册新玩家
        
        Args:
            session_id: 会话ID，作为唯一标识符
            user_id: 玩家ID，可选
            nickname: 玩家昵称，如果未提供则使用session_id
        """
        if not session_id:
            return "无法获取您的会话ID，请确保ID已设置"
        
        # 检查是否已注册
        if self.get_player(session_id):
            return "您已经注册过21点游戏了"
        
        try:
            # 如果没有提供昵称，使用session_id作为默认昵称
            if not nickname:
                nickname = str(session_id)
            
            # 创建新玩家
            player = BJPlayer.create_new(user_id or session_id, nickname, session_id)
            player.player_file = self.player_file
            player.standard_fields = self.STANDARD_FIELDS
            
            # 保存玩家数据
            with open(self.player_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.STANDARD_FIELDS)
                writer.writerow(player.to_dict())
            
            return f"🃏 恭喜！{nickname} 成功注册21点游戏\n💰 初始筹码: 1000\n输入「21点菜单」查看游戏指令"
        except Exception as e:
            logger.error(f"注册21点玩家出错: {e}")
            return "注册失败，请稍后再试"
            
    def get_player(self, user_id) -> Optional[BJPlayer]:
        """获取玩家数据"""
        try:
            player = BJPlayer.get_player(user_id, self.player_file)
            if player:
                # 设置必要的文件信息
                player.player_file = self.player_file
                player.standard_fields = self.STANDARD_FIELDS
            return player
        except Exception as e:
            logger.error(f"获取21点玩家数据出错: {e}")
            raise
            
    def daily_checkin(self, user_id):
        """每日签到"""
        player = self.get_player(user_id)
        if not player:
            return "您还没有注册21点游戏，请先发送「21点注册」进行注册"
            
        # 检查是否已经签到
        current_date = datetime.datetime.now().strftime('%Y-%m-%d')
        if player.last_checkin == current_date:
            return f"您今天已经签到过了，明天再来吧"
            
        # 计算奖励
        base_reward = 200
        level_bonus = player.level * 50
        total_reward = base_reward + level_bonus
        
        # 增加经验值
        current_exp = player.exp
        new_exp = current_exp + 10
        
        # 检查是否升级
        current_level = player.level
        exp_needed = int(current_level * 100 * (1 + (current_level - 1) * 0.5))
        if new_exp >= exp_needed:
            new_level = current_level + 1
            new_chips = player.chips + total_reward + 300  # 升级额外奖励300筹码
            result = [
                f"🎉 签到成功！获得 {total_reward} 筹码",
                f"🎊 恭喜升级到 {new_level} 级！额外奖励 300 筹码",
                f"当前筹码: {new_chips}"
            ]
        else:
            new_level = current_level
            new_chips = player.chips + total_reward
            result = [
                f"🎉 签到成功！获得 {total_reward} 筹码",
                f"当前筹码: {new_chips}",
                f"距离下一级还需要: {exp_needed - new_exp} 经验"
            ]
            
        # 更新玩家数据
        self._update_player_data(user_id, {
            'chips': str(new_chips),
            'level': str(new_level),
            'exp': str(new_exp),
            'last_checkin': current_date
        })
        
        return "\n".join(result)
        
    def get_player_status(self, user_id):
        """获取玩家状态"""
        player = self.get_player(user_id)
        if not player:
            return "您还没有注册21点游戏，请先发送「21点注册」进行注册"
            
        return player.get_player_status()
        
    def show_leaderboard(self, user_id, content):
        """显示排行榜"""
        player = self.get_player(user_id)
        if not player:
            return "您还没有注册21点游戏，请先发送「21点注册」进行注册"
            
        # 解析命令参数
        parts = content.split()
        leaderboard_type = parts[1] if len(parts) > 1 else "chips"
        
        valid_types = ["chips", "胜场", "筹码", "blackjack"]
        if leaderboard_type not in valid_types:
            leaderboard_type = "chips"
            
        # 读取所有玩家数据
        all_players = []
        try:
            with open(self.player_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                all_players = list(reader)
        except Exception as e:
            logger.error(f"读取玩家数据出错: {e}")
            return "读取排行榜数据失败，请稍后再试"
            
        # 根据类型排序
        if leaderboard_type in ["chips", "筹码"]:
            sorted_players = sorted(all_players, key=lambda x: int(x.get('chips', 0)), reverse=True)
            title = "💰 21点筹码排行榜"
            field = "chips"
            prefix = ""
        elif leaderboard_type == "胜场":
            sorted_players = sorted(all_players, key=lambda x: int(x.get('total_wins', 0)), reverse=True)
            title = "🏆 21点胜场排行榜"
            field = "total_wins"
            prefix = ""
        elif leaderboard_type == "blackjack":
            sorted_players = sorted(all_players, key=lambda x: int(x.get('blackjack_count', 0)), reverse=True)
            title = "🎯 21点BlackJack次数排行榜"
            field = "blackjack_count"
            prefix = ""
            
        # 构建排行榜显示
        result = [title, "————————————"]
        
        # 只显示前10名
        for i, p in enumerate(sorted_players[:10], 1):
            player_nickname = p.get('nickname', '未知玩家')
            value = int(p.get(field, 0))
            result.append(f"{i}. {player_nickname}: {prefix}{value}")
            
        # 添加用户自己的排名
        user_rank = next((i for i, p in enumerate(sorted_players, 1) 
                         if p.get('user_id') == player.user_id), None)
        if user_rank:
            if user_rank > 10:
                result.append("...")
                result.append(f"{user_rank}. {player.nickname}: {prefix}{getattr(player, field)}")
                
        return "\n".join(result)
        
    def _update_player_data(self, user_id, updates: dict):
        """更新玩家数据"""
        player = self.get_player(user_id)
        if player:
            player.update_data(updates)
            
    def game_help(self):
        """显示游戏菜单"""
        return """
🃏 21点游戏指令大全 🃏

基础指令
————————————
📝 21点注册 - 注册21点游戏
📊 21点状态 - 查看玩家状态
📅 21点签到 - 每日签到领取筹码
📜 21点规则 - 查看游戏规则
📋 21点菜单 - 显示指令菜单

游戏指令
————————————
🎮 21点准备 - 准备参与游戏
🎲 21点开始 - 开始游戏(需至少1人准备)
💰 下注[数量] - 下注筹码
🎯 要牌 - 要一张牌
🛑 停牌 - 不再要牌
💪 加倍 - 加倍下注并只要一张牌
✂️ 分牌 - 将两张相同点数的牌分成两副(需额外下注)
👀 查看牌局 - 查看当前牌局状态
🧹 清理21点 - 重置游戏状态(出错时使用)

管理指令
————————————
🔄 重置21点 - 清空所有玩家数据和排行榜(管理员专用)

其他功能
————————————
🏆 21点排行榜 [类型] - 查看排行榜
    类型: 筹码(默认)、胜场、blackjack
"""

    def game_rules(self):
        """显示游戏规则"""
        return """
🃏 21点游戏规则 🃏

游戏目标
————————————
尽可能使手牌点数接近21点但不超过21点，同时打败庄家。

牌面点数
————————————
• 2-10的牌: 按牌面值计算
• J、Q、K: 均为10点
• A: 可算作1点或11点，自动选择有利的点数

基本规则
————————————
1. 游戏开始前，玩家需先准备，然后下注
2. 开局每人获得2张牌，庄家1张明牌1张暗牌
3. 轮流行动，可以选择要牌、停牌、加倍或分牌
4. 超过21点为爆牌，直接输掉本局
5. 玩家行动完毕后，庄家亮出底牌并按规则要牌
6. 庄家规则: 手牌小于17点必须要牌，17点及以上必须停牌

特殊规则
————————————
• BlackJack: 首两张牌为A+10点牌(10/J/Q/K)，赔率为3:2
• 加倍(Double Down): 仅限首两张牌时，加倍下注并只能再要一张牌
• 分牌(Split): 当首两张牌点数相同时，可以分成两副牌，每副牌单独下注和操作

胜负判定
————————————
• 玩家BlackJack且庄家非BlackJack: 玩家胜(赔率3:2)
• 玩家爆牌: 庄家胜
• 庄家爆牌: 玩家胜
• 点数比较: 谁更接近21点谁胜
• 点数相同: 平局，退还下注
"""

    def player_ready(self, user_id, nickname, group_id):
        """玩家准备"""
        if not group_id:
            return "21点游戏只能在群聊中进行，请在群聊中使用此指令"
            
        player = self.get_player(user_id)
        if not player:
            return "您还没有注册21点游戏，请先发送「21点注册」进行注册"
            
        # 检查是否已存在正在进行的游戏
        if group_id in self.game_instances and self.game_instances[group_id].game_status != "waiting":
            return "当前已有游戏正在进行中，请等待本局结束后再准备"
            
        # 更新玩家准备状态
        self._update_player_data(user_id, {'ready_status': 'True'})
        
        # 初始化准备玩家列表
        if group_id not in self.ready_players:
            self.ready_players[group_id] = []
            
        # 如果玩家已经在列表中，不重复添加
        if user_id not in self.ready_players[group_id]:
            self.ready_players[group_id].append(user_id)
            
        count = len(self.ready_players[group_id])
        return f"🎮 {nickname} 已准备\n当前已有 {count} 人准备\n发送「21点开始」开始游戏"
        
    def start_game(self, user_id, group_id):
        """开始游戏"""
        if not group_id:
            return "21点游戏只能在群聊中进行，请在群聊中使用此指令"
            
        player = self.get_player(user_id)
        if not player:
            return "您还没有注册21点游戏，请先发送「21点注册」进行注册"
            
        # 检查是否已存在正在进行的游戏
        if group_id in self.game_instances and self.game_instances[group_id].game_status != "waiting":
            return "当前已有游戏正在进行中"
            
        # 检查准备的玩家数量
        if group_id not in self.ready_players or len(self.ready_players[group_id]) < 1:
            return "至少需要1名玩家准备才能开始游戏，请使用「21点准备」准备参与"
            
        # 创建新游戏实例
        game = BJGame()
        game.start_new_game(self.ready_players[group_id])
        self.game_instances[group_id] = game
        
        # 重置准备列表
        ready_players = self.ready_players[group_id].copy()
        self.ready_players[group_id] = []
        
        # 将所有准备玩家的状态重置为未准备
        for player_id in ready_players:
            self._update_player_data(player_id, {'ready_status': 'False'})
            
        # 准备开始消息
        players_str = []
        for player_id in ready_players:
            p = self.get_player(player_id)
            if p:
                players_str.append(f"{p.nickname} (筹码:{p.chips})")
                
        # 开始游戏提示
        result = [
            "🎲 21点游戏开始！",
            f"参与玩家: {', '.join(players_str)}",
            "————————————",
            "请各位玩家发送「下注[筹码数量]」进行下注",
            "例如: 下注100"
        ]
        
        return "\n".join(result)
        
    def place_bet(self, user_id, content, group_id):
        """玩家下注"""
        if not group_id:
            return "21点游戏只能在群聊中进行，请在群聊中使用此指令"
            
        player = self.get_player(user_id)
        if not player:
            return "您还没有注册21点游戏，请先发送「21点注册」进行注册"
            
        # 检查游戏是否存在
        if group_id not in self.game_instances:
            return "当前没有正在进行的游戏，请先使用「21点准备」准备参与"
            
        game = self.game_instances[group_id]
        
        # 检查游戏状态
        if game.game_status != "betting":
            return "当前不是下注阶段"
            
        # 检查玩家是否在游戏中
        if user_id not in game.player_hands:
            return "您不是本局游戏的参与者"
            
        # 解析下注金额
        try:
            # 支持有空格和无空格两种格式
            if " " in content:
                # 有空格格式: "下注 100"
                bet_amount = int(content.split()[1])
            else:
                # 无空格格式: "下注100"
                # 首先确认内容以"下注"开头
                if not content.startswith("下注"):
                    return "下注格式错误，请使用「下注100」，例如：下注100"
                # 提取数字部分
                bet_str = content[2:].strip()
                bet_amount = int(bet_str)
                
                logger.debug(f"[BlackJack] 无空格下注 - 原始内容: '{content}', 提取数字: '{bet_str}', 金额: {bet_amount}")
        except (ValueError, IndexError) as e:
            logger.error(f"[BlackJack] 下注解析错误: {e}, 内容: '{content}'")
            return f"下注格式错误，请使用「下注100」，例如：下注100"
            
        # 检查下注金额是否合法
        if bet_amount <= 0:
            return "下注金额必须大于0"
            
        if bet_amount > player.chips:
            return f"下注失败，您的筹码不足\n当前筹码: {player.chips}"
            
        # 更新下注金额
        game.place_bet(user_id, bet_amount)
        
        # 立即扣除下注筹码并更新玩家数据
        new_chips = player.chips - bet_amount
        player.chips = new_chips
        self._update_player_data(user_id, {'chips': str(new_chips), 'current_bet': str(bet_amount)})
        
        result = [f"💰 {player.nickname} 下注 {bet_amount} 筹码"]
        
        # 检查哪些玩家还未下注
        waiting_players = []
        for player_id in game.player_hands:
            if game.player_bets.get(player_id, 0) == 0:
                p = self.get_player(player_id)
                if p:
                    waiting_players.append(p.nickname)
        
        # 显示待下注玩家
        if waiting_players:
            result.append(f"\n等待下注: {', '.join(waiting_players)}")
        else:
            # 如果所有玩家都已下注，发牌
            result.append("\n所有玩家已完成下注，开始发牌...")
            result.append(self._deal_initial_cards(group_id))
            
        return "\n".join(result)
        
    def _deal_initial_cards(self, group_id):
        """发放初始牌"""
        game = self.game_instances[group_id]
        game.deal_initial_cards()
        
        # 生成游戏状态消息
        result = ["🃏 初始发牌完成", "————————————"]
        
        # 显示庄家的明牌
        dealer_card = game.dealer_hand[0]
        result.append(f"庄家明牌: {dealer_card}")
        
        # 显示每个玩家的手牌
        for player_id in game.player_hands:
            player = self.get_player(player_id)
            if not player:
                continue
                
            # 由于初始发牌阶段，每个玩家只有一副手牌，所以直接使用索引0
            player_hand = game.player_hands[player_id][0]
            hand_value = game.calculate_hand_value(player_hand)
            hand_str = ", ".join(str(card) for card in player_hand)
            
            result.append(f"\n{player.nickname} ({hand_value}点): {hand_str}")
            
            # 检查是否是BlackJack
            if len(player_hand) == 2 and hand_value == 21:
                result.append(f"🎉 BlackJack! 恭喜 {player.nickname}!")
                # 更新blackjack计数
                current_count = int(player.blackjack_count)
                self._update_player_data(player_id, {'blackjack_count': str(current_count + 1)})
        
        # 更新游戏状态
        game.game_status = "playing"
        game.current_player_idx = 0
        
        # 显示轮到哪个玩家操作
        player_ids = list(game.player_hands.keys())
        if player_ids:
            current_player_id = player_ids[game.current_player_idx]
            current_player = self.get_player(current_player_id)
            if current_player:
                result.append(f"\n轮到 {current_player.nickname} 行动")
                
                # 显示可用操作
                actions = ["要牌", "停牌", "加倍"]
                # 检查是否可以分牌
                if game.can_split(current_player_id):
                    actions.append("分牌")
                    
                result.append(f"可选操作: 「{'」「'.join(actions)}」")
        
        return "\n".join(result)
        
    def hit(self, user_id, group_id):
        """玩家要牌"""
        if not group_id:
            return "21点游戏只能在群聊中进行，请在群聊中使用此指令"
            
        player = self.get_player(user_id)
        if not player:
            return "您还没有注册21点游戏，请先发送「21点注册」进行注册"
            
        # 检查游戏是否存在
        if group_id not in self.game_instances:
            return "当前没有正在进行的游戏"
            
        game = self.game_instances[group_id]
        
        # 检查游戏状态
        if game.game_status != "playing":
            return "当前不是玩家行动阶段"
            
        # 检查是否轮到该玩家
        player_ids = list(game.player_hands.keys())
        player_index = player_ids.index(user_id) if user_id in player_ids else -1
        if player_index != game.current_player_idx:
            current_player_id = player_ids[game.current_player_idx]
            current_player = self.get_player(current_player_id)
            return f"当前轮到 {current_player.nickname} 行动，请等待您的回合"
            
        # 获取当前手牌索引
        hand_idx = game.current_hand_idx.get(user_id, 0)
            
        # 执行要牌操作
        result_ok, new_card, hand_value, is_bust = game.hit(user_id)
        if not result_ok or not new_card:
            return "要牌失败，请稍后再试"
            
        player_hand = game.player_hands[user_id][hand_idx]
        
        # 显示手牌标识（如果玩家有多副手牌）
        hand_marker = f"手牌{hand_idx+1} " if len(game.player_hands[user_id]) > 1 else ""
        
        result = [f"🃏 {player.nickname} {hand_marker}要了一张牌: {new_card}"]
        result.append(f"当前手牌 ({hand_value}点): {', '.join(str(card) for card in player_hand)}")
        
        # 检查是否爆牌
        if hand_value > 21:
            result.append(f"💥 爆牌了! {player.nickname} {hand_marker}输掉了本局")
            # 更新玩家战绩
            current_losses = int(player.total_losses)
            player.total_losses = str(current_losses + 1)
            self._update_player_data(user_id, {'total_losses': str(current_losses + 1)})
            
            # 注意：由于在下注时已经扣除筹码，这里不需要再扣除
            # 设置玩家状态为爆牌，以便结算时跳过
            game.player_statuses[user_id][hand_idx] = "bust"
            
            # 进入下一个玩家的回合或庄家行动
            next_action = self._move_to_next_player(group_id)
            if next_action:
                result.append(next_action)
        else:
            # 如果没有爆牌，显示可用操作
            # 显示可用操作
            actions = ["要牌", "停牌"]
            # 检查是否可以加倍（只有在只有两张牌时才能加倍）
            if len(player_hand) == 2:
                actions.append("加倍")
            # 检查是否可以分牌
            if game.can_split(user_id):
                actions.append("分牌")
                
            result.append(f"可选操作: 「{'」「'.join(actions)}」")
        
        return "\n".join(result)
        
    def stand(self, user_id, group_id):
        """玩家停牌"""
        if not group_id:
            return "21点游戏只能在群聊中进行，请在群聊中使用此指令"
            
        player = self.get_player(user_id)
        if not player:
            return "您还没有注册21点游戏，请先发送「21点注册」进行注册"
            
        # 检查游戏是否存在
        if group_id not in self.game_instances:
            return "当前没有正在进行的游戏"
            
        game = self.game_instances[group_id]
        
        # 检查游戏状态
        if game.game_status != "playing":
            return "当前不是玩家行动阶段"
            
        # 检查是否轮到该玩家
        player_ids = list(game.player_hands.keys())
        player_index = player_ids.index(user_id) if user_id in player_ids else -1
        if player_index != game.current_player_idx:
            current_player_id = player_ids[game.current_player_idx]
            current_player = self.get_player(current_player_id)
            return f"当前轮到 {current_player.nickname} 行动，请等待您的回合"
            
        # 获取当前手牌索引
        hand_idx = game.current_hand_idx.get(user_id, 0)
            
        # 执行停牌操作
        success = game.stand(user_id)
        if not success:
            return "停牌失败，请稍后再试"
            
        player_hand = game.player_hands[user_id][hand_idx]
        hand_value = game.calculate_hand_value(player_hand)
        
        # 显示手牌标识（如果玩家有多副手牌）
        hand_marker = f"手牌{hand_idx+1} " if len(game.player_hands[user_id]) > 1 else ""
        
        result = [f"🛑 {player.nickname} {hand_marker}选择停牌"]
        result.append(f"最终手牌 ({hand_value}点): {', '.join(str(card) for card in player_hand)}")
        
        # 进入下一个玩家的回合或庄家行动
        next_action = self._move_to_next_player(group_id)
        if next_action:
            result.append(next_action)
        
        return "\n".join(result)
        
    def double_down(self, user_id, group_id):
        """玩家加倍"""
        if not group_id:
            return "21点游戏只能在群聊中进行，请在群聊中使用此指令"
            
        player = self.get_player(user_id)
        if not player:
            return "您还没有注册21点游戏，请先发送「21点注册」进行注册"
            
        # 检查游戏是否存在
        if group_id not in self.game_instances:
            return "当前没有正在进行的游戏"
            
        game = self.game_instances[group_id]
        
        # 检查游戏状态
        if game.game_status != "playing":
            return "当前不是玩家行动阶段"
            
        # 检查是否轮到该玩家
        player_ids = list(game.player_hands.keys())
        player_index = player_ids.index(user_id) if user_id in player_ids else -1
        if player_index != game.current_player_idx:
            current_player_id = player_ids[game.current_player_idx]
            current_player = self.get_player(current_player_id)
            return f"当前轮到 {current_player.nickname} 行动，请等待您的回合"
        
        # 获取当前手牌索引
        hand_idx = game.current_hand_idx.get(user_id, 0)
        
        # 检查是否符合加倍条件
        if len(game.player_hands[user_id][hand_idx]) != 2:
            return "只有在拥有两张牌时才能加倍"
            
        # 检查玩家筹码是否足够
        bet_amount = game.player_bets[user_id][hand_idx]
        if player.chips < bet_amount:
            return f"加倍失败，您的筹码不足\n当前筹码: {player.chips}\n所需筹码: {bet_amount}"
            
        # 执行加倍操作
        success, new_card, hand_value, is_bust = game.double_down(user_id)
        if not success or not new_card:
            return "加倍失败，请稍后再试"
            
        player_hand = game.player_hands[user_id][hand_idx]
        
        # 显示手牌标识（如果玩家有多副手牌）
        hand_marker = f"手牌{hand_idx+1} " if len(game.player_hands[user_id]) > 1 else ""
        
        # 更新玩家数据
        new_bet = bet_amount * 2
        new_chips = player.chips - bet_amount  # 再扣一次下注金额
        player.chips = new_chips
        self._update_player_data(user_id, {
            'chips': str(new_chips)
        })
        
        result = [f"💪 {player.nickname} {hand_marker}选择加倍!"]
        result.append(f"下注金额增加到 {new_bet} 筹码")
        result.append(f"获得一张牌: {new_card}")
        result.append(f"最终手牌 ({hand_value}点): {', '.join(str(card) for card in player_hand)}")
        
        # 检查是否爆牌
        if hand_value > 21:
            result.append(f"💥 爆牌了! {player.nickname} {hand_marker}输掉了本局")
            # 更新玩家战绩
            current_losses = int(player.total_losses)
            self._update_player_data(user_id, {'total_losses': str(current_losses + 1)})
            
        # 进入下一个玩家的回合或庄家行动
        next_action = self._move_to_next_player(group_id)
        if next_action:
            result.append(next_action)
        
        return "\n".join(result)
        
    def _move_to_next_player(self, group_id):
        """移动到下一个玩家或下一副手牌"""
        game = self.game_instances[group_id]
        player_ids = list(game.player_hands.keys())
        
        # 获取当前玩家和手牌索引
        current_player_id = player_ids[game.current_player_idx]
        current_hand_idx = game.current_hand_idx.get(current_player_id, 0)
        
        # 检查当前玩家是否还有其他待处理的手牌
        if current_hand_idx < len(game.player_hands[current_player_id]) - 1:
            # 如果当前手牌已经处理完毕，移动到下一副手牌
            if game.player_statuses[current_player_id][current_hand_idx] != "waiting":
                game.current_hand_idx[current_player_id] = current_hand_idx + 1
                
                # 查找下一个处于等待状态的手牌
                for i in range(current_hand_idx + 1, len(game.player_hands[current_player_id])):
                    if game.player_statuses[current_player_id][i] == "waiting":
                        game.current_hand_idx[current_player_id] = i
                        break
                
                # 获取当前玩家
                current_player = self.get_player(current_player_id)
                if current_player:
                    hand_idx = game.current_hand_idx[current_player_id]
                    hand_marker = f"手牌{hand_idx+1}" if len(game.player_hands[current_player_id]) > 1 else ""
                    return f"\n轮到 {current_player.nickname} {hand_marker}行动\n可选操作: 「要牌」「停牌」「加倍」"
                
                return ""
        
        # 如果当前玩家的所有手牌都已处理，移动到下一个玩家
        game.current_player_idx += 1
        
        # 检查是否还有等待行动的玩家
        remaining_players = False
        for i in range(game.current_player_idx, len(player_ids)):
            player_id = player_ids[i]
            # 检查该玩家是否有任何一副手牌处于等待状态
            for hand_idx, status in enumerate(game.player_statuses[player_id]):
                if status == "waiting":
                    remaining_players = True
                    game.current_player_idx = i
                    game.current_hand_idx[player_id] = hand_idx
                    break
            if remaining_players:
                break
                
        # 如果没有等待行动的玩家，进入庄家回合
        if not remaining_players:
            return self._dealer_turn(group_id)
            
        # 找到下一个玩家
        next_player_id = player_ids[game.current_player_idx]
        next_player = self.get_player(next_player_id)
        
        if next_player:
            hand_idx = game.current_hand_idx[next_player_id]
            hand_marker = f"手牌{hand_idx+1} " if len(game.player_hands[next_player_id]) > 1 else ""
            return f"\n轮到 {next_player.nickname} {hand_marker}行动\n可选操作: 「要牌」「停牌」「加倍」"
        return ""
        
    def _dealer_turn(self, group_id):
        """庄家回合"""
        game = self.game_instances[group_id]
        game.game_status = "dealer_turn"
        
        result = ["🎲 所有玩家已行动完毕", "————————————", "庄家回合开始"]
        
        # 揭示庄家底牌
        result.append(f"庄家手牌: {', '.join(str(card) for card in game.dealer_hand)}")
        result.append(f"点数: {game.calculate_hand_value(game.dealer_hand)}")
        
        # 庄家按规则要牌
        while game.calculate_hand_value(game.dealer_hand) < 17:
            new_card = game.deck.deal()
            game.dealer_hand.append(new_card)
            result.append(f"庄家要牌: {new_card}")
            
        # 显示庄家最终手牌
        dealer_value = game.calculate_hand_value(game.dealer_hand)
        result.append(f"\n庄家最终手牌: {', '.join(str(card) for card in game.dealer_hand)}")
        result.append(f"点数: {dealer_value}")
        
        # 判断胜负并结算
        result.append("\n🏆 结算结果:")
        
        # 找出庄家是否爆牌
        dealer_busted = dealer_value > 21
        dealer_blackjack = len(game.dealer_hand) == 2 and dealer_value == 21
        
        for player_id in game.player_hands:
            player = self.get_player(player_id)
            if not player:
                continue
                
            # 结算前记录玩家初始筹码
            initial_chips = player.chips
            
            # 处理该玩家的每一副手牌
            for hand_idx, hand in enumerate(game.player_hands[player_id]):
                player_value = game.calculate_hand_value(hand)
                bet_amount = game.player_bets[player_id][hand_idx]
                
                # 显示手牌标识（如果玩家有多副手牌）
                hand_marker = f"手牌{hand_idx+1} " if len(game.player_hands[player_id]) > 1 else ""
                
                # 玩家已经爆牌，之前已经处理，跳过
                if game.player_statuses[player_id][hand_idx] == "bust":
                    result.append(f"{player.nickname} {hand_marker}: 已爆牌，输掉 {bet_amount} 筹码")
                    continue
                    
                # 判断胜负
                is_blackjack = len(hand) == 2 and player_value == 21 and hand_idx == 0
                
                if is_blackjack and not dealer_blackjack:
                    # 玩家BlackJack，赔率3:2
                    winnings = int(bet_amount * 2.5)
                    player.chips += winnings
                    
                    current_wins = int(player.total_wins)
                    player.total_wins = str(current_wins + 1)
                    
                    result.append(f"{player.nickname} {hand_marker}: BlackJack! 赢得 {winnings} 筹码")
                    
                elif dealer_blackjack and not is_blackjack:
                    # 庄家BlackJack，玩家输
                    # 注意：玩家的筹码在下注时已经扣除，这里不需要再扣
                    
                    current_losses = int(player.total_losses)
                    player.total_losses = str(current_losses + 1)
                    
                    result.append(f"{player.nickname} {hand_marker}: 庄家BlackJack，输掉 {bet_amount} 筹码")
                    
                elif is_blackjack and dealer_blackjack:
                    # 双方都是BlackJack，平局
                    # 退还下注筹码
                    player.chips += bet_amount
                    
                    current_draws = int(player.total_draws)
                    player.total_draws = str(current_draws + 1)
                    
                    result.append(f"{player.nickname} {hand_marker}: 双方都是BlackJack，平局，退还下注 {bet_amount} 筹码")
                    
                elif dealer_busted:
                    # 庄家爆牌，玩家赢
                    player.chips += (bet_amount * 2)  # 返还原下注和赢得的等额筹码
                    
                    current_wins = int(player.total_wins)
                    player.total_wins = str(current_wins + 1)
                    
                    result.append(f"{player.nickname} {hand_marker}: 庄家爆牌，赢得 {bet_amount} 筹码")
                    
                elif player_value > dealer_value:
                    # 玩家点数大于庄家，玩家赢
                    player.chips += (bet_amount * 2)  # 返还原下注和赢得的等额筹码
                    
                    current_wins = int(player.total_wins)
                    player.total_wins = str(current_wins + 1)
                    
                    result.append(f"{player.nickname} {hand_marker}: {player_value}点 > 庄家{dealer_value}点，赢得 {bet_amount} 筹码")
                    
                elif player_value < dealer_value:
                    # 玩家点数小于庄家，玩家输
                    # 注意：玩家的筹码在下注时已经扣除，这里不需要再扣
                    
                    current_losses = int(player.total_losses)
                    player.total_losses = str(current_losses + 1)
                    if player.god:
                        player.data["chips"] = str(1000 + player.chips)
                    
                    result.append(f"{player.nickname} {hand_marker}: {player_value}点 < 庄家{dealer_value}点，输掉 {bet_amount} 筹码")
                    
                else:
                    # 点数相同，平局
                    # 退还下注筹码
                    player.chips += bet_amount
                    
                    current_draws = int(player.total_draws)
                    player.total_draws = str(current_draws + 1)
                    
                    result.append(f"{player.nickname} {hand_marker}: {player_value}点 = 庄家{dealer_value}点，平局，退还下注 {bet_amount} 筹码")
            
            # 如果玩家筹码有变化，保存到数据文件
            if player.chips != initial_chips:
                self._update_player_data(player_id, {'chips': str(player.chips)})
                
            # 显示玩家当前总筹码
            result.append(f"{player.nickname} 当前总筹码: {player.chips}")
        
        # 游戏结束，重置游戏状态
        self.game_instances[group_id] = BJGame()
        
        result.append("\n游戏结束，可以使用「21点准备」准备下一局游戏")
        return "\n".join(result)
        
    def show_game_state(self, user_id, group_id):
        """显示当前牌局状态"""
        if not group_id:
            return "21点游戏只能在群聊中进行，请在群聊中使用此指令"
            
        player = self.get_player(user_id)
        if not player:
            return "您还没有注册21点游戏，请先发送「21点注册」进行注册"
            
        # 检查游戏是否存在
        if group_id not in self.game_instances:
            return "当前没有正在进行的游戏"
            
        game = self.game_instances[group_id]
        
        # 生成游戏状态消息
        result = ["🃏 当前牌局状态", "————————————"]
        
        # 显示庄家的牌
        if game.game_status == "dealer_turn" or game.game_status == "finished":
            # 如果是庄家回合或游戏结束，显示所有庄家牌
            dealer_value = game.calculate_hand_value(game.dealer_hand)
            result.append(f"庄家 ({dealer_value}点): {', '.join(str(card) for card in game.dealer_hand)}")
        else:
            # 否则只显示明牌
            dealer_card = game.dealer_hand[0] if game.dealer_hand else "无"
            result.append(f"庄家明牌: {dealer_card}")
        
        # 显示每个玩家的手牌
        player_ids = list(game.player_hands.keys())
        for player_id in player_ids:
            p = self.get_player(player_id)
            if not p:
                continue
            
            # 处理玩家的所有手牌
            for hand_idx, hand in enumerate(game.player_hands[player_id]):
                if not hand:
                    continue
                    
                hand_value = game.calculate_hand_value(hand)
                bet_amount = game.player_bets[player_id][hand_idx]
                status = game.player_statuses[player_id][hand_idx]
                
                # 处理当前玩家的标记
                is_current = (game.game_status == "playing" and 
                             player_id == player_ids[game.current_player_idx] and
                             hand_idx == game.current_hand_idx.get(player_id, 0))
                current_mark = "➡️ " if is_current else ""
                
                # 显示手牌标识（如果玩家有多副手牌）
                hand_marker = f"手牌{hand_idx+1} " if len(game.player_hands[player_id]) > 1 else ""
                
                result.append(f"\n{current_mark}{p.nickname} {hand_marker}({hand_value}点)")
                result.append(f"下注: {bet_amount} 筹码")
                result.append(f"手牌: {', '.join(str(card) for card in hand)}")
                result.append(f"状态: {self._translate_status(status)}")
        
        # 显示游戏状态
        status_map = {
            "waiting": "等待开始",
            "betting": "下注阶段",
            "playing": "玩家回合",
            "dealer_turn": "庄家回合",
            "finished": "已结束"
        }
        
        result.append(f"\n当前状态: {status_map.get(game.game_status, game.game_status)}")
        
        # 如果是玩家回合，提示当前轮到谁
        if game.game_status == "playing" and player_ids and game.current_player_idx < len(player_ids):
            current_player_id = player_ids[game.current_player_idx]
            current_player = self.get_player(current_player_id)
            current_hand_idx = game.current_hand_idx.get(current_player_id, 0)
            
            if current_player:
                # 显示手牌标识（如果玩家有多副手牌）
                hand_marker = f"手牌{current_hand_idx+1} " if len(game.player_hands[current_player_id]) > 1 else ""
                
                result.append(f"轮到 {current_player.nickname} {hand_marker}行动")
                
                # 显示可用操作
                actions = ["要牌", "停牌"]
                # 检查是否可以加倍
                if len(game.player_hands[current_player_id][current_hand_idx]) == 2:
                    actions.append("加倍")
                # 检查是否可以分牌
                if game.can_split(current_player_id):
                    actions.append("分牌")
                    
                result.append(f"可选操作: 「{'」「'.join(actions)}」")
        
        return "\n".join(result)
        
    def _translate_status(self, status):
        """翻译玩家状态为中文"""
        status_map = {
            "waiting": "等待行动",
            "stand": "已停牌",
            "bust": "已爆牌"
        }
        return status_map.get(status, status)
        
    def reset_blackjack_game(self, user_id, group_id):
        """清理游戏数据"""
        if group_id and group_id in self.game_instances:
            self.game_instances[group_id] = BJGame()
            if group_id in self.ready_players:
                self.ready_players[group_id] = []
            return "🧹 21点游戏数据已清理完成，可以重新开始游戏"
        elif not group_id:
            return "清理命令只能在群聊中使用"
        else:
            return "当前没有进行中的21点游戏"
        
    def reset_all_data(self, session_id, user_id):
        """重置所有玩家数据和排行榜"""
        # 只有管理员才能执行此操作
        try:
            # 管理员ID可以在这里设置，此处简单使用首个调用此命令的用户作为管理员
            # 实际应用中建议使用配置文件或更安全的方式存储管理员ID
            admin_file = os.path.join(self.data_dir, "bjadmin.txt")
            if os.path.exists(admin_file):
                with open(admin_file, 'r', encoding='utf-8') as f:
                    admin_id = f.read().strip()
                if user_id != admin_id:
                    return "⚠️ 只有管理员才能执行重置操作"
            else:
                # 如果管理员文件不存在，将当前用户设为管理员
                with open(admin_file, 'w', encoding='utf-8') as f:
                    f.write(user_id)
                admin_id = user_id
                logger.info(f"[BlackJack] 设置新管理员: {user_id}")
                
            # 备份当前数据
            if os.path.exists(self.player_file):
                backup_file = os.path.join(self.data_dir, f"bjplayers_backup_{int(time.time())}.csv")
                with open(self.player_file, 'r', encoding='utf-8') as src:
                    with open(backup_file, 'w', encoding='utf-8') as dst:
                        dst.write(src.read())
                logger.info(f"[BlackJack] 已备份玩家数据到: {backup_file}")
            
            # 重置玩家数据文件
            with open(self.player_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.STANDARD_FIELDS)
                writer.writeheader()
            
            # 重置游戏状态
            self.game_instances = {}
            self.ready_players = {}
            
            return "🔄 BlackJack(21点)游戏数据已完全重置！\n所有玩家数据和排行榜已清空，玩家需要重新注册才能继续游戏。"
        except Exception as e:
            logger.error(f"[BlackJack] 重置游戏数据出错: {e}")
            return f"重置数据时出错: {e}"
        
    def show_debug_status(self, user_id, group_id):
        """显示调试用的游戏状态信息"""
        if not group_id:
            return "此命令只能在群聊中使用"
            
        if group_id not in self.game_instances:
            return "当前没有正在进行的游戏"
            
        game = self.game_instances[group_id]
        
        debug_info = ["🔍 BlackJack游戏调试信息", "————————————"]
        
        # 游戏基本状态
        debug_info.append(f"游戏状态: {game.game_status}")
        debug_info.append(f"当前玩家索引: {game.current_player_idx}")
        debug_info.append(f"牌组剩余: {game.deck.remaining()}张")
        
        # 玩家顺序
        if hasattr(game, 'players_order'):
            debug_info.append("\n玩家顺序:")
            for i, player_id in enumerate(game.players_order):
                player = self.get_player(player_id)
                nickname = player.nickname if player else player_id
                current_mark = "➡️ " if i == game.current_player_idx else ""
                current_hand_idx = game.current_hand_idx.get(player_id, 0)
                debug_info.append(f"{i}. {current_mark}{nickname} (当前手牌索引: {current_hand_idx})")
        
        # 玩家手牌
        debug_info.append("\n玩家手牌:")
        for player_id in game.player_hands:
            player = self.get_player(player_id)
            nickname = player.nickname if player else player_id
            
            for hand_idx, hand in enumerate(game.player_hands[player_id]):
                hand_value = game.calculate_hand_value(hand)
                hand_marker = f"手牌{hand_idx+1}" if len(game.player_hands[player_id]) > 1 else ""
                debug_info.append(f"- {nickname} {hand_marker} ({hand_value}点): {', '.join(str(card) for card in hand)}")
            
        # 玩家下注
        debug_info.append("\n玩家下注:")
        for player_id in game.player_bets:
            player = self.get_player(player_id)
            nickname = player.nickname if player else player_id
            
            for hand_idx, bet in enumerate(game.player_bets[player_id]):
                hand_marker = f"手牌{hand_idx+1}" if len(game.player_bets[player_id]) > 1 else ""
                debug_info.append(f"- {nickname} {hand_marker}: {bet}")
            
        # 玩家状态
        if hasattr(game, 'player_statuses'):
            debug_info.append("\n玩家状态:")
            for player_id in game.player_statuses:
                player = self.get_player(player_id)
                nickname = player.nickname if player else player_id
                
                for hand_idx, status in enumerate(game.player_statuses[player_id]):
                    hand_marker = f"手牌{hand_idx+1}" if len(game.player_statuses[player_id]) > 1 else ""
                    debug_info.append(f"- {nickname} {hand_marker}: {status}")
        
        # 庄家手牌
        debug_info.append("\n庄家手牌:")
        dealer_value = game.calculate_hand_value(game.dealer_hand)
        debug_info.append(f"({dealer_value}点): {', '.join(str(card) for card in game.dealer_hand)}")
        
        return "\n".join(debug_info)
        
    def split(self, user_id, group_id):
        """玩家分牌"""
        if not group_id:
            return "21点游戏只能在群聊中进行，请在群聊中使用此指令"
            
        player = self.get_player(user_id)
        if not player:
            return "您还没有注册21点游戏，请先发送「21点注册」进行注册"
            
        # 检查游戏是否存在
        if group_id not in self.game_instances:
            return "当前没有正在进行的游戏"
            
        game = self.game_instances[group_id]
        
        # 检查游戏状态
        if game.game_status != "playing":
            return "当前不是玩家行动阶段"
            
        # 检查是否轮到该玩家
        player_ids = list(game.player_hands.keys())
        player_index = player_ids.index(user_id) if user_id in player_ids else -1
        if player_index != game.current_player_idx:
            current_player_id = player_ids[game.current_player_idx]
            current_player = self.get_player(current_player_id)
            return f"当前轮到 {current_player.nickname} 行动，请等待您的回合"
            
        # 获取当前手牌索引
        hand_idx = game.current_hand_idx[user_id]
        
        # 检查玩家筹码是否足够进行分牌
        current_bet = game.player_bets[user_id][hand_idx]
        if player.chips < current_bet:
            return f"分牌失败，您的筹码不足\n当前筹码: {player.chips}\n所需筹码: {current_bet}"
            
        # 检查是否可以分牌
        if not game.can_split(user_id):
            hand = game.player_hands[user_id][hand_idx]
            if len(hand) != 2:
                return "只有持有两张牌时才能分牌"
            return "分牌失败，只有点数相同的两张牌才能分牌"
            
        # 执行分牌
        success = game.split(user_id)
        if not success:
            return "分牌失败，请稍后再试"
            
        # 更新玩家数据（扣除额外的下注金额）
        new_chips = player.chips - current_bet
        self._update_player_data(user_id, {'chips': str(new_chips)})
        
        # 获取分牌后的两手牌
        original_hand = game.player_hands[user_id][hand_idx]
        new_hand = game.player_hands[user_id][-1]
        
        # 计算点数
        original_value = game.calculate_hand_value(original_hand)
        new_value = game.calculate_hand_value(new_hand)
        
        result = [f"🃏 {player.nickname} 选择分牌!"]
        result.append(f"手牌1 ({original_value}点): {', '.join(str(card) for card in original_hand)}")
        result.append(f"手牌2 ({new_value}点): {', '.join(str(card) for card in new_hand)}")
        result.append(f"每手牌下注: {current_bet} 筹码")
        result.append(f"总下注: {current_bet * 2} 筹码")
        result.append("\n现在请继续操作第一手牌...")
        
        return "\n".join(result) 