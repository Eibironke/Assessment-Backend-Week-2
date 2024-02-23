"""This file defines the API routes."""

# pylint: disable = no-name-in-module

from flask import Flask, Response, request, jsonify
from psycopg2.errors import ForeignKeyViolation
import psycopg2.extras
from psycopg2 import sql


from database import get_db_connection

app = Flask(__name__)
conn = get_db_connection()


def all_clowns():
    """function that returns all clowns in database"""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT C.clown_id, C.clown_name, S.speciality_name FROM clown as C join speciality as S ON (C.speciality_id = S.speciality_id);")
        return jsonify(cur.fetchall())


def clown_checker(id):
    clown_list = all_clowns()

    if id not in [clown['clown_id'] for clown in clown_list.json]:
        return {"Message": "Clown not found, invalid ID"}, 404


@app.route("/", methods=["GET"])
def index() -> Response:
    """Returns a welcome message."""
    return jsonify({
        "title": "Clown API",
        "description": "Welcome to the world's first clown-rating API."
    })


@app.route("/clown", methods=["GET", "POST"])
def get_clowns() -> Response:
    """Returns a list of clowns in response to a GET request;
    Creates a new clown in response to a POST request."""
    if request.method == "GET":
        args = request.args.to_dict()
        order = args.get("order", "")
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        if order == "descending" or order == "":
            query = sql.SQL("SELECT C.clown_id, clown_name, speciality_name, AVG(rating) FROM speciality as S JOIN clown as C ON (S.speciality_id = C.speciality_id) JOIN review as R ON (C.clown_id = R.clown_id) GROUP BY c.clown_id, clown_name, speciality_name ORDER BY AVG(rating) DESC;")

        elif order == "ascending":
            query = sql.SQL("SELECT C.clown_id, clown_name, speciality_name, AVG(rating) FROM speciality as S JOIN clown as C ON (S.speciality_id = C.speciality_id) JOIN review as R ON (C.clown_id = R.clown_id) GROUP BY c.clown_id, clown_name, speciality_name ORDER BY AVG(rating) ASC;")
        else:
            return jsonify({"Message": "Method of ordering not accepted"}), 400

        cur.execute(query)
        rows = cur.fetchall()
        conn.commit()
        cur.close()
        conn.close
        return rows, 200

    else:
        data = request.json
        try:
            if "clown_name" not in data or "speciality_id" not in data:
                raise KeyError("New clowns need both a name and a speciality.")
            if not isinstance(data["speciality_id"], int):
                raise ValueError("Clown speciality must be an integer.")

            with conn.cursor() as cur:
                cur.execute("""INSERT INTO clown
                                 (clown_name, speciality_id)
                               VALUES (%s, %s)
                               RETURNING *;""",
                            (data["clown_name"], data["speciality_id"]))
                new_clown = cur.fetchone()
                conn.commit()
            return jsonify(new_clown), 201
        except (KeyError, ValueError, ForeignKeyViolation) as err:
            print(err.args[0])
            conn.rollback()
            return jsonify({
                "message": err.args[0]
            }), 400


@app.route("/clown/<int:id>", methods=["GET"])
def get_clowns_by_id(id) -> Response:
    """Returns clown by id with their name, id and speciality"""
    if request.method == "GET":

        clown_list = all_clowns()

        if id not in [clown['clown_id'] for clown in clown_list.json]:
            return {"Message": "Clown not found, invalid ID"}, 404

        with conn.cursor() as cur:
            query = "SELECT C.clown_id, C.clown_name, S.speciality_name FROM clown as C join speciality as S ON (C.speciality_id = S.speciality_id) WHERE C.clown_id = %s;"
            cur.execute(query, (id,))
            clown = cur.fetchone()
            conn.close
            return jsonify(clown), 200


@app.route("/clown/<int:id>/review", methods=["POST"])
def add_clown_review(id) -> Response:
    """Add review for clown dependant on clown ID"""

    if request.method == "POST":
        try:
            data = request.json
            clown_list = all_clowns()

            if data["clown_id"] not in [clown['clown_id'] for clown in clown_list.json]:
                return {"Message": "Clown not found, invalid ID"}, 404
            if data["rating"] not in [1, 2, 3, 4, 5]:
                return {"Message": "Review rating must be between 1 and 5"}, 400

            with conn.cursor() as cur:
                query = "INSERT INTO review(clown_id, rating) Values (%s, %s)"
                cur.execute(query, (data["clown_id"], data["rating"]))
                conn.commit()
            conn.close
            return jsonify({"Message": "Clown review added"}), 201
        except:
            return {"Message": "Error, Reviews must have a (clown_id) and a (rating) between 1 -5"}, 400


if __name__ == "__main__":
    app.run(port=8080, debug=True)
