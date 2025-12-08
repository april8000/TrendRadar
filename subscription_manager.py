# coding=utf-8
"""
订阅管理模块
支持多租户、多分组关键词订阅推送系统

功能：
- 从JSON配置文件加载订阅
- 为每个订阅筛选匹配的新闻
- 支持复杂的关键词匹配规则（必须词、过滤词、数量限制）
- 管理多个webhook推送地址
"""

import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime


class SubscriptionManager:
    """订阅管理器"""
    
    def __init__(self, config_path: str = "config/subscriptions.json"):
        """
        初始化订阅管理器
        
        Args:
            config_path: 订阅配置文件路径
        """
        self.config_path = config_path
        self.config_data = {}
        self.subscriptions = []
        self.global_settings = {}
        self._load_config()
    
    def _load_config(self):
        """加载订阅配置文件"""
        if not os.path.exists(self.config_path):
            print(f"[警告] 订阅配置文件不存在: {self.config_path}")
            print("   将使用默认配置模式")
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
                self.subscriptions = self.config_data.get("subscriptions", [])
                self.global_settings = self.config_data.get("global_settings", {})
                
                print(f"[OK] 成功加载订阅配置")
                print(f"   版本: {self.config_data.get('version', '未知')}")
                print(f"   订阅数量: {len(self.subscriptions)}")
                
        except json.JSONDecodeError as e:
            print(f"[错误] 订阅配置文件JSON格式错误: {e}")
            raise
        except Exception as e:
            print(f"[错误] 加载订阅配置失败: {e}")
            raise
    
    def has_subscriptions(self) -> bool:
        """检查是否有订阅配置"""
        return len(self.subscriptions) > 0
    
    def get_active_subscriptions(self) -> List[Dict]:
        """
        获取所有启用的订阅
        
        Returns:
            启用的订阅列表
        """
        active = [sub for sub in self.subscriptions if sub.get("enabled", True)]
        print(f"[信息] 活跃订阅: {len(active)}/{len(self.subscriptions)}")
        return active
    
    def get_subscription_by_id(self, sub_id: str) -> Optional[Dict]:
        """
        根据ID获取订阅
        
        Args:
            sub_id: 订阅ID
            
        Returns:
            订阅配置字典，未找到返回None
        """
        for sub in self.subscriptions:
            if sub.get("id") == sub_id:
                return sub
        return None
    
    def match_news_for_subscription(
        self, 
        subscription: Dict, 
        news_data: List[Dict]
    ) -> List[Dict]:
        """
        为特定订阅筛选匹配的新闻
        
        匹配规则：
        1. 排除词优先（黑名单）
        2. 普通关键词（OR逻辑，至少匹配一个）
        3. 必须词（AND逻辑，必须全部匹配）
        4. 应用数量限制
        
        Args:
            subscription: 订阅配置
            news_data: 新闻数据列表
            
        Returns:
            匹配的新闻列表
        """
        sub_name = subscription.get("name", "未命名订阅")
        keywords = subscription.get("keywords", {})
        
        normal_kws = keywords.get("normal", [])
        required_kws = keywords.get("required", [])
        excluded_kws = keywords.get("excluded", [])
        limit = keywords.get("limit", 0)
        
        print(f"\n[匹配] [{sub_name}] 开始匹配新闻...")
        print(f"   普通关键词: {normal_kws}")
        print(f"   必须包含: {required_kws}")
        print(f"   排除词: {excluded_kws}")
        print(f"   数量限制: {limit if limit > 0 else '不限制'}")
        
        matched_news = []
        
        for news in news_data:
            title = news.get("title", "").lower()
            
            # 规则1: 检查过滤词（优先级最高）
            if excluded_kws:
                if any(ex.lower() in title for ex in excluded_kws):
                    continue
            
            # 规则2: 检查普通关键词（至少匹配一个）
            if normal_kws:
                if not any(kw.lower() in title for kw in normal_kws):
                    continue
            
            # 规则3: 检查必须词（必须全部匹配）
            if required_kws:
                if not all(req.lower() in title for req in required_kws):
                    continue
            
            # 通过所有规则，添加到结果
            matched_news.append(news)
        
        # 规则4: 应用数量限制
        if limit > 0 and len(matched_news) > limit:
            matched_news = matched_news[:limit]
            print(f"   [警告] 结果超过限制，截取前 {limit} 条")
        
        print(f"   [OK] 匹配到 {len(matched_news)} 条新闻")
        
        return matched_news
    
    def get_webhooks(self, subscription: Dict) -> List[Dict]:
        """
        获取订阅的所有webhook配置
        
        Args:
            subscription: 订阅配置
            
        Returns:
            webhook列表
        """
        webhooks = subscription.get("webhooks", [])
        
        # 验证webhook配置
        valid_webhooks = []
        for webhook in webhooks:
            if not webhook.get("url"):
                print(f"   [警告] 跳过无效webhook: {webhook.get('name', '未命名')}")
                continue
            valid_webhooks.append(webhook)
        
        return valid_webhooks
    
    def should_enable_ai_search(self, subscription: Dict, matched_count: int) -> bool:
        """
        判断是否应该启用AI搜索补充
        
        Args:
            subscription: 订阅配置
            matched_count: 已匹配的新闻数量
            
        Returns:
            是否启用AI搜索
        """
        ai_config = subscription.get("ai_search", {})
        
        if not ai_config.get("enabled", False):
            return False
        
        threshold = ai_config.get("trigger_threshold", 3)
        
        if matched_count < threshold:
            print(f"   [AI] 匹配数 ({matched_count}) < 阈值 ({threshold})，触发AI搜索")
            return True
        
        return False
    
    def get_ai_search_config(self, subscription: Dict) -> Dict:
        """
        获取订阅的AI搜索配置
        
        Args:
            subscription: 订阅配置
            
        Returns:
            AI搜索配置字典
        """
        ai_config = subscription.get("ai_search", {})
        keywords = subscription.get("keywords", {})
        
        # 如果有自定义搜索关键词，使用自定义的
        search_keywords = ai_config.get("search_keywords")
        if not search_keywords:
            # 否则使用普通关键词
            search_keywords = keywords.get("normal", [])
        
        return {
            "enabled": ai_config.get("enabled", False),
            "trigger_threshold": ai_config.get("trigger_threshold", 3),
            "search_keywords": search_keywords,
            "time_range_hours": ai_config.get("time_range_hours", 24),
            "max_results": ai_config.get("max_results", 15)
        }
    
    def get_global_settings(self) -> Dict:
        """获取全局设置"""
        return self.global_settings
    
    def export_config(self, output_path: str):
        """
        导出配置到文件
        
        Args:
            output_path: 输出文件路径
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=2)
            print(f"[OK] 配置已导出到: {output_path}")
        except Exception as e:
            print(f"[错误] 导出配置失败: {e}")
    
    def validate_config(self) -> bool:
        """
        验证配置文件的有效性
        
        Returns:
            配置是否有效
        """
        if not self.subscriptions:
            print("[警告] 没有配置任何订阅")
            return False
        
        errors = []
        
        for idx, sub in enumerate(self.subscriptions, 1):
            sub_id = sub.get("id", f"订阅{idx}")
            
            # 检查必需字段
            if not sub.get("name"):
                errors.append(f"[{sub_id}] 缺少 name 字段")
            
            if not sub.get("keywords"):
                errors.append(f"[{sub_id}] 缺少 keywords 字段")
            
            if not sub.get("webhooks"):
                errors.append(f"[{sub_id}] 缺少 webhooks 字段")
            else:
                webhooks = sub.get("webhooks", [])
                if not webhooks:
                    errors.append(f"[{sub_id}] webhooks 列表为空")
                else:
                    for w_idx, webhook in enumerate(webhooks, 1):
                        if not webhook.get("url"):
                            errors.append(f"[{sub_id}] webhook[{w_idx}] 缺少 url")
        
        if errors:
            print("[错误] 配置验证失败:")
            for error in errors:
                print(f"   - {error}")
            return False
        
        print("[OK] 配置验证通过")
        return True
    
    def get_statistics(self) -> Dict:
        """
        获取订阅统计信息
        
        Returns:
            统计信息字典
        """
        total = len(self.subscriptions)
        active = len(self.get_active_subscriptions())
        
        webhook_count = 0
        ai_enabled_count = 0
        
        for sub in self.subscriptions:
            webhook_count += len(sub.get("webhooks", []))
            if sub.get("ai_search", {}).get("enabled", False):
                ai_enabled_count += 1
        
        return {
            "total_subscriptions": total,
            "active_subscriptions": active,
            "total_webhooks": webhook_count,
            "ai_enabled_count": ai_enabled_count,
            "config_version": self.config_data.get("version", "未知")
        }


# ==================== 辅助函数 ====================

def create_sample_config(output_path: str = "config/subscriptions_sample.json"):
    """
    创建示例配置文件
    
    Args:
        output_path: 输出文件路径
    """
    sample_config = {
        "version": "1.0",
        "subscriptions": [
            {
                "id": "sub_example_001",
                "name": "示例订阅",
                "enabled": True,
                "keywords": {
                    "normal": ["关键词1", "关键词2"],
                    "required": [],
                    "excluded": ["广告"],
                    "limit": 10
                },
                "webhooks": [
                    {
                        "type": "wework",
                        "url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=your-key",
                        "name": "测试群组"
                    }
                ],
                "ai_search": {
                    "enabled": False,
                    "trigger_threshold": 3
                },
                "schedule": {
                    "enabled": True,
                    "cron": "0 * * * *"
                }
            }
        ],
        "global_settings": {
            "report_mode": "incremental",
            "platforms": ["zhihu", "weibo", "douyin"],
            "weight": {
                "rank_weight": 0.6,
                "frequency_weight": 0.3,
                "hotness_weight": 0.1
            }
        }
    }
    
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(sample_config, f, ensure_ascii=False, indent=2)
    
    print(f"[OK] 示例配置已创建: {output_path}")


if __name__ == "__main__":
    # 测试代码
    print("订阅管理模块测试\n")
    
    # 创建示例配置
    create_sample_config("config/subscriptions_sample.json")
    
    # 加载并验证
    manager = SubscriptionManager("config/subscriptions_sample.json")
    manager.validate_config()
    
    # 显示统计
    stats = manager.get_statistics()
    print(f"\n统计信息:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

