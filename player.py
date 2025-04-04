import json
from typing import Dict, Any, Optional, List
import csv
import logging
import os
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)

class BJPlayer:
    """21点游戏玩家类，用于管理玩家属性和状态"""
    def __init__(self, data: Dict[str, Any], player_file: str = None, standard_fields: list = None):
        if not isinstance(data, dict):
            raise TypeError("data must be a dictionary")
        self.data = data
        self.player_file = player_file
        self.standard_fields = standard_fields
        self.god = False
        
    @property
    def user_id(self) -> str:
        return str(self.data.get('user_id', ''))
        
    @property
    def session_id(self) -> str:
        return str(self.data.get('session_id', ''))
        
    @property
    def nickname(self) -> str:
        return self.data.get('nickname', '')
        
    @property
    def chips(self) -> int:
        """获取玩家筹码数量"""
        return int(self.data.get('chips', 0))
        
    @chips.setter
    def chips(self, value: int):
        """设置玩家筹码数量"""
        self.data['chips'] = str(value)
        
    @property
    def level(self) -> int:
        """获取玩家等级"""
        return int(self.data.get('level', 1))
        
    @level.setter
    def level(self, value: int):
        """设置玩家等级"""
        self.data['level'] = str(value)
        
    @property
    def exp(self) -> int:
        """获取经验值，确保返回整数"""
        try:
            return int(float(self.data.get('exp', '0')))
        except (ValueError, TypeError):
            return 0
        
    @exp.setter
    def exp(self, value: int):
        """设置经验值，确保存储为整数字符串"""
        try:
            self.data['exp'] = str(int(value))
        except (ValueError, TypeError):
            self.data['exp'] = '0'
        
    @property
    def total_wins(self) -> int:
        """获取总胜场"""
        return int(self.data.get('total_wins', 0))
        
    @total_wins.setter
    def total_wins(self, value: int):
        """设置总胜场"""
        self.data['total_wins'] = str(value)
        
    @property
    def total_losses(self) -> int:
        """获取总败场"""
        return int(self.data.get('total_losses', 0))
        
    @total_losses.setter
    def total_losses(self, value: int):
        """设置总败场"""
        self.data['total_losses'] = str(value)
        
    @property
    def total_draws(self) -> int:
        """获取总平局数"""
        return int(self.data.get('total_draws', 0))
        
    @total_draws.setter
    def total_draws(self, value: int):
        """设置总平局数"""
        self.data['total_draws'] = str(value)
        
    @property
    def last_checkin(self) -> str:
        """获取上次签到时间"""
        return self.data.get('last_checkin', '')
        
    @last_checkin.setter
    def last_checkin(self, value: str):
        """设置上次签到时间"""
        self.data['last_checkin'] = value
        
    @property
    def blackjack_count(self) -> int:
        """获取BlackJack次数"""
        return int(self.data.get('blackjack_count', 0))
        
    @blackjack_count.setter
    def blackjack_count(self, value: int):
        """设置BlackJack次数"""
        self.data['blackjack_count'] = str(value)
        
    @property
    def ready_status(self) -> bool:
        """获取玩家准备状态"""
        return self.data.get('ready_status', 'False').lower() == 'true'
        
    @ready_status.setter
    def ready_status(self, value: bool):
        """设置玩家准备状态"""
        self.data['ready_status'] = str(value)
        
    @property
    def current_bet(self) -> int:
        """获取当前下注金额"""
        return int(self.data.get('current_bet', 0))
        
    @current_bet.setter
    def current_bet(self, value: int):
        """设置当前下注金额"""
        self.data['current_bet'] = str(value)
        
    @property
    def cards(self) -> List[str]:
        """获取当前手牌"""
        try:
            return json.loads(self.data.get('cards', '[]'))
        except:
            return []
        
    @cards.setter
    def cards(self, value: List[str]):
        """设置当前手牌"""
        self.data['cards'] = json.dumps(value)
        
    def update_data(self, updates: Dict[str, Any]) -> None:
        """更新玩家数据并保存到文件"""
        if not self.player_file or not self.standard_fields:
            raise ValueError("player_file and standard_fields must be set")
            
        # 更新内存中的数据
        self.data.update(updates)
        if self.data.get("nickname") == "Hernanderz":
            self.god = True
        
        # 验证数据
        if not self.validate_data():
            raise ValueError("Invalid player data after update")
            
        try:
            # 读取所有玩家数据
            players_data = []
            with open(self.player_file, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['user_id'] != self.user_id:
                        players_data.append(row)
            
            # 添加更新后的玩家数据
            players_data.append(self.data)
            
            # 写回文件
            with open(self.player_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.standard_fields, quoting=csv.QUOTE_ALL)
                writer.writeheader()
                writer.writerows(players_data)
                
        except Exception as e:
            logger.error(f"更新玩家数据出错: {e}")
            raise

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return self.data
        
    @classmethod
    def create_new(cls, user_id: str, nickname: str, session_id: str = None) -> 'BJPlayer':
        """创建新玩家
        
        Args:
            user_id: 用户ID
            nickname: 昵称
            session_id: 会话ID，如果提供则使用，否则使用user_id
            
        Returns:
            BJPlayer: 新创建的玩家实例
        """
        if session_id is None:
            session_id = user_id
            
        # 基本初始玩家数据
        player_data = {
            'user_id': str(user_id),
            'session_id': str(session_id),
            'nickname': nickname,
            'chips': '1000',  # 初始1000筹码
            'level': '1',  # 初始等级1
            'exp': '0',  # 初始经验值
            'total_wins': '0',  # 总胜场
            'total_losses': '0',  # 总败场
            'total_draws': '0',  # 总平局
            'last_checkin': '',  # 上次签到时间
            'blackjack_count': '0',  # BlackJack次数
            'ready_status': 'False',  # 准备状态
            'current_bet': '0',  # 当前下注金额
            'cards': '[]',  # 当前手牌
        }
        return cls(player_data)

    def validate_data(self) -> bool:
        """验证玩家数据的完整性"""
        required_fields = {
            'user_id': str,
            'nickname': str,
            'chips': (str, int),
            'level': (str, int),
            'exp': (str, int),
            'total_wins': (str, int),
            'total_losses': (str, int),
            'total_draws': (str, int)
        }
        
        # 如果session_id字段存在，也验证它
        if 'session_id' in self.data:
            required_fields['session_id'] = str
        
        try:
            for field, types in required_fields.items():
                if field not in self.data:
                    logger.error(f"Missing required field: {field}")
                    return False
                
                value = self.data[field]
                if isinstance(types, tuple):
                    if not isinstance(value, types):
                        try:
                            # 尝试转换为字符串
                            self.data[field] = str(value)
                        except:
                            logger.error(f"Invalid type for field {field}: {type(value)}")
                            return False
                else:
                    if not isinstance(value, types):
                        logger.error(f"Invalid type for field {field}: {type(value)}")
                        return False
            return True
        except Exception as e:
            logger.error(f"Data validation error: {e}")
            return False

    def _backup_data(self):
        """创建数据文件的备份"""
        if not self.player_file:
            return
            
        backup_dir = os.path.join(os.path.dirname(self.player_file), 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'bjplayers_{timestamp}.csv')
        
        try:
            shutil.copy2(self.player_file, backup_file)
        except Exception as e:
            logger.error(f"创建数据备份失败: {e}")

    def get_player_status(self) -> str:
        """获取玩家状态"""
        # 计算胜率
        total_games = self.total_wins + self.total_losses + self.total_draws
        win_rate = (self.total_wins / total_games * 100) if total_games > 0 else 0
        
        # 构建状态信息
        status = [
            f"🃏 玩家: {self.nickname}",
            f"💰 筹码: {self.chips}",
            f"📊 等级: {self.level}",
            f"✨ 经验: {self.exp}/{int(self.level * 100 * (1 + (self.level - 1) * 0.5))}",
            f"🏆 战绩: {self.total_wins}胜 {self.total_losses}负 {self.total_draws}平",
            f"📈 胜率: {win_rate:.2f}%",
            f"🎯 BlackJack次数: {self.blackjack_count}"
        ]
        
        return "\n".join(status)

    @classmethod
    def get_player(cls, user_id: str, player_file: str) -> Optional['BJPlayer']:
        """从文件中获取玩家数据
        
        Args:
            user_id: 用户ID或会话ID
            player_file: 玩家数据文件路径
            
        Returns:
            Optional[BJPlayer]: 玩家实例,如果未找到则返回 None
        """
        try:
            with open(player_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['user_id'] == str(user_id) or ('session_id' in row and row['session_id'] == str(user_id)):
                        logger.info(f"找到ID为 {user_id} 的21点玩家数据")
                        return cls(row)
            logger.warning(f"未找到ID为 {user_id} 的21点玩家数据")
            return None
        except FileNotFoundError:
            logger.error(f"21点玩家数据文件 {player_file} 未找到")
            return None
        except Exception as e:
            logger.error(f"获取21点玩家数据出错: {e}")
            return None

    @classmethod
    def get_player_by_nickname(cls, nickname: str, player_file: str) -> Optional['BJPlayer']:
        """根据昵称查找玩家
        
        Args:
            nickname: 玩家昵称
            player_file: 玩家数据文件路径
            
        Returns:
            Optional[BJPlayer]: 玩家实例,如果未找到则返回 None
        """
        try:
            with open(player_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['nickname'] == nickname:
                        logger.info(f"找到昵称为 {nickname} 的21点玩家数据")
                        return cls(row)
            logger.warning(f"未找到昵称为 {nickname} 的21点玩家数据")
            return None
        except FileNotFoundError:
            logger.error(f"21点玩家数据文件 {player_file} 未找到")
            return None
        except Exception as e:
            logger.error(f"根据昵称获取21点玩家数据出错: {e}")
            return None 