from asyncio.windows_events import NULL
import sqlite3
from flask import Flask, render_template,url_for,Response
import os
import json
import datetime
from flask import Flask, jsonify, render_template, request, flash,session,redirect
from flask_session import Session
from flask_socketio import SocketIO, emit, join_room, leave_room, send
import cv2
from fer import FER
from rake_nltk import Rake
import time

rake_nltk_var = Rake()
question=["How long you have been under stress?","Have you shared your problem to anyone else?","can you say further more...","have you taken any steps to solve the problem","did anyone help you to solve this problem"]
Answers=[]
all_states=[]
neutral=0.0
angry=0.0
sad=0.0
happy=0.0
suprise=0.0
i=0
neu_no=0
ang_no=0
sup_no=0
sad_no=0
hap_no=0
d_id=None
emotion2=""
face_cascade_name = cv2.data.haarcascades + 'haarcascade_frontalface_alt.xml'  #getting a haarcascade xml file
face_cascade = cv2.CascadeClassifier()  #processing it for our project
if not face_cascade.load(cv2.samples.findFile(face_cascade_name)):  #adding a fallback event
    print("Error loading xml file")

camera=cv2.VideoCapture(0)

def generate_frames():
    global emotion
    while True:
            
        ## read the camera frame
        success,frame=camera.read()
        if not success:
            break
        else:
            gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)  #changing the video to grayscale to make the face analisis work properly
            face=face_cascade.detectMultiScale(gray,scaleFactor=1.1,minNeighbors=5)

            for x,y,w,h in face:
                img=cv2.rectangle(frame,(x,y),(x+w,y+h),(0,0,255),1)  #making a recentangle to show up and detect the face and setting it position and colour
          
            ret,buffer=cv2.imencode('.jpg',frame)
            emotion_detector = FER()
            emotion=emotion_detector.top_emotion(frame)
            global emotion2,neu_no,ang_no,sad_no,hap_no,sup_no,neutral,angry,suprise,sad,happy
            
            emotion2=emotion[0]
            print(emotion)
            if(emotion[0]=="neutral"):
                neu_no+=1
                neutral+=emotion[1]
            elif(emotion[0]=="angry"):
                ang_no+=1
                angry=angry+emotion[1]
            elif(emotion[0]=="surprise"):
                sup_no+=1
                suprise+=emotion[1]
            elif(emotion[0]=="happy"):
                happy+=emotion[1]
                hap_no+=1
            elif(emotion[0]=="sad"):
                sad+=emotion[1]
                sad_no+=1
            frame=buffer.tobytes()


        yield(b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


#with open('schema.sql') as f:
  #connection.executescript(f.read())
app = Flask(__name__) 
app.debug = True
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SESSION_PERMANENET"]=False
app.config["SESSION_TYPE"]="filesystem"
Session(app)
socketio = SocketIO(app, manage_session=False)
connection = sqlite3.connect('db2.db',check_same_thread=False)

flag=0

@app.route("/", methods=['GET','POST']) 

def home():
  return render_template("home.html")
def get_db_connection():
    conn = sqlite3.connect('db2.db')
    conn.row_factory = sqlite3.Row
    return conn
@app.route("/Admin_main",methods=['POST'])
def Admin_main():
    connection = sqlite3.connect('db2.db',check_same_thread=False)
    cur=connection.cursor()
    q=[request.form['name1'],request.form['name2'],request.form['name3'],request.form['name4'],request.form['name5']]
    for i in range(0,len(q)):
        if(q[i]!=''):
           cur.execute('update questions set question= ? where question_id = ?',(q[i],i+1) )
           connection.commit()

    return render_template('admin.html')

@app.route("/login",methods=['POST', 'GET'])
def login_pg():
    
    
    if request.method=="POST":
        session["u_id"]=int(request.form.get("uname"))
        session["password"]=request.form.get("upswd")
        print("hi",flush=True)
        conn = get_db_connection()
        users = conn.execute('SELECT * FROM user').fetchall()
        print("users")
        for user in users:
            if(user["u_id"]==session["u_id"]):
                global flag
                flag=1
                if(user["password"]==session["password"]):
                    flag=1
                else:
                    flag=0
        print(flag)
        if(flag==0):
            session["u_id"]=None
            session["password"]=None
            message="username or password is wrong"
            return render_template("login.html",message=message)
        conn.close()
        
        return redirect("/")
    return render_template("login.html")

@app.route('/signup1',methods=["GET","POST"])
def signup1():
    return render_template("signup.html")

@app.route('/sign',methods=["GET","POST"])
def sign():
    

    name=(request.form.get("uname1"))
    email=(request.form.get("email1"))
    age=int((request.form.get("age")))
    ph=float((request.form.get("phonenumber")))
    passwd1=request.form.get("upswd1")
    passwd2=request.form.get("upswd2")
    if not name :
        return render_template("error.html",message="Missing Name")   
    if (passwd1!=passwd2):
        return render_template("error.html",message="passwords not matching")
    cur = connection.cursor()   
    cur.execute("INSERT INTO user (name,email,phonenumber,password,age) VALUES (?, ?,?,?,?)",(name,email,ph,passwd1,age)
            )
    post1=cur.execute('SELECT u_id FROM user  WHERE email =?',(email,)).fetchone()
    connection.commit()           
   
    
    return render_template("login.html",message=post1)

@app.route('/admin_ques')
def admin_ques():
    q2=[]
    conn = get_db_connection()
    q1 = conn.execute('SELECT question FROM questions').fetchall()
    for q in q1:
        q2.append(q['question'])
    conn.close()
    return render_template("admin_ques.html",questions=q2)
@app.route('/index',methods=["GET","POST"])
def index():
        if not session.get("u_id"):
            return redirect("/login")
        
        return render_template("index.html")
@app.route('/connect')
def connect():
   

    if not session.get(""):
            return redirect("/login")
    
    print("connect")
    return render_template("connect.html")

@app.route("/logout")
def logout():
    session["u_id"]=None
    global flag
    flag=0
    print ("hi")
    return redirect("/")
@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if(request.method=='POST'):
        username = request.form['username']
        room = request.form['room']
        #Store the data in session
        session['username'] = username
        session['room'] = room
        return render_template('chat.html', session = session)
    else:
        if(session.get('username') is not None):
            return render_template('chat.html', session = session)
        else:
            return redirect(url_for('index'))
@app.route('/admin')
def admin():
     conn = get_db_connection()
     users = conn.execute('SELECT * FROM user').fetchall()
     conn.close()
     return render_template('admin.html',users=users)
@app.route('/details')
def details():
    connection = sqlite3.connect('db2.db',check_same_thread=False)

    detail=request.args.get("detail")
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM Answer a,user u where a.u_id=? and a.u_id=u.u_id ',(detail)).fetchall()
    
    conn.close()
    return render_template('details.html',users=users)

@socketio.on('join', namespace='/chat')
def join(message):
    room = session.get('room')
    join_room(room)
    emit('status', {'msg':  session.get('username') + ' has entered the room.'}, room=room)


@socketio.on('text', namespace='/chat')
def text(message):
    room = session.get('room')
    emit('message', {'msg': session.get('username') + ' : ' + message['msg']}, room=room)


@socketio.on('left', namespace='/chat')
def left(message):
    room = session.get('room')
    username = session.get('username')
    leave_room(room)
    session.clear()
    emit('status', {'msg': username + ' has left the room.'}, room=room)
@app.route('/thread1')
def thread1():
    connection = sqlite3.connect('db2.db',check_same_thread=False)
    
    if not session.get("u_id"):
            return redirect("/login")
    try:
        cur=connection.cursor()
    except:
        return redirect("/") 
    post1=cur.execute('SELECT d_id FROM user  WHERE u_id =?',(session["u_id"],)).fetchone()
    print(post1)
    print("kl")
    n=('null',)

    if  post1==n:
        return redirect("/doctorpg")
    
    global i
    i=i+1
    post1=cur.execute('SELECT question FROM questions  WHERE question_id =?',(i,)).fetchone()
    return render_template('voice.html',message=post1[0],emotion1=emotion2)

@app.route('/thread')
def thread():
    connection = sqlite3.connect('db2.db',check_same_thread=False)

    
    if not session.get("u_id"):
            return redirect("/login")
    try:
        cur=connection.cursor()
    except:
        return redirect("/") 
        
   
    global i,neu_no,ang_no,sad_no,hap_no,neutral,angry,suprise,sad,happy,sup_no
    t = time.localtime()
    current_time = time.strftime("%H:%M:%S", t)

    answer1=request.args.get("name1")
    if(neu_no!=0):
        neu_val=(neutral*100)/neu_no
    else:
        neu_val=0
    if(hap_no!=0):
        hap_val=happy*100/hap_no
    else:
        hap_val=0
    if(sad_no!=0):
        sad_val=sad*100/sad_no
    else:
        sad_val=0
    if(sup_no!=0):
        suprise_val=suprise*100/sup_no
    else:
        suprise_val=0
    if(ang_no!=0):
        ang_val=angry*100/ang_no
    else:
        ang_val=0
        neutral=0.0
        angry=0.0
        sad=0.0
        happy=0.0
        suprise=0.0
        neu_no=0
        ang_no=0
        sup_no=0
        sad_no=0
        hap_no=0
    print(all_states)
    cur = connection.cursor()
    post1=cur.execute('SELECT d_id FROM user  WHERE u_id =?',(session["u_id"],)).fetchone()
    cur.execute("INSERT INTO answer  (u_id,q_id,angry,sad,neutral,happy,surprise,answer,d_id,time) VALUES (?,?,?,?,?,?,?,?,?,?)",(session["u_id"],i,ang_val,sad_val,neu_val,hap_val,suprise_val,answer1,post1[0],current_time) )
    connection.commit()
    i=i+1
    cur1=connection.cursor()
    post1=cur1.execute('SELECT question FROM questions  WHERE question_id =?',(i,)).fetchone()
    if(i>len(question)):
        cur1.execute('update user set d_id= ? where u_id = ?',("null",session["u_id"]) )
        connection.commit()
        i=0
        connection.close()
        return render_template('thankyou.html')
   
    return render_template('voice.html',message=post1[0],emotion1=emotion2)
@app.route("/venna",methods=["GET","POST"])
def venna():
    return render_template('doctor_l.html')
@app.route("/venna1",methods=["GET","POST"])
def venna1():
    return render_template('doctor.html')

@app.route("/doctorsign",methods=["GET","POST"])
def doctor_sign():
    name=(request.form.get("uname1"))
    email=(request.form.get("email"))
    qualification=(request.form.get("q"))
    password=(request.form.get("upswd1"))
    c_password=(request.form.get("upswd2"))
    Experience=int(request.form.get("e"))
    phone_number=float(request.form.get("ph"))
    print(name)
    print(email,qualification,password,Experience)
    if not name :
        return render_template("error.html",message="Missing Name")   
    if (password!=c_password):
        return render_template("error.html",message="passwords not matching")

    cur = connection.cursor()   
    cur.execute("INSERT INTO doctor (d_name,phonenumber,email,password,qualification,experience) VALUES (?, ?,?,?,?,?)",(name,phone_number,email,password,qualification,Experience)
            )
    post1=cur.execute('SELECT d_id FROM doctor ').fetchall()
    connection.commit() 
    print(post1)          
    return render_template("doctor_l.html",message=post1[-1][0])
@app.route("/doctorlpg",methods=['POST', 'GET'])
def doctor_lpg():
    
    
    if request.method=="POST":
        global d_id
        d_id=int(request.form.get("uname"))
        passw=request.form.get("upswd")
        print("hi",flush=True)
        conn = get_db_connection()
        users = conn.execute('SELECT * FROM doctor').fetchall()
        print("users")
        for user in users:
            if(user["d_id"]==d_id):
                global flag
                flag=1
                if(user["password"]==passw):
                    flag=1
                else:
                    flag=0
        print(flag)
        if(flag==0):
        
            d_id=None
            passw=None
            message="username or password is wrong"
            return render_template("doctor_l.html",message=message)
        conn.close()
        
        return redirect("/doctorinfo")
    return render_template("doctor_l.html")  
@app.route('/doctorinfo')
def doctorinfo():
     conn = get_db_connection()
     
     users = conn.execute('SELECT * FROM answer a,user u where a.d_id=? and a.u_id=u.u_id',(d_id,)).fetchall()
     print('hi')
     
     conn.close()
     return render_template('details.html',users=users) 
@app.route('/doctorpg')
def doctorpg():
     conn = get_db_connection()
     users = conn.execute('SELECT * FROM doctor').fetchall()
     conn.close()
     return render_template('doctordetails.html',doctors=users)
@app.route('/message')
def message():
    connection = sqlite3.connect('db2.db',check_same_thread=False)

    detail=int(request.args.get("details"))
    cur=connection.cursor()
    x = session.get("u_id",' ')
    cur.execute('update user set d_id= ? where u_id = ?',(detail,x) )
    connection.commit()
    connection.close()
    return redirect('/')
    
@app.route('/video')
def video():
    return Response(generate_frames(),mimetype='multipart/x-mixed-replace; boundary=frame')