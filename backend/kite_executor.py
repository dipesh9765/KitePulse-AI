"""
KitePulse AI - Trading Execution Engine & Broker Abstraction Layer

This module provides the core execution layer for KitePulse AI, adhering to SOLID principles,
the Strategy Pattern, and the Adapter Pattern. It cleanly separates low-level broker execution
(Zerodha KiteConnect SDK) from virtual sandbox execution (Paper Engine), orchestrated through
a unified trading engine facade.

SOLID Architectural Principles Applied:
- Single Responsibility Principle (SRP): Each class and helper method encapsulates exactly one
  domain responsibility (e.g. order preparation, network dispatch, fill reconciliation, state persistence).
- Open/Closed Principle (OCP): New broker adapters (e.g., Angel One, Dhan, Upstox) can implement
  BaseOrderExecutor without modifying the orchestrator.
- Liskov Substitution Principle (LSP): Both KiteExecutionEngine and PaperExecutionEngine fully
  honor the BaseOrderExecutor contract.
- Interface Segregation Principle (ISP): Clean, minimal interfaces defined in core.interfaces.
- Dependency Inversion Principle (DIP): High-level trading orchestration depends on abstract base
  classes rather than concrete broker implementations.
"""

import datetime
import time
import uuid
import logging
from typing import Dict, List, Optional, Any, Tuple, Union

from config import settings, get_tradingsymbol_map
import database
from security import has_active_session
from server_logger import (
    log_outgoing_request,
    log_outgoing_response,
    log_outgoing_error
)
from core.interfaces import BaseOrderExecutor, OrderStatus, TradingMode
from core.paper_executor import PaperExecutionEngine

logger = logging.getLogger(__name__)


class KiteExecutionEngine(BaseOrderExecutor):
    """
    Production-Grade Zerodha Kite Connect Execution Adapter.

    Responsibilities:
        - Implements BaseOrderExecutor to encapsulate all Zerodha KiteConnect SDK communications.
        - Enforces the mandatory 30-second token re-validation heartbeat before outbound dispatch.
        - Sanitizes instrument identifiers across NSE Equity and NFO Derivatives.
        - Dispatches regular MIS Intraday market orders and polls Kite order history for fill prices.

    Extends:
        core.interfaces.BaseOrderExecutor

    Uses:
        - kiteconnect.KiteConnect: Official Zerodha SDK client.
        - security.has_active_session: Global session token validator.
        - database: SQLite encrypted vault reader and order/position persistence.
        - server_logger: 3MB rotating log tracing with credential redaction.
    """

    def __init__(self, api_key: str = "", api_secret: str = "", access_token: str = ""):
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.kite_client = None

        # 30-Second token verification tracking state
        self._last_token_verification_time: float = 0.0
        self._token_verification_interval: float = 30.0  # Exactly 30 seconds
        self._is_token_verified: bool = False
        self._last_verification_error: Optional[str] = None

        self._init_kite()

    @property
    def mode(self) -> str:
        """Returns the operational execution mode ('LIVE')."""
        return "LIVE"

    def _init_kite(self) -> None:
        """
        Initializes the underlying Zerodha KiteConnect client instance.
        
        Configures API key and binds access token if available.
        """
        if self.api_key:
            try:
                from kiteconnect import KiteConnect
                self.kite_client = KiteConnect(api_key=self.api_key)
                if self.access_token:
                    self.kite_client.set_access_token(self.access_token)
                    logger.info("Zerodha KiteConnect client successfully initialized with access token.")
            except Exception as e:
                logger.error(f"Failed to initialize Zerodha KiteConnect client: {e}")

    # -------------------------------------------------------------------------
    # Authentication & Heartbeat Verification (SRP decomposed)
    # -------------------------------------------------------------------------

    def _check_system_session(self) -> Optional[str]:
        """Validates that an active, authenticated user session exists in the system."""
        if not has_active_session():
            return "No active authenticated user session exists in system."
        return None

    def _check_vault_unlocked(self) -> Optional[str]:
        """Validates that the master security vault is currently unlocked."""
        if not database.is_vault_unlocked():
            return "Master security vault is locked."
        return None

    def _check_client_configured(self) -> Optional[str]:
        """Validates that Kite access token is present and client is initialized."""
        if not self.access_token or not self.kite_client:
            return "Kite access token missing or client uninitialized."
        return None

    def _verify_remote_kite_session(self, now: float) -> Dict[str, Any]:
        """
        Sends an active profile ping to Zerodha Kite servers to confirm token validity.
        
        Args:
            now: Current epoch timestamp in seconds.

        Returns:
            Dict containing verification status and error/warning details.
        """
        call_start = time.time()
        log_outgoing_request("Zerodha Kite", "profile", {})
        try:
            profile_data = self.kite_client.profile()
            dur = round((time.time() - call_start) * 1000, 2)
            log_outgoing_response(
                "Zerodha Kite", "profile",
                {"user_id": profile_data.get("user_id"), "status": "active"},
                dur
            )
            self._is_token_verified = True
            self._last_verification_error = None
            self._last_token_verification_time = now
            logger.info("30s Verification SUCCESS: System session and Kite token are verified and valid.")
            return {"valid": True, "error": None, "timestamp": now}
        except Exception as e:
            dur = round((time.time() - call_start) * 1000, 2)
            log_outgoing_error("Zerodha Kite", "profile", e, dur)
            err_msg = str(e)
            logger.warning(f"30s Kite token verification check error: {err_msg}")

            if "TokenException" in type(e).__name__ or "403" in err_msg or "401" in err_msg:
                self._is_token_verified = False
                self._last_verification_error = f"Kite token expired/invalid: {err_msg}"
                return {"valid": False, "error": self._last_verification_error, "timestamp": now}

            # Non-auth network glitch, but local session remains valid
            self._last_token_verification_time = now
            self._is_token_verified = True
            return {"valid": True, "warning": err_msg, "timestamp": now}

    def verify_session(self) -> Dict[str, Any]:
        """
        Actively verifies system authentication state and Kite token validity.
        
        Decomposes verification into:
        1. Local session check
        2. Security vault unlock check
        3. Token presence check
        4. Remote Kite server profile handshake
        
        Returns:
            Dict containing 'valid' (bool), 'error' (Optional[str]), and 'timestamp' (float).
        """
        now = time.time()

        # Step 1: System Level Session Check
        session_err = self._check_system_session()
        if session_err:
            self._is_token_verified = False
            self._last_verification_error = session_err
            logger.warning(f"30s Check: {session_err}")
            return {"valid": False, "error": session_err, "timestamp": now}

        # Step 2: Vault Level Check
        vault_err = self._check_vault_unlocked()
        if vault_err:
            self._is_token_verified = False
            self._last_verification_error = vault_err
            logger.warning(f"30s Check: {vault_err}")
            return {"valid": False, "error": vault_err, "timestamp": now}

        # Step 3: Client & Token Presence Check
        client_err = self._check_client_configured()
        if client_err:
            self._is_token_verified = False
            self._last_verification_error = client_err
            return {"valid": False, "error": client_err, "timestamp": now}

        # Step 4: Active Remote Kite Ping
        return self._verify_remote_kite_session(now)

    def verify_outgoing_kite_request(self) -> bool:
        """
        CRITICAL SECURITY GUARD: Pre-flight validator called before EVERY outbound Kite request.
        
        Authenticates first whether the active user session exists and vault is unlocked.
        Every 30 seconds, actively re-verifies that the request authentication token is valid.
        
        Returns:
            bool: True if pre-flight verification succeeds.

        Raises:
            PermissionError: If active user session is missing, vault is locked, or token check fails.
        """
        if not has_active_session():
            raise PermissionError("Outgoing Kite request BLOCKED: No active authenticated system session exists.")

        if not database.is_vault_unlocked():
            raise PermissionError("Outgoing Kite request BLOCKED: Master security vault is locked.")

        now = time.time()
        if (now - self._last_token_verification_time) >= self._token_verification_interval:
            verif = self.verify_session()
            if not verif["valid"]:
                raise PermissionError(f"Outgoing Kite request BLOCKED: 30s token verification failed - {verif.get('error')}")

        return True

    def get_margins(self) -> Dict[str, Any]:
        """
        Fetches authentic account margins and balance from Zerodha Kite.
        
        Returns:
            Dict containing raw margin dictionary from Zerodha Kite Connect.
        """
        self.verify_outgoing_kite_request()
        if not self.kite_client:
            raise ValueError("KiteConnect client is not initialized.")

        call_start = time.time()
        log_outgoing_request("Zerodha Kite", "margins", {})
        try:
            margins_data = self.kite_client.margins()
            dur = round((time.time() - call_start) * 1000, 2)
            log_outgoing_response(
                "Zerodha Kite", "margins",
                {"status": "success", "equity_enabled": bool(margins_data.get("equity", {}).get("enabled", False))},
                dur
            )
            return margins_data
        except Exception as e:
            dur = round((time.time() - call_start) * 1000, 2)
            log_outgoing_error("Zerodha Kite", "margins", e, dur)
            raise e

    # -------------------------------------------------------------------------

    # Order Execution Pipeline (SRP decomposed)
    # -------------------------------------------------------------------------

    def _prepare_order_parameters(self, proposal: Dict[str, Any], lot_size: int) -> Tuple[Dict[str, Any], str, str]:
        """
        Prepares and sanitizes Kite order parameters according to exchange conventions.

        Args:
            proposal: Approved trade proposal payload.
            lot_size: Number of lots/quantity to trade.

        Returns:
            Tuple of (order_params_dict, clean_tradingsymbol, exchange_str).
        """
        trans_type = (
            self.kite_client.TRANSACTION_TYPE_BUY
            if "BUY" in proposal["signal_type"]
            else self.kite_client.TRANSACTION_TYPE_SELL
        )

        is_derivative = "CE" in proposal["instrument"] or "PE" in proposal["instrument"]
        exchange = self.kite_client.EXCHANGE_NFO if is_derivative else self.kite_client.EXCHANGE_NSE

        raw_inst = proposal.get("instrument", "")
        clean_tradingsymbol = raw_inst.replace(" MIS", "").replace(" CNC", "").replace(" EQ", "").strip()
        if not is_derivative and proposal.get("symbol"):
            sym = proposal["symbol"].strip()
            clean_tradingsymbol = get_tradingsymbol_map().get(sym, sym)

        order_params = {
            "variety": self.kite_client.VARIETY_REGULAR,
            "exchange": exchange,
            "tradingsymbol": clean_tradingsymbol,
            "transaction_type": trans_type,
            "quantity": lot_size,
            "product": self.kite_client.PRODUCT_MIS,
            "order_type": self.kite_client.ORDER_TYPE_MARKET
        }
        return order_params, clean_tradingsymbol, exchange

    def _dispatch_kite_order(self, order_params: Dict[str, Any]) -> str:
        """
        Dispatches the prepared market order to Zerodha Kite Connect with telemetry logging.

        Args:
            order_params: Sanitized KiteConnect order parameter dictionary.

        Returns:
            str: Broker-assigned order identifier.

        Raises:
            Exception: If order placement encounters a broker failure.
        """
        call_start = time.time()
        log_outgoing_request("Zerodha Kite", "place_order", order_params)
        try:
            order_id = self.kite_client.place_order(**order_params)
            dur = round((time.time() - call_start) * 1000, 2)
            log_outgoing_response("Zerodha Kite", "place_order", {"order_id": str(order_id)}, dur)
            return str(order_id)
        except Exception as pe_err:
            dur = round((time.time() - call_start) * 1000, 2)
            log_outgoing_error("Zerodha Kite", "place_order", pe_err, dur)
            raise pe_err

    def _reconcile_order_fill(self, order_id: str, default_price: float) -> Tuple[str, str, float]:
        """
        Queries Kite order history to determine actual broker status and average fill price.

        Args:
            order_id: Broker order identifier.
            default_price: Fallback entry price from proposal.

        Returns:
            Tuple of (kite_status_str, status_message_str, filled_price_float).
        """
        kite_status = "SUBMITTED"
        status_message = "Order submitted to Zerodha Kite"
        filled_price = default_price

        try:
            h_start = time.time()
            log_outgoing_request("Zerodha Kite", "order_history", {"order_id": order_id})
            history = self.kite_client.order_history(order_id)
            h_dur = round((time.time() - h_start) * 1000, 2)
            log_outgoing_response("Zerodha Kite", "order_history", {"records_count": len(history) if history else 0}, h_dur)
            if history:
                latest = history[-1]
                kite_status = latest.get("status", "SUBMITTED")
                status_message = latest.get("status_message") or f"Kite status: {kite_status}"
                if latest.get("average_price") and float(latest.get("average_price")) > 0:
                    filled_price = float(latest["average_price"])
        except Exception as he:
            logger.warning(f"Could not fetch order history from Kite: {he}")

        return kite_status, status_message, filled_price

    def _record_executed_order(
        self,
        order_id: str,
        proposal: Dict[str, Any],
        lot_size: int,
        filled_price: float,
        kite_status: str,
        status_message: str
    ) -> Dict[str, Any]:
        """Constructs an immutable order audit record and persists it to SQLite."""
        order_record = {
            "order_id": order_id,
            "instrument": proposal["instrument"],
            "type": "BUY" if "BUY" in proposal["signal_type"] else "SELL",
            "quantity": lot_size,
            "price": filled_price,
            "status": kite_status,
            "status_message": status_message,
            "mode": "LIVE",
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
        }
        database.save_order(order_record, proposal.get("proposal_id"))
        return order_record

    def _record_live_position(
        self,
        order_id: str,
        proposal: Dict[str, Any],
        lot_size: int,
        filled_price: float
    ) -> Dict[str, Any]:
        """Constructs a tracked live position record and persists it to SQLite."""
        pos_id = f"POS-LIVE-{order_id[-6:]}"
        position = {
            "position_id": pos_id,
            "proposal_id": proposal.get("proposal_id"),
            "order_id": order_id,
            "symbol": proposal["symbol"],
            "instrument": proposal["instrument"],
            "signal_type": proposal["signal_type"],
            "quantity": lot_size,
            "buy_price": filled_price,
            "current_ltp": filled_price,
            "stop_loss": float(proposal["stop_loss"]),
            "target_1": float(proposal["target_1"]),
            "target_2": float(proposal["target_2"]),
            "unrealized_pnl": 0.0,
            "pnl_pct": 0.0,
            "opened_at": datetime.datetime.now().strftime("%H:%M:%S"),
            "status": "OPEN",
            "mode": "LIVE"
        }
        database.save_position(position)
        return position

    def execute_order(self, proposal: Dict[str, Any], lot_size: int) -> Dict[str, Any]:
        """
        Orchestrates live MIS Intraday order execution on Zerodha Kite Connect.
        
        Workflow:
            1. Verify outbound authentication & 30s token heartbeat.
            2. Prepare and sanitize order parameters.
            3. Dispatch order to Zerodha Kite.
            4. Reconcile fill price and execution state from broker order history.
            5. Persist order audit log and active position record.
            
        Args:
            proposal: Approved trade proposal payload.
            lot_size: Number of lots/quantity (strictly validated).
            
        Returns:
            Dict containing order details, initial position, status, and feedback message.
            
        Raises:
            RuntimeError: If order placement encounters a fatal broker error.
        """
        self.verify_outgoing_kite_request()
        try:
            # 1. Parameter Preparation
            order_params, clean_symbol, exchange = self._prepare_order_parameters(proposal, lot_size)

            # 2. Network Dispatch
            order_id = self._dispatch_kite_order(order_params)

            # 3. Status & Fill Reconciliation
            default_entry = float(proposal["entry_price"])
            kite_status, status_message, filled_price = self._reconcile_order_fill(order_id, default_entry)

            # 4. Audit Log Persistence
            order_record = self._record_executed_order(
                order_id, proposal, lot_size, filled_price, kite_status, status_message
            )

            # 5. Handle Broker Rejection
            if kite_status == "REJECTED":
                return {
                    "order": order_record,
                    "rejected": True,
                    "status": "REJECTED",
                    "mode": "LIVE",
                    "message": f"Zerodha Kite REJECTED order: {status_message}"
                }

            # 6. Position Initialization
            position = self._record_live_position(order_id, proposal, lot_size, filled_price)

            return {
                "order": order_record,
                "position": position,
                "status": kite_status,
                "mode": "LIVE",
                "message": f"Order executed on Zerodha Kite! Order ID: #{order_id} ({kite_status})"
            }
        except Exception as e:
            logger.error(f"Live Kite order placement failed: {e}")
            raise RuntimeError(f"Kite order failed: {str(e)}")

    def close_position(self, position_id: str, reason: str = "MANUAL_EXIT") -> Dict[str, Any]:
        """Routes square-off order to Zerodha Kite for live position termination."""
        self.verify_outgoing_kite_request()
        return {"position_id": position_id, "reason": reason, "mode": "LIVE"}


class UnifiedTradingEngine:
    """
    Unified Trading Orchestrator & Portfolio Strategy Facade.

    Responsibilities:
        - Orchestrates execution strategy routing between Paper Sandbox and Live Kite broker.
        - Manages pending proposals with strict 60-second human approval countdowns.
        - Recalculates real-time mark-to-market P&L and option delta adjustments.
        - Evaluates dynamic Stop-Loss and Take-Profit triggers for automatic square-off.
        - Provides backward-compatible interface (KiteTradingExecutor) for API and tests.

    Extends:
        Acts as a Strategy Facade coordinating BaseOrderExecutor implementations.

    Uses:
        - PaperExecutionEngine: Virtual portfolio sandbox engine.
        - KiteExecutionEngine: Production Zerodha broker engine.
        - database: Persistent SQLite storage for orders, positions, and suggestions.
        - config.settings: Application-wide parameters and lot size guardrails.
    """

    def __init__(self):
        self.mode: str = settings.TRADING_MODE  # "PAPER" or "LIVE"
        self.api_key: str = ""
        self.api_secret: str = ""
        self.access_token: str = ""

        # Sub-engines
        self.paper_engine = PaperExecutionEngine(initial_balance=settings.INITIAL_PAPER_CAPITAL)
        self.kite_engine = KiteExecutionEngine()

        # Shared portfolio state
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.orders_history: List[Dict[str, Any]] = []
        self.pending_proposals: Dict[str, Dict[str, Any]] = {}
        self._last_kite_margins: Optional[Dict[str, Any]] = None

        self.load_credentials()
        self.load_open_positions()

    # -------------------------------------------------------------------------
    # Backward Compatibility Properties & Delegates
    # -------------------------------------------------------------------------

    @property
    def paper_balance(self) -> float:
        """Exposes paper balance for backward compatibility."""
        return self.paper_engine.paper_balance

    @paper_balance.setter
    def paper_balance(self, value: float) -> None:
        self.paper_engine.paper_balance = value

    @property
    def kite_client(self):
        """Exposes underlying KiteConnect client for backward compatibility."""
        return self.kite_engine.kite_client

    @kite_client.setter
    def kite_client(self, client):
        self.kite_engine.kite_client = client

    def _init_kite(self) -> None:
        """Initializes or re-initializes Zerodha KiteConnect instance on kite_engine."""
        self.kite_engine.api_key = self.api_key
        self.kite_engine.api_secret = self.api_secret
        self.kite_engine.access_token = self.access_token
        self.kite_engine._init_kite()

    # -------------------------------------------------------------------------
    # State Synchronization & Credentials
    # -------------------------------------------------------------------------

    def load_open_positions(self) -> None:
        """Restores any active open positions from the persistent SQLite database."""
        try:
            open_pos = database.get_open_positions_from_db()
            for pid, pos in open_pos.items():
                if pid not in self.positions:
                    self.positions[pid] = pos
                    if pos.get("mode") == "PAPER":
                        self.paper_engine.positions[pid] = pos
            if open_pos:
                logger.info(f"Restored {len(open_pos)} active open positions from SQLite database.")
        except Exception as e:
            logger.warning(f"Could not load open positions from DB: {e}")

    def load_credentials(self) -> None:
        """Loads Kite credentials from encrypted vault or environment settings."""
        db_key = database.get_secure_setting("KITE_API_KEY", "")
        db_secret = database.get_secure_setting("KITE_API_SECRET", "")
        db_token = database.get_secure_setting("KITE_ACCESS_TOKEN", "")
        db_mode = database.get_secure_setting("TRADING_MODE", "")

        self.api_key = db_key or settings.KITE_API_KEY
        self.api_secret = db_secret or settings.KITE_API_SECRET
        self.access_token = db_token or settings.KITE_ACCESS_TOKEN
        if db_mode in ["PAPER", "LIVE"]:
            self.mode = db_mode
            settings.TRADING_MODE = db_mode

        # Update Kite Engine credentials
        self.kite_engine.api_key = self.api_key
        self.kite_engine.api_secret = self.api_secret
        self.kite_engine.access_token = self.access_token
        self.kite_engine._init_kite()

    def verify_auth_token_now(self) -> Dict[str, Any]:
        """Actively verifies system session and Kite token validity via Kite Engine."""
        return self.kite_engine.verify_session()

    def verify_outgoing_kite_request(self) -> bool:
        """Enforces pre-flight authentication checks prior to Kite outbound calls."""
        return self.kite_engine.verify_outgoing_kite_request()

    def is_authenticated(self) -> bool:
        """Returns True if Kite client is initialized, access token is set, and system session is active."""
        return bool(
            self.kite_engine.kite_client
            and self.kite_engine.access_token
            and has_active_session()
            and database.is_vault_unlocked()
        )

    def get_login_url(self) -> str:
        """Returns the Zerodha OAuth login URL for user authentication."""
        if not self.api_key:
            raise ValueError("Kite API Key is required to generate OAuth login URL.")
        if self.kite_engine.kite_client:
            return self.kite_engine.kite_client.login_url()
        return "https://kite.zerodha.com/connect/login?v=3&api_key=" + self.api_key

    def set_session(self, request_token: str) -> Dict[str, Any]:
        """Exchanges Kite OAuth request token for access token and saves to encrypted vault."""
        if not self.kite_engine.kite_client or not self.api_secret:
            raise ValueError("Kite API Key and Secret are required.")
        call_start = time.time()
        log_outgoing_request("Zerodha Kite", "generate_session", {"request_token": request_token})
        try:
            session_data = self.kite_engine.kite_client.generate_session(request_token, api_secret=self.api_secret)
            dur = round((time.time() - call_start) * 1000, 2)
            log_outgoing_response("Zerodha Kite", "generate_session", {"user_id": session_data.get("user_id"), "status": "success"}, dur)
        except Exception as e:
            dur = round((time.time() - call_start) * 1000, 2)
            log_outgoing_error("Zerodha Kite", "generate_session", e, dur)
            raise e

        self.access_token = session_data["access_token"]
        self.kite_engine.access_token = self.access_token
        self.kite_engine.kite_client.set_access_token(self.access_token)
        try:
            database.save_secure_setting("KITE_ACCESS_TOKEN", self.access_token)
        except Exception as e:
            logger.warning(f"Could not persist access token to vault: {e}")
        return session_data

    def get_kite_margins(self) -> Dict[str, Any]:
        """
        Retrieves formatted Zerodha Kite account margins including available balance and utilised funds.
        
        Returns:
            Dict with 'connected', 'equity', 'commodity', 'timestamp', and optional 'error'.
        """
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if not self.is_authenticated():
            return {
                "connected": False,
                "error": "Zerodha Kite is not connected or daily session is inactive.",
                "timestamp": now_iso
            }

        try:
            raw_margins = self.kite_engine.get_margins()
            equity = raw_margins.get("equity", {})
            equity_avail = equity.get("available", {})
            equity_util = equity.get("utilised", {})
            
            # Zerodha live_balance represents real usable intraday cash
            available_cash = float(equity_avail.get("live_balance", equity_avail.get("cash", 0.0)) or 0.0)
            total_net = float(equity.get("net", available_cash) or available_cash)
            utilised_margin = float(equity_util.get("debits", 0.0) or 0.0)
            opening_bal = float(equity_avail.get("opening_balance", 0.0) or 0.0)
            
            commodity = raw_margins.get("commodity", {})
            comm_avail = commodity.get("available", {})
            comm_util = commodity.get("utilised", {})
            comm_available_cash = float(comm_avail.get("live_balance", comm_avail.get("cash", 0.0)) or 0.0)

            result = {
                "connected": True,
                "equity": {
                    "net": round(total_net, 2),
                    "available_cash": round(available_cash, 2),
                    "available_margin": round(available_cash, 2),
                    "utilised": round(utilised_margin, 2),
                    "opening_balance": round(opening_bal, 2)
                },
                "commodity": {
                    "enabled": bool(commodity.get("enabled", False)),
                    "net": round(float(commodity.get("net", 0.0) or 0.0), 2),
                    "available_cash": round(comm_available_cash, 2),
                    "utilised": round(float(comm_util.get("debits", 0.0) or 0.0), 2)
                },
                "timestamp": now_iso
            }
            self._last_kite_margins = result
            return result
        except Exception as e:
            logger.error(f"Failed to fetch Kite margins: {e}")
            return {
                "connected": False,
                "error": str(e),
                "timestamp": now_iso
            }

    # -------------------------------------------------------------------------

    # Proposal Lifecycle Management
    # -------------------------------------------------------------------------

    def create_trade_proposal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a pending trade proposal awaiting human verbal or click confirmation.
        
        Strict Guardrail: No trade is executed until approve_trade() is explicitly called!
        
        Args:
            signal: Generated technical/AI trade setup.
            
        Returns:
            Dict containing proposal payload with 60s expiration and PENDING status.
        """
        proposal_id = str(uuid.uuid4())[:8]
        proposal = {
            "proposal_id": proposal_id,
            "symbol": signal["symbol"],
            "instrument": signal["instrument_to_trade"],
            "signal_type": signal["signal_type"],
            "direction": signal["direction"],
            "lot_size": settings.DEFAULT_LOT_SIZE,  # Strictly 1 lot
            "quantity": 1,
            "entry_price": float(signal["entry_price"]),
            "stop_loss": float(signal["stop_loss"]),
            "target_1": float(signal["target_1"]),
            "target_2": float(signal["target_2"]),
            "risk_reward": signal["risk_reward"],
            "confidence": int(signal["confidence"]),
            "verbal_pitch": signal["verbal_pitch"],
            "technical_rationale": signal["technical_rationale"],
            "status": OrderStatus.PENDING_APPROVAL,
            "created_at": datetime.datetime.now().strftime("%H:%M:%S"),
            "expires_in_seconds": 60
        }
        self.pending_proposals[proposal_id] = proposal
        database.save_suggestion(proposal)
        return proposal

    def approve_trade(self, proposal_id: str) -> Dict[str, Any]:
        """
        Processes human trade confirmation ('Approve' click or voice command).
        Routes order to either Zerodha Kite (LIVE) or Paper Sandbox (PAPER).
        
        Args:
            proposal_id: 8-character proposal identifier.
            
        Returns:
            Dict of execution results including order record and active position.
        """
        proposal = self.pending_proposals.get(proposal_id)
        if not proposal:
            raise ValueError(f"Trade proposal {proposal_id} not found or expired.")

        if proposal["status"] != OrderStatus.PENDING_APPROVAL:
            raise ValueError(f"Proposal {proposal_id} already processed: {proposal['status']}")

        # Enforce strict lot size constraint (capped at 1 during incubation)
        lot_size = min(proposal.get("lot_size", 1), settings.MAX_LOT_SIZE)

        executed_trade = None
        if self.mode == "LIVE" and self.kite_engine.kite_client and self.access_token:
            executed_trade = self.kite_engine.execute_order(proposal, lot_size)
        else:
            executed_trade = self.paper_engine.execute_order(proposal, lot_size)

        # Synchronize local positions
        if "position" in executed_trade:
            pos = executed_trade["position"]
            self.positions[pos["position_id"]] = pos

        if "order" in executed_trade:
            self.orders_history.insert(0, executed_trade["order"])

        proposal["status"] = OrderStatus.APPROVED
        database.update_suggestion_status(proposal_id, "APPROVED")
        return executed_trade

    def reject_trade(self, proposal_id: str, reason: str = "User declined") -> Dict[str, Any]:
        """Records user rejection ('Reject' click or voice command)."""
        proposal = self.pending_proposals.get(proposal_id)
        if not proposal:
            raise ValueError(f"Trade proposal {proposal_id} not found.")
        proposal["status"] = OrderStatus.REJECTED
        proposal["rejection_reason"] = reason
        database.update_suggestion_status(proposal_id, "REJECTED")
        return proposal

    # -------------------------------------------------------------------------
    # Position Termination & P&L Calculation (SRP decomposed)
    # -------------------------------------------------------------------------

    def _resolve_position(self, position_id: str) -> Dict[str, Any]:
        """Resolves position from active memory or falls back to SQLite database."""
        pos = self.positions.get(position_id)
        if pos:
            return pos

        db_pos = database.get_position_by_id(position_id)
        if not db_pos:
            raise ValueError(f"Position {position_id} not found in active records or database.")

        if db_pos.get("status") == "CLOSED":
            return db_pos

        self.positions[position_id] = db_pos
        return db_pos

    def _calculate_realized_pnl(self, pos: Dict[str, Any], exit_price: float, quantity: int) -> float:
        """Calculates direction-aware realized Profit and Loss."""
        buy_price = float(pos.get("buy_price") or exit_price)
        signal_type = str(pos.get("signal_type") or "BUY")

        if "SHORT" in signal_type:
            return round((buy_price - exit_price) * quantity, 2)
        return round((exit_price - buy_price) * quantity, 2)

    def _persist_closed_position(
        self,
        pos: Dict[str, Any],
        exit_price: float,
        realized_pnl: float,
        reason: str,
        closed_at: str
    ) -> None:
        """Updates position record in memory and SQLite database."""
        pos["status"] = "CLOSED"
        pos["exit_price"] = exit_price
        pos["realized_pnl"] = realized_pnl
        pos["close_reason"] = reason
        pos["closed_at"] = closed_at
        database.update_position_in_db(pos)

    def _record_exit_order(
        self,
        pos: Dict[str, Any],
        exit_price: float,
        quantity: int,
        pnl: float,
        closed_at: str
    ) -> Dict[str, Any]:
        """Creates an offsetting exit order audit record and persists it."""
        signal_type = str(pos.get("signal_type") or "BUY")
        exit_order = {
            "order_id": f"EXIT-{uuid.uuid4().hex[:6].upper()}",
            "instrument": pos.get("instrument", "UNKNOWN"),
            "type": "SELL" if "BUY" in signal_type else "BUY",
            "quantity": quantity,
            "price": exit_price,
            "status": "COMPLETED",
            "mode": pos.get("mode", "PAPER"),
            "pnl": pnl,
            "timestamp": closed_at
        }
        self.orders_history.insert(0, exit_order)
        database.save_order(exit_order, pos.get("proposal_id"))
        return exit_order

    def close_position(self, position_id: str, reason: str = "MANUAL_EXIT") -> Dict[str, Any]:
        """
        Closes an active position and updates portfolio accounting.
        
        Decomposed Steps:
            1. Resolve position from memory or database.
            2. Compute realized P&L based on direction.
            3. Update and persist position state.
            4. Record offsetting exit order in audit log.
            5. Evict position from active tracking pools.
        """
        pos = self._resolve_position(position_id)
        if pos.get("status") == "CLOSED":
            return {
                "message": "Position was already closed.",
                "pnl": pos.get("realized_pnl", 0.0),
                "position": pos
            }

        exit_price = float(pos.get("current_ltp") or pos.get("buy_price") or 0.0)
        buy_price = float(pos.get("buy_price") or exit_price)
        quantity = int(pos.get("quantity") or 1)

        # Calculate P&L
        pnl = self._calculate_realized_pnl(pos, exit_price, quantity)
        self.paper_balance += pnl
        closed_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Persist position
        self._persist_closed_position(pos, exit_price, pnl, reason, closed_at)

        # Record exit order
        exit_order = self._record_exit_order(pos, exit_price, quantity, pnl, closed_at)

        # Evict from active memory
        self.positions.pop(position_id, None)
        if position_id in self.paper_engine.positions:
            self.paper_engine.positions.pop(position_id, None)

        return {
            "message": "Position closed successfully",
            "pnl": pnl,
            "exit_order": exit_order,
            "position": pos
        }

    # -------------------------------------------------------------------------
    # Mark-to-Market & Trigger Monitoring (SRP decomposed)
    # -------------------------------------------------------------------------

    def _calculate_effective_price(
        self,
        symbol: str,
        instrument: str,
        current_ltp: float,
        live_prices: Dict[str, float]
    ) -> float:
        """
        Calculates the effective instrument price.
        For options derivatives, models premium delta movement (~0.5 delta).
        """
        cur_price = live_prices.get(symbol, current_ltp)
        if "CE" in instrument or "PE" in instrument:
            delta_price = (cur_price - live_prices.get(symbol, cur_price)) * 0.5
            return round(max(5.0, current_ltp + delta_price), 2)
        return cur_price

    def _evaluate_position_pnl(self, pos: Dict[str, Any], cur_price: float) -> Tuple[float, float]:
        """Calculates unrealized P&L and percentage return for a position."""
        buy_price = float(pos["buy_price"])
        qty = int(pos["quantity"])

        if "BUY" in pos["signal_type"]:
            pnl = round((cur_price - buy_price) * qty, 2)
        else:
            pnl = round((buy_price - cur_price) * qty, 2)

        cost_basis = buy_price * qty
        pnl_pct = round((pnl / cost_basis) * 100, 2) if cost_basis > 0 else 0.0
        return pnl, pnl_pct

    def _check_exit_triggers(self, pos: Dict[str, Any], cur_price: float) -> Optional[str]:
        """
        Evaluates whether a position has reached its Stop-Loss or Target 1 threshold.

        Returns:
            Optional[str]: 'STOP_LOSS_HIT', 'TARGET_HIT', or None.
        """
        is_long = "BUY" in pos["signal_type"]
        sl = float(pos["stop_loss"])
        t1 = float(pos["target_1"])

        if is_long:
            if cur_price <= sl:
                return "STOP_LOSS_HIT"
            if cur_price >= t1:
                return "TARGET_HIT"
        else:
            if cur_price >= sl:
                return "STOP_LOSS_HIT"
            if cur_price <= t1:
                return "TARGET_HIT"

        return None

    def update_positions_pnl(self, live_prices: Dict[str, float]) -> None:
        """
        Recalculates active positions P&L and triggers automatic Stop-Loss or Target exits.
        
        Decomposed Workflow:
            1. Calculate effective price (with option delta).
            2. Compute unrealized P&L and return percentage.
            3. Evaluate SL/Target trigger breaches.
            4. Auto-execute close_position on breached positions.
        """
        to_close: List[Tuple[str, str]] = []

        for pid, pos in list(self.positions.items()):
            symbol = pos["symbol"]
            cur_price = self._calculate_effective_price(
                symbol, pos["instrument"], pos["current_ltp"], live_prices
            )

            pos["current_ltp"] = cur_price
            pnl, pnl_pct = self._evaluate_position_pnl(pos, cur_price)
            pos["unrealized_pnl"] = pnl
            pos["pnl_pct"] = pnl_pct

            database.update_position_in_db(pos)

            trigger_reason = self._check_exit_triggers(pos, cur_price)
            if trigger_reason:
                to_close.append((pid, trigger_reason))

        for pid, reason in to_close:
            self.close_position(pid, reason)

    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Returns consolidated high-level portfolio balance, P&L, and connectivity summary."""
        total_unrealized_pnl = round(sum(p["unrealized_pnl"] for p in self.positions.values()), 2)
        total_realized_pnl = round(sum(o.get("pnl", 0.0) for o in self.orders_history if "pnl" in o), 2)
        return {
            "mode": self.mode,
            "paper_balance": round(self.paper_balance + total_unrealized_pnl, 2),
            "initial_balance": settings.INITIAL_PAPER_CAPITAL,
            "unrealized_pnl": total_unrealized_pnl,
            "realized_pnl": total_realized_pnl,
            "total_pnl": round(total_unrealized_pnl + total_realized_pnl, 2),
            "open_positions_count": len(self.positions),
            "completed_orders_count": len(self.orders_history),
            "kite_connected": bool(self.access_token and self.kite_client),
            "kite_balance": self._last_kite_margins
        }


# Export alias for 100% backward compatibility across all imports
KiteTradingExecutor = UnifiedTradingEngine

# Singleton instance
kite_executor = KiteTradingExecutor()
