#!/usr/bin/env python3
"""
FastAPI REST API for MetaTrader5 interaction
"""
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import asyncio
import logging
import os
from contextlib import asynccontextmanager

try:
    from mt5linux import MetaTrader5

    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    MetaTrader5 = None

try:
    import MetaTrader5 as mt5_constants
except ImportError:
    # Crear constantes dummy para que la API funcione
    class MT5Constants:
        ORDER_TYPE_BUY = 0
        ORDER_TYPE_SELL = 1
        TRADE_ACTION_DEAL = 1
        TRADE_RETCODE_DONE = 10009
        TIMEFRAME_M1 = 1
        TIMEFRAME_M5 = 5
        TIMEFRAME_M15 = 15
        TIMEFRAME_M30 = 30
        TIMEFRAME_H1 = 16385
        TIMEFRAME_H4 = 16388
        TIMEFRAME_D1 = 16408
        TIMEFRAME_W1 = 32769
        TIMEFRAME_MN1 = 49153

    mt5_constants = MT5Constants


logger = logging.getLogger(__name__)

# Global MT5 connection
mt5_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage MT5 connection lifecycle"""
    global mt5_client
    if MT5_AVAILABLE and MetaTrader5:
        try:
            mt5_client = MetaTrader5(host="localhost", port=18812)
            if not mt5_client.initialize():
                logger.error("Failed to initialize MT5 connection")
                mt5_client = None
        except Exception as e:
            logger.error(f"Failed to create MT5 client: {e}")
            mt5_client = None
    else:
        logger.warning("MetaTrader5 module not available, API will run in limited mode")
        mt5_client = None
    yield
    if mt5_client:
        try:
            mt5_client.shutdown()
        except Exception:
            pass


# Create FastAPI app
app = FastAPI(
    title="MetaTrader5 API",
    description="REST API for MetaTrader5 trading operations",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
_allowed_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:8080")
allowed_origins = [o.strip() for o in _allowed_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API key authentication middleware
API_KEY = os.environ.get("API_KEY")


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    """Verify X-API-Key header when API_KEY env var is set."""
    # Skip auth if API_KEY is not configured (local dev)
    if not API_KEY:
        return await call_next(request)

    # Allow health check without auth
    if request.url.path in ("/health", "/docs", "/openapi.json", "/redoc"):
        return await call_next(request)

    provided_key = request.headers.get("X-API-Key")
    if provided_key != API_KEY:
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or missing API key"},
        )

    return await call_next(request)


# Pydantic models
class AccountInfo(BaseModel):
    login: int
    server: str
    balance: float
    equity: float
    margin: float
    free_margin: float
    leverage: int
    currency: str
    name: str = Field(default="")
    company: str = Field(default="")


class SymbolInfo(BaseModel):
    name: str
    description: str
    bid: float
    ask: float
    spread: float
    digits: int
    trade_contract_size: float
    volume_min: float
    volume_max: float
    volume_step: float


class OrderRequest(BaseModel):
    symbol: str
    volume: float
    order_type: str = Field(description="BUY or SELL")
    price: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    deviation: int = 20
    magic: int = 0
    comment: str = "API Order"


class OrderResponse(BaseModel):
    ticket: int
    symbol: str
    volume: float
    price: float
    order_type: str
    profit: float = 0.0
    status: str


class HistoryRequest(BaseModel):
    symbol: str
    timeframe: str = "M1"  # M1, M5, M15, M30, H1, H4, D1, W1, MN1
    start: datetime
    end: datetime
    count: Optional[int] = 1000


class Candle(BaseModel):
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    spread: int


# Health check
@app.get("/health")
async def health_check():
    """Check API and MT5 connection health"""
    mt5_status = mt5_client.terminal_info() if mt5_client else None

    return {
        "status": "healthy" if mt5_status else "unhealthy",
        "mt5_connected": bool(mt5_status),
        "terminal_info": mt5_status._asdict() if mt5_status else None,
    }


# Account endpoints
@app.get("/account", response_model=AccountInfo)
async def get_account_info():
    """Get current account information"""
    if not mt5_client:
        raise HTTPException(status_code=503, detail="MT5 not connected")

    account = mt5_client.account_info()
    if not account:
        raise HTTPException(status_code=404, detail="Account info not available")

    return AccountInfo(
        login=account.login,
        server=account.server,
        balance=account.balance,
        equity=account.equity,
        margin=account.margin,
        free_margin=account.margin_free,
        leverage=account.leverage,
        currency=account.currency,
        name=account.name,
        company=account.company,
    )


# Symbol endpoints
@app.get("/symbols")
async def get_symbols():
    """Get all available trading symbols"""
    if not mt5_client:
        raise HTTPException(status_code=503, detail="MT5 not connected")

    symbols = mt5_client.symbols_get()
    if not symbols:
        return []

    return [s.name for s in symbols if s.visible]


@app.get("/symbol/{symbol}", response_model=SymbolInfo)
async def get_symbol_info(symbol: str):
    """Get detailed information about a symbol"""
    if not mt5_client:
        raise HTTPException(status_code=503, detail="MT5 not connected")

    info = mt5_client.symbol_info(symbol)
    if not info:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")

    tick = mt5_client.symbol_info_tick(symbol)
    if not tick:
        raise HTTPException(status_code=404, detail=f"No tick data for {symbol}")

    return SymbolInfo(
        name=info.name,
        description=info.description,
        bid=tick.bid,
        ask=tick.ask,
        spread=info.spread,
        digits=info.digits,
        trade_contract_size=info.trade_contract_size,
        volume_min=info.volume_min,
        volume_max=info.volume_max,
        volume_step=info.volume_step,
    )


# Trading endpoints
@app.post("/order", response_model=OrderResponse)
async def place_order(request: OrderRequest):
    """Place a new trading order"""
    if not mt5_client:
        raise HTTPException(status_code=503, detail="MT5 not connected")

    # Prepare order request
    symbol_info = mt5_client.symbol_info(request.symbol)
    if not symbol_info:
        raise HTTPException(
            status_code=404, detail=f"Symbol {request.symbol} not found"
        )

    tick = mt5_client.symbol_info_tick(request.symbol)
    if not tick:
        raise HTTPException(
            status_code=404, detail=f"No tick data for {request.symbol}"
        )

    # Determine order type and price
    if request.order_type.upper() == "BUY":
        order_type = mt5_constants.ORDER_TYPE_BUY
        price = tick.ask
    elif request.order_type.upper() == "SELL":
        order_type = mt5_constants.ORDER_TYPE_SELL
        price = tick.bid
    else:
        raise HTTPException(status_code=400, detail="Invalid order type")

    # Create order request
    order_request = {
        "action": mt5_constants.TRADE_ACTION_DEAL,
        "symbol": request.symbol,
        "volume": request.volume,
        "type": order_type,
        "price": price,
        "deviation": request.deviation,
        "magic": request.magic,
        "comment": request.comment,
    }

    if request.sl:
        order_request["sl"] = request.sl
    if request.tp:
        order_request["tp"] = request.tp

    # Send order
    result = mt5_client.order_send(order_request)

    if not result or result.retcode != mt5_constants.TRADE_RETCODE_DONE:
        error_msg = result.comment if result else "Order failed"
        raise HTTPException(status_code=400, detail=error_msg)

    return OrderResponse(
        ticket=result.order,
        symbol=request.symbol,
        volume=request.volume,
        price=result.price,
        order_type=request.order_type,
        status="executed",
    )


@app.get("/positions")
async def get_positions():
    """Get all open positions"""
    if not mt5_client:
        raise HTTPException(status_code=503, detail="MT5 not connected")

    positions = mt5_client.positions_get()
    if not positions:
        return []

    return [
        {
            "ticket": pos.ticket,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": "BUY" if pos.type == 0 else "SELL",
            "price": pos.price_open,
            "current_price": pos.price_current,
            "profit": pos.profit,
            "sl": pos.sl,
            "tp": pos.tp,
            "time": pos.time,
            "magic": pos.magic,
            "comment": pos.comment,
        }
        for pos in positions
    ]


@app.delete("/position/{ticket}")
async def close_position(ticket: int):
    """Close a specific position"""
    if not mt5_client:
        raise HTTPException(status_code=503, detail="MT5 not connected")

    position = mt5_client.positions_get(ticket=ticket)
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    position = position[0]

    # Prepare close request
    tick = mt5_client.symbol_info_tick(position.symbol)
    if not tick:
        raise HTTPException(status_code=404, detail="No tick data")

    close_request = {
        "action": mt5_constants.TRADE_ACTION_DEAL,
        "position": ticket,
        "symbol": position.symbol,
        "volume": position.volume,
        "type": (
            mt5_constants.ORDER_TYPE_SELL
            if position.type == 0
            else mt5_constants.ORDER_TYPE_BUY
        ),
        "price": tick.bid if position.type == 0 else tick.ask,
        "deviation": 20,
        "magic": position.magic,
        "comment": f"Close position {ticket}",
    }

    result = mt5_client.order_send(close_request)

    if not result or result.retcode != mt5_constants.TRADE_RETCODE_DONE:
        error_msg = result.comment if result else "Failed to close position"
        raise HTTPException(status_code=400, detail=error_msg)

    return {"status": "closed", "ticket": ticket}


# History endpoints
@app.post("/history/candles", response_model=List[Candle])
async def get_candles(request: HistoryRequest):
    """Get historical candle data"""
    if not mt5_client:
        raise HTTPException(status_code=503, detail="MT5 not connected")

    # Convert timeframe
    timeframe_map = {
        "M1": mt5_constants.TIMEFRAME_M1,
        "M5": mt5_constants.TIMEFRAME_M5,
        "M15": mt5_constants.TIMEFRAME_M15,
        "M30": mt5_constants.TIMEFRAME_M30,
        "H1": mt5_constants.TIMEFRAME_H1,
        "H4": mt5_constants.TIMEFRAME_H4,
        "D1": mt5_constants.TIMEFRAME_D1,
        "W1": mt5_constants.TIMEFRAME_W1,
        "MN1": mt5_constants.TIMEFRAME_MN1,
    }

    timeframe = timeframe_map.get(request.timeframe.upper())
    if not timeframe:
        raise HTTPException(status_code=400, detail="Invalid timeframe")

    # Get rates
    rates = mt5_client.copy_rates_range(
        request.symbol, timeframe, request.start, request.end
    )

    if rates is None:
        return []

    # Limit results if specified
    if request.count and len(rates) > request.count:
        rates = rates[-request.count :]

    return [
        Candle(
            time=datetime.fromtimestamp(rate["time"]),
            open=rate["open"],
            high=rate["high"],
            low=rate["low"],
            close=rate["close"],
            volume=rate["tick_volume"],
            spread=rate["spread"],
        )
        for rate in rates
    ]


# WebSocket for real-time data
@app.websocket("/ws/ticks/{symbol}")
async def websocket_ticks(websocket: WebSocket, symbol: str):
    """WebSocket endpoint for real-time tick data"""
    await websocket.accept()

    try:
        while True:
            if not mt5_client:
                await websocket.send_json({"error": "MT5 not connected"})
                break

            tick = mt5_client.symbol_info_tick(symbol)
            if tick:
                await websocket.send_json(
                    {
                        "symbol": symbol,
                        "time": datetime.now().isoformat(),
                        "bid": tick.bid,
                        "ask": tick.ask,
                        "last": tick.last,
                        "volume": tick.volume,
                    }
                )

            await asyncio.sleep(0.5)  # Send updates every 500ms

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for {symbol}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
