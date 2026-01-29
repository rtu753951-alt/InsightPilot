from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Literal, Optional
import os
import random

RiskLevel = Literal["low", "medium", "high"]

@dataclass
class FollowupSuggestion:
    risk_level: RiskLevel
    summary: str
    scripts: Dict[str, str]
    next_actions: List[str]
    tags: List[str]

def _mock_suggestion(
    customer_code: str,
    membership_type: str,
    days_since_last_visit: int,
    total_spent: int,
    visit_count: int,
    risk_level: RiskLevel,
) -> FollowupSuggestion:
    # 讓 demo 看起來「每位客戶不一樣」，但又可控
    tone = "關懷" if risk_level != "low" else "友善提醒"
    offer = "回流小禮" if membership_type.upper() == "VIP" else "限定優惠"
    channel = "Line" if random.random() < 0.6 else "簡訊"

    summary = (
        f"{membership_type} 會員 {customer_code} 距離上次來訪 {days_since_last_visit} 天，"
        f"累計消費 {total_spent:,}、來訪 {visit_count} 次；建議以「{tone}」方式在本週內跟進。"
    )

    scripts = {
        "line": (
            f"您好 {customer_code}～最近看您有一段時間沒回來了😊 "
            f"想關心一下近況，也跟您分享我們本週的 {offer}，"
            f"若您方便我可以幫您安排合適的時段～"
        ),
        "sms": (
            f"{customer_code}您好：提醒您已 {days_since_last_visit} 天未回訪，"
            f"本週有 {offer}，回覆1我協助安排。"
        ),
        "call": (
            f"您好，我是XX這邊致電關心。看到您已 {days_since_last_visit} 天未回訪，"
            f"想了解是否有需要我們協助安排時段或提供相關建議。"
        ),
    }

    next_actions = []
    if risk_level == "high":
        next_actions = [
            "24 小時內優先聯繫（Line/電話）",
            "若未回應，48 小時後再跟進一次",
            "仍無回應：標記為『暫停打擾』並排入下週再次評估",
        ]
    elif risk_level == "medium":
        next_actions = [
            "本週內完成一次關懷訊息",
            "3 天後檢查是否回覆／是否預約",
        ]
    else:
        next_actions = [
            "維持被動提醒即可（每月一次）",
        ]

    tags = [risk_level, membership_type.lower(), channel.lower()]

    return FollowupSuggestion(
        risk_level=risk_level,
        summary=summary,
        scripts=scripts,
        next_actions=next_actions,
        tags=tags,
    )

def generate_followup_suggestion(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    payload 由後端組合後丟進來（不直接信任前端輸入）
    先做 mock；之後可切換成真正 LLM provider。
    """
    from app.core.config import settings
    provider = settings.LLM_PROVIDER.lower()

    # 先取必備欄位
    customer_code = str(payload.get("customer_code", "UNKNOWN"))
    membership_type = str(payload.get("membership_type", "STANDARD"))
    days_since = int(payload.get("days_since_last_visit", 0))
    total_spent = int(payload.get("total_spent", 0))
    visit_count = int(payload.get("visit_count", 0))
    risk_level = payload.get("risk_level", "low")
    if risk_level not in ("low", "medium", "high"):
        risk_level = "low"

    if provider == "mock":
        s = _mock_suggestion(
            customer_code=customer_code,
            membership_type=membership_type,
            days_since_last_visit=days_since,
            total_spent=total_spent,
            visit_count=visit_count,
            risk_level=risk_level,  # type: ignore
        )
        return {
            "risk_level": s.risk_level,
            "summary": s.summary,
            "scripts": s.scripts,
            "next_actions": s.next_actions,
            "tags": s.tags,
        }

    # 先保留：之後接真 LLM（OpenAI / 自架模型）時用
    raise RuntimeError(f"Unsupported LLM_PROVIDER={provider}. Use 'mock' for now.")
