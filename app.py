from flask import Flask, redirect, request, send_from_directory, url_for, render_template
import logging
from relations_graph.relations_graph import get_graph_from_text

# TODO: add requirenments and setup
# set the project root directory as the static folder, you can set others.
app = Flask(__name__, static_url_path='')
app.jinja_env.auto_reload = True
app.config['TEMPLATES_AUTO_RELOAD'] = True

title_to_graph = dict() # string->pair of jsons
graph = {"nodes":[{"id":"id","group":0},{"id":"Королевid","group":1},{"id":"Пилюгинid","group":2},{"id":"Глушкоid","group":3},{"id":"Гонорid","group":4}],"links":[{"source":"Пилюгинid","target":"Королевid","value":29},{"source":"Глушкоid","target":"Королевid","value":41},{"source":"Глушкоid","target":"Пилюгинid","value":20}]}

@app.route('/graph.html')
def sent_graph():
    return render_template("graph.html", graph=graph)

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

@app.route('/create_graph', methods = ['POST'])
def upload_new_text():
    global graph
    if request.method == 'POST':
        logging.warning(f"Request:\n{request}")
        logging.warning(f"Form:\n{request.form}")

        text = request.form['text']

        logging.warning(f"Text length: {len(text)}")
        graph = get_graph_from_text(text)

        logging.warning(f"Graph:\n{graph}")

        return redirect("/graph.html", code=302)


if __name__ == "__main__":
    app.run()