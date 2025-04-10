![Logo](logo.png)

# BlackJack 21点游戏插件

![Version](https://img.shields.io/badge/version-0.2.6-blue.svg)

适用于 LLM-App-Starter 框架的 21 点游戏插件。

## 特性

- 支持多玩家同时游戏
- 带有筹码管理系统
- 玩家等级系统
- 每日签到奖励
- 排行榜功能
- 支持拆牌（Split）
- 支持加倍（Double Down）

## 命令

| 命令 | 说明 |
|-----|-----|
| `BlackJack注册 <昵称>` 或 `21点注册 <昵称>` | 注册玩家，指定昵称 |
| `查看BlackJack排行榜` 或 `查看21点排行榜` | 显示玩家排行榜 |
| `BlackJack签到` 或 `21点签到` | 进行每日签到获得筹码 |
| `BlackJack状态` 或 `21点状态` | 查看玩家当前状态 |
| `BlackJack准备` 或 `21点准备` | 准备开始游戏 |
| `开始BlackJack` 或 `开始21点` | 开始一局新游戏 |
| `下注 <数量>` | 下注指定数量的筹码 |
| `要牌` | 再要一张牌 |
| `停牌` | 停止要牌，保持当前手牌 |
| `加倍` | 将赌注翻倍并再要一张牌，然后自动停牌 |
| `拆牌` | 当持有两张相同点数的牌时，可以拆分成两手牌 |
| `BJStatus` | 显示当前游戏详细状态（调试用） |
| `清理BlackJack` 或 `清理21点` | 清理当前游戏（当游戏状态出错时使用） |
| `重置BlackJack` 或 `重置21点` | 重置所有玩家数据和排行榜 |

## 规则

- 玩家初始获得 1000 筹码
- 庄家在点数小于17时必须要牌
- 21点（BlackJack）给予 1.5 倍赔率
- 玩家可以在只有两张牌时选择加倍（Double Down）
- 拥有两张相同点数的牌时可以选择拆牌（Split）
- 拆牌后的每手牌单独计算，各自可以继续要牌或停牌

## 更新记录

### v0.2.6 (2025-04-11)
- 修复了"要牌"命令中的参数错误问题，确保游戏流程能够正常继续
- 优化了命令处理逻辑，使参数传递更加一致

### v0.2.5 (2025-04-05)
- 修复了战绩重复计算的问题
- 优化了玩家在爆牌后的战绩统计逻辑，确保每局游戏只记录一次输赢结果
- 完善了多手牌情况下的统计机制，避免重复计数

### v0.2.4 (2025-04-04)
- 修复了统计错误问题，避免输局被重复计算
- 优化了爆牌后更新统计的逻辑，确保每局游戏结果只记录一次
- 完善了多手牌情况下的统计准确性

### v0.2.3 (2025-04-03)
- 改进了拆牌功能的显示效果，现在所有手牌状态都能正确显示
- 优化了停牌操作的反馈信息，显示所有手牌及其状态
- 修复了初始发牌时的一个bug，确保测试时更容易成功拆牌

### v0.2.2 (2025-04-02)
- 新增了游戏状态显示命令 `BJStatus`，用于调试和查看详细游戏状态
- 完善了玩家顺序显示功能，使用箭头标记当前玩家
- 优化了手牌显示格式，增加手牌点数和状态信息

### v0.2.1 (2025-04-01) 
- 新增了拆牌(Split)功能，允许玩家将相同点数的两张牌分成两手牌进行游戏
- 改进了玩家交互体验，添加了更详细的操作反馈
- 修复了多手牌情况下的游戏流程问题

### v0.2.0 (2025-03-31)
- 新增了加倍(Double Down)功能
- 实现了更完整的21点规则
- 优化了消息展示格式

### v0.1.1 (2025-04-04)
- 修复了多人游戏流程问题：现在当一个玩家爆牌后，游戏会正确地转移到下一个玩家，而不是直接转到庄家回合
- 改进了玩家状态处理机制，确保所有玩家都有机会行动

### v0.1.0 (2025-03-30)
- 初始版本发布
- 基本的21点游戏功能
- 玩家管理系统
- 每日签到奖励
- 排行榜功能

## 安装方法

1. 将整个`BlackJack`文件夹复制到`plugins`目录中
2. 重启机器人

## 游戏指令

### 基础指令

- `BlackJack注册` 或 `21点注册` - 注册游戏账号
- `BlackJack状态` 或 `21点状态` - 查看玩家状态
- `BlackJack签到` 或 `21点签到` - 每日签到领取筹码
- `BlackJack规则` 或 `21点规则` - 查看游戏规则
- `BlackJack菜单` 或 `21点菜单` - 显示指令菜单
- `BlackJack排行榜 [类型]` 或 `21点排行榜 [类型]` - 查看排行榜
  - 类型: 筹码(默认)、胜场、blackjack

### 游戏指令

- `BlackJack准备` 或 `21点准备` - 准备参与游戏
- `开始BlackJack` 或 `开始21点` - 开始游戏(需至少1人准备)
- `下注 [数量]` - 下注筹码
- `要牌` - 要一张牌
- `停牌` - 不再要牌
- `加倍` - 加倍下注并只要一张牌
- `分牌` - 将两张相同点数的牌分成两副(需额外下注)
- `查看牌局` - 查看当前牌局状态
- `BJStatus` - 显示详细游戏状态（调试用）
- `清理BlackJack` 或 `清理21点` - 重置游戏状态(游戏出错时使用)

### 管理指令

- `重置BlackJack` 或 `重置21点` - 清空所有玩家数据和排行榜(管理员专用)

## 游戏规则

### 游戏目标
尽可能使手牌点数接近21点但不超过21点，同时打败庄家。

### 牌面点数
- 2-10的牌: 按牌面值计算
- J、Q、K: 均为10点
- A: 可算作1点或11点，自动选择有利的点数

### 基本规则
1. 游戏开始前，玩家需先准备，然后下注
2. 开局每人获得2张牌，庄家1张明牌1张暗牌
3. 轮流行动，可以选择要牌、停牌或加倍
4. 超过21点为爆牌，直接输掉本局
5. 玩家行动完毕后，庄家亮出底牌并按规则要牌
6. 庄家规则: 手牌小于17点必须要牌，17点及以上必须停牌

### 特殊规则
- BlackJack: 首两张牌为A+10点牌(10/J/Q/K)，赔率为3:2（赢得1.5倍下注）
- 加倍(Double Down): 仅限首两张牌时，加倍下注并只能再要一张牌
- 分牌: 两张相同点数的牌可分成两副单独游戏，每副牌均需下注

### 胜负判定
- 玩家BlackJack且庄家非BlackJack: 玩家胜(赔率3:2)
- 玩家爆牌: 庄家胜
- 庄家爆牌: 玩家胜
- 点数比较: 谁更接近21点谁胜
- 点数相同: 平局，退还下注

## 数据存储

玩家数据存储在`BlackJack/data/bjplayers.csv`文件中，包含以下字段:

- user_id: 用户ID
- session_id: 会话ID
- nickname: 玩家昵称
- chips: 筹码数量
- level: 玩家等级
- exp: 经验值
- total_wins: 胜场数
- total_losses: 输场数
- total_draws: 平局数
- last_checkin: 上次签到日期
- blackjack_count: BlackJack次数
- ready_status: 准备状态
- current_bet: 当前下注
- cards: 当前手牌

## 管理功能

插件提供了管理员功能，可以完全重置游戏数据：

1. 首位使用`重置BlackJack`命令的用户将被设置为管理员
2. 管理员信息存储在`BlackJack/data/bjadmin.txt`文件中
3. 重置操作会自动备份当前玩家数据到`BlackJack/data/bjplayers_backup_时间戳.csv`
4. 重置后所有玩家需要重新注册才能继续游戏

## 其他说明

- 每日签到可获得基础奖励+等级加成
- 升级所需经验值随等级增加而增加
- 玩家初始筹码为1000
- BlackJack(首两张牌为A+10点牌)赔率为3:2（赢得1.5倍下注）
- 普通获胜赔率为1:1
- 下注金额不能超过当前持有筹码
- 加倍操作需要有足够筹码支付额外下注
- 如果游戏出现错误，可以使用清理命令重置游戏状态

## 开发者信息

- 插件版本: 0.2.6
- 作者: assistant
- 依赖库: 无额外依赖
- 兼容性: 适用于所有支持plugins系统的聊天机器人框架

## 计划功能

- 更多赌场游戏变种(保险等)
- 定时筹码奖励
- 筹码兑换系统
- 更多统计数据
- 高级AI庄家策略 