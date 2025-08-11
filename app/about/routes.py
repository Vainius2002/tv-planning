from . import bp


@bp.route("/")
def about():
    return "welcome to the about page!"