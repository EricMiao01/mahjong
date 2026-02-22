import socketio
import time

# 建立 Socket.IO 客戶端
sio = socketio.Client()

@sio.event
def connect():
    print("\n[系統] 成功連線到伺服器！")

@sio.event
def disconnect():
    print("\n[系統] 與伺服器斷開連線。")

@sio.event
def server_message(data):
    """接收伺服器的系統訊息"""
    print(f"\n[系統廣播] {data['msg']}")
    print("你要打哪張牌？(輸入代碼) > ", end="", flush=True) # 恢復輸入提示

@sio.event
def player_discarded(data):
    """接收其他玩家打牌的廣播"""
    # \r 是為了把游標拉回行首，才不會把原本打到一半的字覆蓋掉
    print(f"\r[牌桌動態] 玩家 {data['player_id'][:4]}... 打出了 【{data['tile']}】！")
    print("你要打哪張牌？(輸入代碼) > ", end="", flush=True) # 恢復輸入提示

if __name__ == '__main__':
    print("正在尋找麻將大廳...")
    try:
        # 連線到本機的伺服器
        sio.connect('http://localhost:5001')
    except Exception as e:
        print(f"連線失敗，請確認 server.py 是否已啟動。錯誤：{e}")
        exit()

    # 遊戲的「發送」主迴圈 (不會卡住接收訊息，因為接收是在背景執行的)
    time.sleep(1) # 稍微等一下連線訊息印完
    while True:
        try:
            # 這裡會卡住等你輸入，但背景依然能瞬間收到別人的牌！
            tile_to_play = input("你要打哪張牌？(輸入代碼) > ") 
            
            if tile_to_play.lower() in ['q', 'exit', 'quit']:
                sio.disconnect()
                break
                
            if tile_to_play:
                # 把你想打的牌「發送 (emit)」給伺服器
                sio.emit('play_tile', {'tile': tile_to_play})
                
        except KeyboardInterrupt:
            sio.disconnect()
            break