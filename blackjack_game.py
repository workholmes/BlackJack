import random
from typing import List, Dict, Tuple, Any, Optional

class Card:
    """扑克牌类"""
    SUITS = ['♠', '♥', '♦', '♣']
    RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    
    def __init__(self, suit: str, rank: str):
        self.suit = suit
        self.rank = rank
        
    def __str__(self) -> str:
        return f"{self.suit}{self.rank}"
    
    def get_value(self) -> int:
        """获取牌的点数"""
        if self.rank in ['J', 'Q', 'K']:
            return 10
        elif self.rank == 'A':
            return 11  # Ace默认值为11，计算总点数时如果超过21会当作1
        else:
            return int(self.rank)

class Deck:
    """牌组类"""
    def __init__(self, num_decks: int = 6):
        """初始化牌组，默认使用6副牌"""
        self.cards: List[Card] = []
        for _ in range(num_decks):
            for suit in Card.SUITS:
                for rank in Card.RANKS:
                    self.cards.append(Card(suit, rank))
        self.shuffle()
        
    def shuffle(self):
        """洗牌"""
        random.shuffle(self.cards)
        
    def deal(self) -> Optional[Card]:
        """发牌"""
        if len(self.cards) > 0:
            return self.cards.pop()
        return None
    
    def remaining(self) -> int:
        """获取剩余牌的数量"""
        return len(self.cards)

class BJGame:
    """21点游戏类"""
    def __init__(self):
        """初始化游戏"""
        self.deck = Deck()
        self.player_hands: Dict[str, List[List[Card]]] = {}  # 玩家ID -> [手牌列表1, 手牌列表2, ...]
        self.dealer_hand: List[Card] = []  # 庄家手牌
        self.player_bets: Dict[str, List[int]] = {}  # 玩家ID -> [下注金额1, 下注金额2, ...]
        self.player_statuses: Dict[str, List[str]] = {}  # 玩家ID -> [状态1, 状态2, ...] （等待、要牌、停牌、爆牌）
        self.game_status = "waiting"  # 游戏状态：waiting, betting, playing, dealer_turn, finished
        self.current_player_idx = 0  # 当前玩家索引
        self.current_hand_idx: Dict[str, int] = {}  # 玩家ID -> 当前手牌索引
        self.players_order: List[str] = []  # 玩家顺序列表
        
    def start_new_game(self, player_ids: List[str]):
        """开始新游戏
        
        Args:
            player_ids: 参与游戏的玩家ID列表
        """
        # 重置游戏状态
        self.player_hands = {pid: [[]] for pid in player_ids}
        self.dealer_hand = []
        self.player_bets = {pid: [0] for pid in player_ids}
        self.player_statuses = {pid: ["waiting"] for pid in player_ids}
        self.current_hand_idx = {pid: 0 for pid in player_ids}
        self.game_status = "betting"
        self.current_player_idx = 0
        self.players_order = player_ids.copy()
        
        # 如果牌组剩余不足一半，重新洗牌
        if self.deck.remaining() < (52 * 6 // 2):
            self.deck = Deck()
            
    def place_bet(self, player_id: str, amount: int) -> bool:
        """玩家下注
        
        Args:
            player_id: 玩家ID
            amount: 下注金额
            
        Returns:
            bool: 下注是否成功
        """
        if self.game_status != "betting" or player_id not in self.player_hands:
            return False
            
        self.player_bets[player_id][0] = amount
        return True
        
    def deal_initial_cards(self):
        """发初始牌"""
        if self.game_status != "betting":
            return False
            
        # 检查是否所有玩家都已下注
        if any(bet[0] == 0 for bet in self.player_bets.values()):
            return False
            
        # 发牌：每个玩家2张牌，庄家2张牌
        for player_id in self.players_order:
            self.player_hands[player_id][0].append(self.deck.deal())
            self.player_hands[player_id][0].append(self.deck.deal())
            
        self.dealer_hand.append(self.deck.deal())
        self.dealer_hand.append(self.deck.deal())
        
        self.game_status = "playing"
        return True
        
    def hit(self, player_id: str) -> Tuple[bool, Optional[Card], int, bool]:
        """玩家要牌
        
        Args:
            player_id: 玩家ID
            
        Returns:
            Tuple[bool, Card, int, bool]: (是否操作成功, 获得的牌, 当前点数, 是否爆牌)
        """
        if (self.game_status != "playing" or 
            player_id not in self.player_hands or
            self.players_order[self.current_player_idx] != player_id):
            return (False, None, 0, False)
            
        # 获取当前手牌索引
        hand_idx = self.current_hand_idx[player_id]
        
        # 检查状态
        if self.player_statuses[player_id][hand_idx] != "waiting":
            return (False, None, 0, False)
            
        # 发一张牌
        new_card = self.deck.deal()
        self.player_hands[player_id][hand_idx].append(new_card)
        
        # 计算点数
        hand_value = self.calculate_hand_value(self.player_hands[player_id][hand_idx])
        
        # 检查是否爆牌
        is_bust = hand_value > 21
        if is_bust:
            self.player_statuses[player_id][hand_idx] = "bust"
            
        return (True, new_card, hand_value, is_bust)
        
    def stand(self, player_id: str) -> bool:
        """玩家停牌
        
        Args:
            player_id: 玩家ID
            
        Returns:
            bool: 是否操作成功
        """
        if (self.game_status != "playing" or 
            player_id not in self.player_hands or
            self.players_order[self.current_player_idx] != player_id):
            return False
            
        # 获取当前手牌索引
        hand_idx = self.current_hand_idx[player_id]
        
        # 检查状态
        if self.player_statuses[player_id][hand_idx] != "waiting":
            return False
            
        self.player_statuses[player_id][hand_idx] = "stand"
        return True
        
    def double_down(self, player_id: str) -> Tuple[bool, Optional[Card], int, bool]:
        """玩家加倍
        
        Args:
            player_id: 玩家ID
            
        Returns:
            Tuple[bool, Card, int, bool]: (是否操作成功, 获得的牌, 当前点数, 是否爆牌)
        """
        if (self.game_status != "playing" or 
            player_id not in self.player_hands or
            self.players_order[self.current_player_idx] != player_id):
            return (False, None, 0, False)
            
        # 获取当前手牌索引
        hand_idx = self.current_hand_idx[player_id]
        
        # 检查状态和手牌
        if (self.player_statuses[player_id][hand_idx] != "waiting" or
            len(self.player_hands[player_id][hand_idx]) != 2):  # 只能在拿到两张牌时加倍
            return (False, None, 0, False)
            
        # 加倍下注
        self.player_bets[player_id][hand_idx] *= 2
        
        # 只发一张牌然后停牌
        new_card = self.deck.deal()
        self.player_hands[player_id][hand_idx].append(new_card)
        
        # 计算点数
        hand_value = self.calculate_hand_value(self.player_hands[player_id][hand_idx])
        
        # 检查是否爆牌
        is_bust = hand_value > 21
        if is_bust:
            self.player_statuses[player_id][hand_idx] = "bust"
        else:
            self.player_statuses[player_id][hand_idx] = "stand"
            
        return (True, new_card, hand_value, is_bust)
        
    def split(self, player_id: str) -> bool:
        """玩家分牌
        
        Args:
            player_id: 玩家ID
            
        Returns:
            bool: 是否操作成功
        """
        if (self.game_status != "playing" or 
            player_id not in self.player_hands or
            self.players_order[self.current_player_idx] != player_id):
            return False
            
        # 获取当前手牌索引
        hand_idx = self.current_hand_idx[player_id]
        
        # 检查状态和手牌
        if (self.player_statuses[player_id][hand_idx] != "waiting" or
            len(self.player_hands[player_id][hand_idx]) != 2):
            return False
            
        # 检查两张牌是否点数相同（对子）
        hand = self.player_hands[player_id][hand_idx]
        if hand[0].get_value() != hand[1].get_value():
            return False
            
        # 创建新的手牌
        new_hand = [hand.pop()]
        self.player_hands[player_id].append(new_hand)
        
        # 为每手牌各发一张新牌
        self.player_hands[player_id][hand_idx].append(self.deck.deal())
        self.player_hands[player_id][-1].append(self.deck.deal())
        
        # 复制下注金额
        current_bet = self.player_bets[player_id][hand_idx]
        self.player_bets[player_id].append(current_bet)
        
        # 设置状态
        self.player_statuses[player_id].append("waiting")
        
        return True
        
    def _advance_to_next_player(self):
        """移动到下一个玩家或下一副手牌"""
        player_id = self.players_order[self.current_player_idx]
        hand_idx = self.current_hand_idx[player_id]
        
        # 检查当前玩家是否还有其他待处理的手牌
        if hand_idx < len(self.player_hands[player_id]) - 1:
            # 移动到该玩家的下一副手牌
            self.current_hand_idx[player_id] += 1
            return
            
        # 如果当前玩家的所有手牌都已处理，移动到下一个玩家
        self.current_player_idx += 1
        
        # 跳过已完成操作的玩家
        while (self.current_player_idx < len(self.players_order)):
            next_player_id = self.players_order[self.current_player_idx]
            # 检查该玩家是否有任何一副手牌处于等待状态
            if any(status == "waiting" for status in self.player_statuses[next_player_id]):
                self.current_hand_idx[next_player_id] = 0  # 重置手牌索引
                # 找到第一副等待状态的手牌
                for i, status in enumerate(self.player_statuses[next_player_id]):
                    if status == "waiting":
                        self.current_hand_idx[next_player_id] = i
                        break
                return
            self.current_player_idx += 1
            
        # 如果所有玩家都已完成，轮到庄家
        if self.current_player_idx >= len(self.players_order):
            self._dealer_turn()
        
    def _dealer_turn(self):
        """庄家回合"""
        self.game_status = "dealer_turn"
        
        # 庄家按规则要牌：少于17点必须要牌，17点或以上必须停牌
        while self.calculate_hand_value(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deck.deal())
            
        self._determine_winners()
        
    def _determine_winners(self):
        """确定胜负并结算"""
        self.game_status = "finished"
        results = {}
        
        dealer_value = self.calculate_hand_value(self.dealer_hand)
        dealer_busted = dealer_value > 21
        dealer_blackjack = len(self.dealer_hand) == 2 and dealer_value == 21
        
        for player_id in self.players_order:
            results[player_id] = []
            
            for hand_idx, hand in enumerate(self.player_hands[player_id]):
                bet = self.player_bets[player_id][hand_idx]
                player_value = self.calculate_hand_value(hand)
                
                # 玩家已经爆牌
                if self.player_statuses[player_id][hand_idx] == "bust":
                    results[player_id].append({
                        "outcome": "lose",
                        "winnings": -bet,
                        "blackjack": False
                    })
                    continue
                
                # 检查BlackJack (只有原始手牌才能构成BlackJack)
                is_blackjack = len(hand) == 2 and player_value == 21 and hand_idx == 0
                
                if is_blackjack and not dealer_blackjack:
                    # 玩家BlackJack，庄家不是，赔率3:2
                    results[player_id].append({
                        "outcome": "blackjack",
                        "winnings": int(bet * 1.5),
                        "blackjack": True
                    })
                elif dealer_blackjack and not is_blackjack:
                    # 庄家BlackJack，玩家不是
                    results[player_id].append({
                        "outcome": "lose",
                        "winnings": -bet,
                        "blackjack": False
                    })
                elif is_blackjack and dealer_blackjack:
                    # 双方都是BlackJack，平局
                    results[player_id].append({
                        "outcome": "push",
                        "winnings": 0,
                        "blackjack": True
                    })
                elif dealer_busted:
                    # 庄家爆牌，玩家胜
                    results[player_id].append({
                        "outcome": "win",
                        "winnings": bet,
                        "blackjack": False
                    })
                elif player_value > dealer_value:
                    # 玩家点数大于庄家，玩家胜
                    results[player_id].append({
                        "outcome": "win",
                        "winnings": bet,
                        "blackjack": False
                    })
                elif player_value < dealer_value:
                    # 玩家点数小于庄家，庄家胜
                    results[player_id].append({
                        "outcome": "lose",
                        "winnings": -bet,
                        "blackjack": False
                    })
                else:
                    # 平局
                    results[player_id].append({
                        "outcome": "push",
                        "winnings": 0,
                        "blackjack": False
                    })
                
        return results
        
    def calculate_hand_value(self, hand: List[Card]) -> int:
        """计算手牌点数
        
        Args:
            hand: 手牌列表
            
        Returns:
            int: 手牌点数
        """
        value = 0
        aces = 0
        
        for card in hand:
            if card.rank == 'A':
                aces += 1
                value += 11
            else:
                value += card.get_value()
        
        # 如果点数超过21且有A，则将A当作1点计算
        while value > 21 and aces > 0:
            value -= 10  # 11 - 1 = 10
            aces -= 1
            
        return value
        
    def get_dealer_first_card(self) -> Optional[Card]:
        """获取庄家的第一张牌（明牌）"""
        if len(self.dealer_hand) > 0:
            return self.dealer_hand[0]
        return None
        
    def get_player_hand(self, player_id: str, hand_idx: int = 0) -> List[Card]:
        """获取玩家手牌
        
        Args:
            player_id: 玩家ID
            hand_idx: 手牌索引，默认为0
            
        Returns:
            List[Card]: 手牌列表
        """
        if player_id in self.player_hands and hand_idx < len(self.player_hands[player_id]):
            return self.player_hands[player_id][hand_idx]
        return []
        
    def get_player_hand_value(self, player_id: str, hand_idx: int = 0) -> int:
        """获取玩家手牌点数
        
        Args:
            player_id: 玩家ID
            hand_idx: 手牌索引，默认为0
            
        Returns:
            int: 手牌点数
        """
        if player_id in self.player_hands and hand_idx < len(self.player_hands[player_id]):
            return self.calculate_hand_value(self.player_hands[player_id][hand_idx])
        return 0
        
    def get_dealer_hand(self) -> List[Card]:
        """获取庄家手牌"""
        return self.dealer_hand
        
    def get_dealer_hand_value(self) -> int:
        """获取庄家手牌点数"""
        return self.calculate_hand_value(self.dealer_hand)
        
    def get_current_player(self) -> Optional[str]:
        """获取当前玩家ID"""
        if 0 <= self.current_player_idx < len(self.players_order):
            return self.players_order[self.current_player_idx]
        return None
        
    def get_current_hand_idx(self, player_id: str) -> int:
        """获取当前玩家的手牌索引"""
        return self.current_hand_idx.get(player_id, 0)
        
    def is_player_turn(self, player_id: str) -> bool:
        """检查是否是指定玩家的回合"""
        if (self.game_status != "playing" or 
            self.get_current_player() != player_id):
            return False
            
        hand_idx = self.current_hand_idx.get(player_id, 0)
        if hand_idx >= len(self.player_statuses.get(player_id, [])):
            return False
            
        return self.player_statuses[player_id][hand_idx] == "waiting"
        
    def can_split(self, player_id: str) -> bool:
        """检查玩家是否可以分牌"""
        if not self.is_player_turn(player_id):
            return False
            
        hand_idx = self.current_hand_idx[player_id]
        hand = self.player_hands[player_id][hand_idx]
        
        # 检查是否只有两张牌且点数相同
        return (len(hand) == 2 and 
                hand[0].get_value() == hand[1].get_value())
                
    def format_card(self, card: Card) -> str:
        """格式化扑克牌显示"""
        return f"{card.suit}{card.rank}"
        
    def format_hand(self, hand: List[Card]) -> str:
        """格式化手牌显示"""
        return " ".join([self.format_card(card) for card in hand])
        
    def format_dealer_hand(self, show_hole_card: bool = False) -> str:
        """格式化庄家手牌显示
        
        Args:
            show_hole_card: 是否显示底牌
            
        Returns:
            str: 格式化的庄家手牌
        """
        if not self.dealer_hand:
            return ""
            
        if show_hole_card or self.game_status in ["dealer_turn", "finished"]:
            return self.format_hand(self.dealer_hand)
        else:
            # 只显示第一张牌，第二张以后显示为背面
            return f"{self.format_card(self.dealer_hand[0])} 🂠" 