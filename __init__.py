# BlackJack游戏插件
import os
import sys

# 添加当前目录到Python模块搜索路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 导出插件
from .blackjack import BlackJack 