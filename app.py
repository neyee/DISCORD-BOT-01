from flask import Flask
app = Flask(__name__)

@app.route("/")
def home():
    return "¡Mi sitio en Python funciona en Render!"

if __name__ == "__main__":
    app.run()
