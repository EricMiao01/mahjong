import socketio
from aiohttp import web

# 建立一個非同步的 Socket.IO 伺服器
sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins='*')
app = web.Application()
sio.attach(app)

# 記錄目前連線的玩家數量
connected_players = 0

@sio.event
async def connect(sid, environ):
    global connected_players
    connected_players += 1
    print(f"[伺服器] 玩家 {sid} 已連線！目前總人數：{connected_players}")
    # 歡迎新玩家
    await sio.emit('server_message', {'msg': f'歡迎加入麻將大廳！你的 ID 是 {sid}'}, to=sid)

@sio.event
async def disconnect(sid):
    global connected_players
    connected_players -= 1
    print(f"[伺服器] 玩家 {sid} 斷線了。目前總人數：{connected_players}")

@sio.event
async def play_tile(sid, data):
    """當收到玩家打牌的事件時"""
    tile = data.get('tile')
    print(f"[伺服器] 收到玩家 {sid} 打出了：{tile}")
    
    # 廣播給「除了打牌者以外」的所有人
    await sio.emit('player_discarded', {
        'player_id': sid,
        'tile': tile
    }, skip_sid=sid)

if __name__ == '__main__':
    print("啟動麻將伺服器於 http://localhost:5001 ...")
    web.run_app(app, port=5001)