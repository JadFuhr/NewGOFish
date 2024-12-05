from flask import Flask, render_template, session, flash, redirect, url_for, request
import cards
import random
app = Flask(__name__)
from DBcm import UseDatabase

db_config={
    'host': 'localhost',
    'database': 'GoFishDataBase',
    'user': 'GoFishUser',
    'password': 'thisisastrongpassword'
}

app.secret_key = "fdhghdfjghndfhgdlfgnh'odfahngldafhgjdafngjdfaghldkafngladkfngdfljka"


def reset_state():
    session["deck"] = cards.build_deck()

    session["computer"] = []  
    session["player"] = []
    session["player_pairs"] = []
    session["computer_pairs"] = []

    for _ in range(7):
        session["computer"].append(session["deck"].pop())
        session["player"].append(session["deck"].pop())
    session["player"], pairs = cards.identify_remove_pairs(session["player"])
    session["player_pairs"].extend(pairs)
    session["computer"], pairs = cards.identify_remove_pairs(session["computer"])
    session["computer_pairs"].extend(pairs)


@app.route("/", methods=['GET','POST'])
@app.route("/register", methods=['GET','POST'])
def register():
    if request.method=='POST':
        username=request.form['username']
        
        with UseDatabase(db_config) as db:
            db.execute("INSERT IGNORE INTO players (handle) VALUES (%s)", (username,))
            db.execute("SELECT id FROM players WHERE handle = %s", (username,))
            result=db.fetchone()
            db.execute("SELECT winAmounts FROM players WHERE handle = %s", (username,))
            result2=db.fetchone()
            if result2:
                session['winAmounts']=result2[0]
                print(type(session['winAmounts']))
            if result:
                session['playerID']=result[0]
                session['username']=username
                return redirect(url_for('start'))
            
    return render_template("register.html")

@app.get('/leaderboards')
def leaderboard():

    with UseDatabase(db_config) as cursor:

        # Execute a query to fetch leaderboard data
        cursor.execute("SELECT handle, winAmounts FROM players ORDER BY winAmounts DESC LIMIT 10")
        rows = cursor.fetchall()

        # Convert rows into a dictionary-like structure
        leaderboard = [{"handle": row[0], "winAmounts": row[1]} for row in rows]

    return render_template("leaderboards.html", leaderboard = leaderboard)

@app.get("/startgame")
def start():
    reset_state()
    card_images = [ card.lower().replace(" ", "_") + ".png" for card in session["player"] ]
    return render_template(
                "startgame.html",
                title="Welcome to GoFish for the Web!",
                cards=card_images,  # available in the template as {{ cards }}
                n_computer=len(session["computer"]),  # available in the template as {{ n_computer }}
    )

def check_win_condition():
    if len(session["player"]) == 0:
        winAmount = session["winAmounts"]
        winAmount+=1
        session["winAmounts"]=winAmount
        with UseDatabase(db_config) as db:
            username = session["username"]
            db.execute("SELECT id FROM players WHERE handle =%s",(username,))
            result = db.fetchone()
            if result:
                id = result[0]
            db.execute("""
                UPDATE players SET winAmounts = %s WHERE id = %s AND handle = %s
            """, (winAmount,id, username,))
        session["winner"] = "Game Over, Player Has Won !!!!"
        return True
    elif len(session["computer"]) == 0:
        winAmount = len(session["computer_pairs"])
        session["winner"] = "Game Over, Computer Has Won !!!!"
        return True
    return False

@app.get("/end")
def end():
    winner = session.get("winner", "Player")
    return render_template("end.html",title="Game Over!", result=winner)

@app.get("/select/<value>")
def process_card_selection(value):
    found_it = False
    for n, card in enumerate(session["computer"]):
        if card.startswith(value):
            found_it = n
            break
    if isinstance(found_it, bool):
        flash("Go Fish!")
        if len(session["deck"]) > 0:

            session["player"].append(session["deck"].pop())
            flash(f"You drew a {session['player'][-1]}.")
        else:
            flash("deck is empty")
    else:
        flash(f"Here is your card from the computer: {session['computer'][n]}.")

        if len(session["computer"]) > 0:

            session["player"].append(session["computer"].pop(n))

    session["player"], pairs = cards.identify_remove_pairs(session["player"])
    session["player_pairs"].extend(pairs)

    if check_win_condition():
        return redirect(url_for("end"))

    card = random.choice(session["computer"])
    the_value = card[: card.find(" ")]

    card_images = [card.lower().replace(" ", "_") + ".png" for card in session["player"]]
    return render_template(
        "pickcard.html",
        title="The computer wants to know",
        value=the_value,
        cards=card_images,
    )
    
@app.get("/pick/<value>")
def process_the_picked_card(value):
    if value == "0":
        session["computer"].append(session["deck"].pop())
    else:
        for n, card in enumerate(session["player"]):
            if card.startswith(value.title()):
                break
        flash(f"DEBUG: The picked card was at location {n}.")
        session["computer"].append(session["player"].pop(n))

    session["computer"], pairs = cards.identify_remove_pairs(session["computer"])
    session["computer_pairs"].extend(pairs)

    if check_win_condition():
        return redirect(url_for("end"))

    card_images = [card.lower().replace(" ", "_") + ".png" for card in session["player"]]
    return render_template(
        "startgame.html",
        title="Keep playing!",
        cards=card_images,
        n_computer=len(session["computer"]),
    )


if __name__ == "__main__":
    app.run(debug=True)
