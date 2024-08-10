from cs50 import SQL
from datetime import datetime, timedelta
from flask import Flask, render_template, request
import json
from multiprocessing import Process


# Configure application
app = Flask(__name__)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///movies.db")

# save results as LIST of dicts, structure {star_id: [root_id, movie_id]}
results = []
already_checked = []
queue = []
start_time = datetime.now()

# set up list of allowed characters for name input (including special characters from languages in addition to English)
allowed_characters = [39, 45, 46, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 225, 228, 230, 231, 233, 235, 237, 246, 252, 351]

# open JSON file as python dict for saving / managing results
with open("cache.json", "r") as j:
    cache = json.load(j)

# setting up global process to handle timeout between website & server
# create dummy function for the dummy process --> in order to be created, the process requires a target-function (=placeholder)
def placeholder():
    return

# create dummy process (without starting it --> .is_alive() will return False)
p_search = Process(target=placeholder, args=())


def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def direct_connection(root_id, star_id):
    global results
    global already_checked

    subresults = {}

    if root_id not in already_checked:
        already_checked.append(root_id)

    # handle case of no connection
    if db.execute("SELECT A.movie_id FROM stars A, stars B WHERE A.person_id = (?) AND B.person_id = (?) AND A.movie_id = B.movie_id", root_id, star_id):
        gimme_movie = db.execute("SELECT A.movie_id FROM stars A, stars B WHERE A.person_id = (?) AND B.person_id = (?) AND A.movie_id = B.movie_id LIMIT 1", root_id, star_id)
        actual_movie_id = int(gimme_movie[0]['movie_id'])
        subresults[root_id] = [star_id, actual_movie_id]
        results.insert(0, subresults)
        return True
    else:
        return False


def search_on(root_id, star_id):
    global already_checked
    global queue

    if direct_connection(root_id=root_id, star_id=star_id):
        return True

    # begin cycling through list of movies --> CREATE LIST OF MOVIES OF ROOT_ID TO CYCLE THROUGH
    movies_unpretty = db.execute("SELECT movie_id FROM stars WHERE person_id = (?)", root_id)
    movies_root = []
    for i in movies_unpretty:
        movies_root.append(i['movie_id'])

    # restrict: if star not in already_checked --> add star to list
    for i in movies_root:
        star_list = []
        stars_unpretty = db.execute("SELECT person_id FROM stars WHERE movie_id = (?)", i)
        for j in range(len(stars_unpretty)):
            if stars_unpretty[j]['person_id'] == root_id or stars_unpretty[j]['person_id'] in already_checked:
                continue
            star_list.append(stars_unpretty[j]['person_id'])
            queue.append(stars_unpretty[j]['person_id'])


def queue_Bacons_movie_stars():
    global already_checked
    global queue

    movies_Bacon_unpretty = db.execute("SELECT movie_id FROM stars WHERE person_id = (?)", 102)
    movies_Bacon = []
    for i in movies_Bacon_unpretty:
        movies_Bacon.append(i['movie_id'])
    for i in movies_Bacon:
        stars_unpretty = db.execute("SELECT person_id FROM stars WHERE movie_id = (?)", i)
        for j in range(len(stars_unpretty)):
            if stars_unpretty[j]['person_id'] == 102 or stars_unpretty[j]['person_id'] in already_checked:
                continue
            queue.append(stars_unpretty[j]['person_id'])


def printing_results(list_plz):

    # prepare list of dicts
    transformed_results = []

    # then differentiate the passed list of numbers:
    for i in reversed(list_plz):
            temp_dict = {}
            co_star = list(i.keys())[0]
            co_star_pretty = db.execute("SELECT name FROM people WHERE id = (?)", int(co_star))[0]['name']
            star = i[co_star][0]
            star_pretty = db.execute("SELECT name FROM people WHERE id = (?)", star)[0]['name']
            movie = i[co_star][1]
            movie_pretty = db.execute("SELECT title FROM movies WHERE id = (?)", movie)[0]['title']
            temp_dict[co_star_pretty] = [star_pretty, movie_pretty]
            transformed_results.append(temp_dict)

    # return the transformed_results (with names instead of numbers)
    return transformed_results


def do_the_search(star_id):
    global cache
    global results
    global queue
    global already_checked
    global p_search

    queue_Bacons_movie_stars()
    while len(queue) > 0:
        current_time = datetime.now()
        delta = start_time + timedelta(minutes=25)
        # in case of timeout (codespace = 30min), save empty results
        if current_time > delta:
            # save in cache (= python dict)
            cache[str(star_id)] = []
            with open("cache.json", "w") as output:
                json.dump(cache, output)

            return results

        if search_on(root_id=queue[0], star_id=star_id):
            while len(results) > 0:
                first_key = list(results[0].keys())[0]
                if first_key == 102:
                    break
                else:
                    for i in already_checked:
                        if direct_connection(root_id=i, star_id=first_key):
                            break

            # save in cache (= python dict)
            cache[str(star_id)] = results

            # save this cache as the new json file
            with open("cache.json", "w") as output:
                json.dump(cache, output)

            return results
        queue.pop(0)


@app.route("/")
def layout():
    return render_template("layout.html")


@app.route("/search", methods=["GET", "POST"])
def search():
    global already_checked
    global results
    global cache
    global p_search

    already_checked = []
    results = []

    # open the updated file as a python-dict
    with open("cache.json", "r") as j:
        cache = json.load(j)

    if request.method == "POST":

        # validate input 1: if empty
        if not request.form.get("star"):
            return apology("Please enter a name.")

        star = request.form.get("star")
        alpha_check = star.replace(" ", "")

        # validate input 2: if not string of allowed characters
        for i in range(len(alpha_check)):
            while ord(alpha_check[i]) not in allowed_characters:
                return apology("Please enter a valid name.")

        # validate input 3: if input is "Kevin Bacon"
        if star.lower() == 'kevin bacon':
            return apology("Ha. Ha.")

        birth_year = request.form.get("birth")

        # WITH YEAR
        if birth_year:

            # handle incorrect submission (not integer of len = 4)
            if not birth_year.isdigit() or len(str(birth_year)) != 4:
                return apology("Please enter a proper birth year for this star.")

            # search again with birth year
            if not db.execute("SELECT id FROM people WHERE name LIKE (?) AND birth LIKE (?)", star, birth_year):
                return apology("Sorry, our database does not know this person.")

            # turn input into person_id WITH YEAR
            star_id = db.execute("SELECT id FROM people WHERE name LIKE (?) AND birth LIKE (?)", star, birth_year)[0]['id']


        # ONLY NAME
        else:
            # validate input 4: if name not in database ONLY NAME
            if not db.execute("SELECT id FROM people WHERE name LIKE (?)", star):
                return apology("Sorry, our database does not know this name.")

            # turn input into person_id ONLY NAME
            star_id = db.execute("SELECT id FROM people WHERE name LIKE (?)", star)

            if len(star_id) > 1:
                # have user specify birth year in a different html-form for submit
                return render_template("search_with_year.html", star=star)

            # extract star_id to continue working with it
            star_id = db.execute("SELECT id FROM people WHERE name LIKE (?)", star)[0]['id']

        # 1: we already have results in cache (from any previous search)
        if str(star_id) in cache:

            # if the background process (that produced the results) has not been terminated yet:
            if p_search.is_alive():
                p_search.join()

            result_list = cache[str(star_id)]
            pretty_results = printing_results(result_list)
            degree = len(pretty_results)
            initial_star = db.execute("SELECT name FROM people WHERE id = (?)", star_id)[0]['name']
            return render_template("results.html", initial_star=initial_star, pretty_results=pretty_results, degree=degree)

        # 2: results are easily found
        if direct_connection(root_id=102, star_id=star_id):
            cache[star_id] = results
            with open("cache.json", "w") as output:
                json.dump(cache, output)
            result_list = results
            pretty_results = printing_results(result_list)
            degree = len(pretty_results)
            initial_star = db.execute("SELECT name FROM people WHERE id = (?)", star_id)[0]['name']
            return render_template("results.html", initial_star=initial_star, pretty_results=pretty_results, degree=degree)

        # 3: in case there is no quick answer
        else:

            # in case NO background-process: do the search
            if not p_search.is_alive():

                # define process
                p_search = Process(target=do_the_search, args=(star_id, ))

                # start process
                p_search.start()

                # ask to wait in the meantime
                if not birth_year:
                    return render_template("please_wait_search.html", star=star)
                else:
                    return render_template("please_wait_search_with_year.html", star=star, birth_year=birth_year)


            # everything below means background-process is ongoing (= alive)
            # for resubmitting form with ONLY name:
            if not birth_year:
                return render_template("please_wait_search.html", star=star)

            # for resubmitting form with name AND year
            else:
                return render_template("please_wait_search_with_year.html", star=star, birth_year=birth_year)

    else:
        return render_template("search.html")




