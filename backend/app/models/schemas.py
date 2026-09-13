"""
Pydantic Request & Response Data Transfer Objects (DTOs)
"""

from typing import Optional
from pydantic import BaseModel, Field


class SetupRequest(BaseModel):
    password: str = Field(..., description="Master password to initialize secure vault")


class LoginRequest(BaseModel):
    password: str = Field(..., description="Master password to authenticate session")


class ScanRequest(BaseModel):
    symbol: Optional[str] = Field(default=None, description="Underlying symbol to scan. Defaults dynamically to the first configured watchlist instrument if omitted.")


class ApproveRequest(BaseModel):
    proposal_id: str = Field(..., description="Proposal ID to approve for execution")


class RejectRequest(BaseModel):
    proposal_id: str = Field(..., description="Proposal ID to reject")
    reason: Optional[str] = Field(default="User declined", description="Rejection rationale")


class ClosePositionRequest(BaseModel):
    position_id: str = Field(..., description="Position ID to close")


class SettingsUpdateRequest(BaseModel):
    kite_api_key: Optional[str] = None
    kite_api_secret: Optional[str] = None
    kite_access_token: Optional[str] = None
    gemini_api_key: Optional[str] = None
    trading_mode: Optional[str] = None  # "PAPER" or "LIVE"
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    discord_webhook_url: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    office_mode: Optional[bool] = None


class ModeUpdateRequest(BaseModel):
    trading_mode: str = Field(..., description="'PAPER' or 'LIVE'")


class KiteSessionRequest(BaseModel):
    request_token: str = Field(..., description="OAuth request token from Zerodha login redirect")
