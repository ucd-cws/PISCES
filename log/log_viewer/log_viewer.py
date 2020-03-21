from flask import Flask, safe_join, send_from_directory
import sqlite3

dbpath = "../logsdb.db"
app = Flask(__name__)

#probably could be much cleaner
@app.route("/")
def root():
    with open ("static/viewer.html", "r") as myfile:
        data = myfile.read().replace('\n', '')
        return data

#cheated and told all requests for the root directory to look inside the static directory instead
@app.route('/<path:filename>')
def get_file_from_static(filename):
    return send_from_directory(app.static_folder, filename)


@app.route('/refresh')
def refresh():
    dbconnect = sqlite3.connect(dbpath)
    db = dbconnect.cursor()
    db.execute("SELECT * FROM logbook_occurrences")
    all_rows = db.fetchall()
    data = "["
    for row in all_rows:
        data = data + '%s\n,' % row[3]

    data = data.rstrip(',') + "]"
    return data

if __name__ == "__main__":
    app.run()
