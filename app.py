from flask import Flask, redirect, url_for, request, render_template, make_response, session, flash
import pymongo
from pymongo import MongoClient
from datetime import datetime
from bson.objectid import ObjectId
import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.use('Agg')
cluster = MongoClient('mongodb+srv://2020112089:0000@cluster1.x11eelo.mongodb.net/?retryWrites=true&w=majority')

db = cluster['coin_trading_market']
user_info = db['user_TB']
post_info = db['post_TB']

#사이트 첫 실행 시 거래소의 코인 초기값 설정

app = Flask(__name__)
app.config["SECRET_KEY"] = "SW_Enginnering"


@app.route('/', methods=["GET", "POST"])
def mainpage():
    posts = post_info.find()
    return render_template("mainpage.html", posts=posts)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    
    if session.get("userid") : # 로그인이 된 상황일 때
        flash("이미 로그인 된 상태입니다!")
        return redirect(url_for("mainpage"))

    if request.method == 'POST':
        username = request.form['username']
        userid = request.form['userid']
        password = request.form['password']
        
        if user_info.find_one({'username': username}):
            flash ('이미 가입된 사용자입니다.')
            return render_template("signup.html")
        
        user = {'username': username, 'userid': userid, 'password': password, 'coin_amount':0, 'balance': 0}
        user_info.insert_one(user)
        flash("회원가입 완료")
        return redirect(url_for("mainpage"))
        
    else:
        return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'userid' in session:
        flash ('이미 로그인 된 상태입니다.')
        return redirect(url_for("mainpage"))
    
    if request.method == 'POST':
        userid = request.form['userid']
        password = request.form['password']
        
        user = user_info.find_one({'userid': userid, 'password': password})
        
        if user:
            session['userid'] = userid
            return redirect(url_for("mainpage"))
        else:
            flash('잘못된 아이디 또는 비밀번호입니다.')
            return redirect(url_for("login"))
    else:
        return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('userid', None)
    return redirect(url_for("mainpage"))

@app.route('/mypage', methods=['GET', 'POST'])
def mypage():
    if 'userid' not in session:
        return redirect(url_for('login'))
        
    userid = session['userid']
    user = user_info.find_one({'userid': userid})
    username = user['username']
    coin_amount = user['coin_amount']
    balance = user['balance']
    
    if userid == "Website":  # userid가 "Website"인 경우
        if request.method == 'POST':
            if 'coin_amount' in request.form:
                amount = int(request.form['coin_amount'])
                coin_amount += amount
                flash(f"{amount}개의 코인이 추가되었습니다.")
                user_info.update_one({'userid': userid}, {'$set': {'coin_amount': coin_amount}})
                return redirect(url_for('mypage'))
        
        return render_template('mypage.html', username=username, coin_amount=coin_amount, balance=balance, website=True)
    
    if request.method == 'POST':
        if 'deposit_amount' in request.form:
            amount = int(request.form['deposit_amount'])
            balance += amount
            flash(f"{amount}원 입금되었습니다.")
            
        elif 'withdraw_amount' in request.form:
            amount = int(request.form['withdraw_amount'])
            if balance >= amount:
                balance -= amount
                flash(f"{amount}원 출금되었습니다.")
            else:
                flash(f"{amount-balance}원 부족합니다.")
        
        # 사용자 정보 업데이트
        user_info.update_one({'userid': userid}, {'$set': {'balance': balance}})
        
        return redirect(url_for('mypage'))
    else:
        return render_template('mypage.html', username=username, coin_amount=coin_amount, balance=balance)



@app.route('/coinpost', methods=['GET', 'POST'])
def coinpost():
    if 'userid' not in session:
        flash("로그인 후 이용해 주세요")
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        userid = session['userid']
        user = user_info.find_one({'userid': userid})
        coin_amount_in_account = user['coin_amount']
        coin_amount_to_sell = int(request.form['coin_amount'])

        if coin_amount_to_sell > coin_amount_in_account:
            flash('보유한 코인 개수보다 많은 코인을 등록할 수 없습니다.')
            return redirect(url_for('coinpost'))

        post = {
            'timestamp': datetime.now(),
            'userid': userid,
            'coin_amount': coin_amount_to_sell,
            'coin_price': int(request.form['coin_price'])
        }
        post_info.insert_one(post)
        flash('게시물이 등록되었습니다.')
        return redirect(url_for('coinpost'))
    else:
        posts = post_info.find()
        return render_template('coinpost.html', posts=posts)


@app.route('/buy/<post_id>', methods=['GET', 'POST'])
def buy_coin(post_id):
    if request.method == 'POST':
        userid = session['userid']
        buyer = user_info.find_one({'userid': userid})
        seller_post = post_info.find_one({'_id': ObjectId(post_id)})
        seller_p_userid = seller_post['userid']
        seller = user_info.find_one({'userid': seller_p_userid})
        seller_userid = seller['userid']

        if not seller_post:
            flash('해당 게시물을 찾을 수 없습니다.')
            return redirect(url_for('coinpost'))
              
        # 판매자와 구매자가 동일한 경우에는 구매가 이루어지지 않도록 제어
        if userid == seller_userid:
            flash('본인이 올린 게시물은 구매할 수 없습니다.')
            return redirect(url_for('coinpost'))

        # 구매자와 판매자의 정보 가져오기
        buyer_coin_amount = buyer['coin_amount']
        buyer_balance = buyer['balance']
        seller_p_coin_amount = seller_post['coin_amount']
        seller_p_coin_price = seller_post['coin_price']

        # 코인 구매
        if buyer_balance >= seller_p_coin_price * seller_p_coin_amount:
            # 구매자 정보 업데이트
            buyer_coin_amount += seller_p_coin_amount
            buyer_balance -= seller_p_coin_price * seller_p_coin_amount
            user_info.update_one({'userid': userid}, {'$set': {'coin_amount': buyer_coin_amount, 'balance': buyer_balance}})

            # 판매자 정보 업데이트
            seller_coin_amount = seller['coin_amount']
            seller_balance = seller['balance']
            seller_coin_amount -= seller_p_coin_amount
            seller_balance += seller_p_coin_price * seller_p_coin_amount
            user_info.update_one({'userid': seller_userid}, {'$set': {'coin_amount': seller_coin_amount, 'balance': seller_balance}})
            
            post_info.delete_one({'_id': seller_post['_id']})

            flash(f'코인 구매가 완료되었습니다.')
            return redirect(url_for('coinpost'))
        else:
            flash(f'잔액이 부족하여 코인을 구매할 수 없습니다.')
            return redirect(url_for('coinpost'))
    else:
        flash('잘못된 요청입니다.')
        return redirect(url_for('coinpost'))
    
#본인이 작성한 게시물을 삭제하는 기능
@app.route('/delete_post/<post_id>', methods=['POST'])
def delete_post(post_id):
    if 'userid' not in session:
        flash("로그인 후 이용해 주세요")
        return redirect(url_for('login'))

    userid = session['userid']
    post = post_info.find_one({'_id': ObjectId(post_id)})

    if not post:
        flash('해당 게시물을 찾을 수 없습니다.')
        return redirect(url_for('coinpost'))

    if userid != post['userid']:
        flash('본인이 작성한 게시물만 삭제할 수 있습니다.')
        return redirect(url_for('coinpost'))

    post_info.delete_one({'_id': ObjectId(post_id)})
    flash('게시물이 삭제되었습니다.')
    return redirect(url_for('coinpost'))

@app.route('/coinhistory')
def coinhistory():
    import matplotlib
    matplotlib.use('Agg')
    
    # 코인 포스트 정보 가져오기
    posts = post_info.find()
    coin_amounts = []
    coin_prices = []
    for post in posts:
        coin_amount = post['coin_amount']
        coin_price = post['coin_price']
        coin_amounts.append(coin_amount)
        coin_prices.append(coin_price)
    
    # 시세 분석 및 그래프 생성
    total_coins = sum(coin_amounts)
    price_per_coin = np.array(coin_prices, dtype='float64') * np.array(coin_amounts, dtype='float64')
    price_per_coin /= total_coins
    
    # 그래프 생성
    x = np.arange(len(coin_prices))
    plt.plot(x, price_per_coin)
    plt.xlabel('Post Index')
    plt.ylabel('Coin Price')
    plt.title('Coin Price Analysis')
    plt.xticks(x, x)
    plt.grid(True)
    
    # 그래프를 이미지로 저장
    graph_path = 'static/coin_graph.png'
    plt.savefig(graph_path)
    
    return render_template('coinhistory.html', graph_path=graph_path)

if __name__ == '__main__':
    app.run(debug=True)