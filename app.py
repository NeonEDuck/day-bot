from flask import Flask

app = Flask(__name__)

@app.route('/')
def main() -> str:
    return 'Bot is alive!'

def run(host: str='0.0.0.0', port: int=8080) -> None:
	app.run(host=host, port=port)