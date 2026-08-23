from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def catch_all(path):
    action = request.args.get("action", "")
    print(f"[GET/POST] Rota requisitada: /{path} | Ação: {action}")

    if "social_player.php" in path:
        if action == "logConnectStatus":
            resposta = {"status": 0, "result": "success", "message": "connected"}
        else:
            resposta = {"status": 0, "domain": "gold", "port": "0"}
    elif "hdloading.php" in path or "ads" in path:
        resposta = {"status": 0, "result": "ok", "url": ""}
    else:
        resposta = {"status": 0, "result": "ok"}

    return jsonify(resposta)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
