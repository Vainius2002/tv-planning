from . import bp
from flask import request, jsonify, render_template
from app import models

@bp.route("/")
def contacts():
    return render_template("contacts.html")

@bp.route("/first_input", methods=["POST"])
def adding_prices():
    data = request.get_json()
    number_str = data.get("number")
    
    try:
        number = int(number_str)
        models.create_price(number)
        print("price added successfully!")
        return {"message": "Contact added"}, 201
    except (ValueError, TypeError):
        print("price add failed.")
        return jsonify({"status" : "error", "message" : "Invalid integer"}), 400
