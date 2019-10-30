from flask import *
from flask_sqlalchemy import SQLAlchemy
import time
import random
import os

app = Flask(__name__)
app.config['SECRET_KEY']='HAIMEIXIANGHAO'
# app.config['SQLALCHEMY_DATABASE_URI']='mysql+pymysql://root:123456@localhost/gaga?charset=UTF8MB4'
app.config['SQLALCHEMY_DATABASE_URI']='sqlite:////' + os.path.join(app.root_path, '../mysql/data.db')
app.config['SQLALCHEMY_ECHO'] = False
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['JSON_AS_ASCII'] = False
app.config['JSON_SORT_KEYS'] = False
db = SQLAlchemy(app)

class Useri(db.Model):
    __tablename__='useri'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    schid = db.Column(db.BigInteger, unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True)
    auth = db.Column(db.SmallInteger, default=1, nullable=False)#1是普通用户，2是志愿者，3是值班人员，4是管理员，5是被ban的
    st=db.Column(db.SmallInteger, default=1, nullable=False)#1是不在会话中，2是在会话中

    def __repr__(self):
        return '<User %r>' % self.username

class Userp(db.Model):
    __tablename__ = 'userp'
    id = db.Column(db.Integer, db.ForeignKey('useri.id'), primary_key=True)
    username = db.Column(db.String(80), db.ForeignKey('useri.username'), unique=True, index=True)
    password = db.Column(db.String(40), nullable=False)

class Volunteer(db.Model):
    __tablename__='vlt'
    id = db.Column(db.Integer, db.ForeignKey('useri.id'))
    idvlt = db.Column(db.Integer, primary_key=True, nullable=False, autoincrement=True)
    st = db.Column(db.SmallInteger, default=2, nullable=False)#1收信2不收信

    def __repr__(self):
        return '<id %d>' % self.id

class Case(db.Model):
    __tablename__ = 'case'
    idcase = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user1 = db.Column(db.Integer, db.ForeignKey('useri.id'), nullable=False, index=True)
    user2 = db.Column(db.Integer, db.ForeignKey('useri.id'), index=True)
    time = db.Column(db.DateTime, nullable=False)
    st = db.Column(db.SmallInteger, default=1, nullable=False)#1普通2疑难3加急4结束5找不到志愿者6已回复

class Msg(db.Model):
    __tablename__ = 'msg'
    idmsg = db.Column(db.Integer, primary_key=True, autoincrement=True)
    idcase = db.Column(db.Integer, db.ForeignKey('case.idcase'), nullable=False, index=True)
    id = db.Column(db.Integer, db.ForeignKey('useri.id'), nullable=False,index=True)
    time = db.Column(db.DateTime, nullable=False)
    content = db.Column(db.Text, nullable=False)
    st = db.Column(db.SmallInteger, default=1, nullable=False)#1表示正常，2表示未审核，3表示未通过，4表示已删除

class Proposal(db.Model):
    __tablename__ = 'proposal'
    idproposal = db.Column(db.Integer, primary_key=True, autoincrement=True)
    idcase = db.Column(db.Integer, db.ForeignKey('case.idcase'), nullable=False, index=True)
    reason = db.Column(db.Text, nullable=False)
    time = db.Column(db.DateTime, nullable=False)
    st = db.Column(db.SmallInteger, nullable=False)

class OtMsg(db.Model):
    __tablename__ = 'otmsg'
    idcase = db.Column(db.Integer, db.ForeignKey('case.idcase'), primary_key=True)
    time = db.Column(db.DateTime, nullable=False)

class WaitCheck(db.Model):
    __tablename__ = 'waitcheck'
    idcase = db.Column(db.Integer, db.ForeignKey('case.idcase'), primary_key=True)
    time = db.Column(db.DateTime, nullable=False)

def check_login(usr,psw):#None表示不存在用户，0表示密码不对，1表示对
    a=Userp.query.filter(Userp.username==usr).one_or_none()
    if not a:
        return None
    elif a.password==psw:
        return 1
    else:
        return 0

def get_id(usr):
    a = Useri.query.filter(Useri.username == usr).one_or_none()
    if not a:
        return None
    else:
        return a.id

def check_auth_and_id(usr):
    a = Useri.query.filter(Useri.username == usr).one_or_none()
    if not a:
        return None
    else:
        return a.auth, a.id

def check_auth(usr):
    a = Useri.query.filter(Useri.username == usr).one_or_none()
    if not a:
        return None
    else:
        return a.auth

def get_username(u_id):
    a = Useri.query.filter(Useri.id == u_id).one_or_none()
    if not a:
        return None
    else:
        return a.username

def user_get_msg(u_id):#所有正常状态的信的列表，每项为（写信者用户名，收信者用户名，时间，内容,idmsg）
    res=[]
    user_name=get_username(u_id)
    for a in Case.query.filter(Case.user1==u_id).all():
        for b in Msg.query.filter(and_(Msg.idcase==a.idcase, Msg.st==1)).all():
            c=get_username(b.id)
            if c==user_name:
                if a.user2:
                    t=get_username(a.user2)
                else:
                    t='未分配志愿者'
            else:
                t=user_name
            res.append((c,t,b.time,b.content, b.idmsg))
    return res

def get_user_st(id):
    a = Useri.query.filter(Useri.id == id).one_or_none()
    if not a:
        return None
    else:
        return a.st


def creat_case(id):#创建信件，寻找并分配志愿者，修改用户状态为在会话中，返回会话的idcase
    a=Volunteer.query.filter(Volunteer.st == 1).all()
    d_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    if not a:
        c = Case(user1=id, st=5, time=d_time)
        db.session.add(c)
    else:
        b=random.choice(a)
        c=Case(user1=id,user2=b.id, st=1,time=d_time)
        db.session.add(c)
    d = Useri.query.filter(Useri.id == id).one_or_none()
    d.st = 2
    db.session.commit()
    return c.idcase

def creat_case_change(u_id,notid):#创建信件，寻找并分配id不是notid的志愿者，返回会话的idcase，没有则返回None
    a=Volunteer.query.filter(and_(Volunteer.st == 1, Volunteer.id != notid)).all()
    d_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    if not a:
        return None
    else:
        b=random.choice(a)
        c=Case(user1=u_id,user2=b.id, st=1,time=d_time)
        db.session.add(c)
        db.session.commit()
        return c.idcase

def creat_msg(idcase,u_id,content,st=1):
    d_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    a=Msg(idcase=idcase, id=u_id, content=content, time=d_time,st=st)
    db.session.add(a)
    db.session.commit()

def user_get_case(u_id):#其实有这个函数可以把useri的st属性去掉，最后有时间可以改
    a=Case.query.filter(and_(Case.user1==u_id, Case.st!=4)).one_or_none()
    if a is None:
        return None
    else:
        return a

def creat_user(username, schid, password):
    a=Useri(schid=schid, username=username)
    db.session.add(a)
    db.session.commit()
    c=a.id
    b=Userp(id=c, username=username,password=password)
    db.session.add(b)
    db.session.commit()
    return c

def burn_msg(idmsg):
    a=Msg.query.filter(Msg.idmsg == idmsg).one_or_none()
    if not a is None:
        a.st=4
        db.session.commit()

#下面是志愿者功能
'''
def creat_re(idcase,u_id,content):#志愿者发送回信，状态未审核，并送到WaitCheck中
    d_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    a = Msg(idcase=idcase, id=u_id, content=content, time=d_time,st=2)
    b = WaitCheck(idcase=idcase, time=d_time)
    db.session.add(a)
    db.session.add(b)
    db.session.commit()
'''
def vlt_get_msg(u_id):#返回由字典{'from','to','content','idcase','time'}组成的列表，值都是字符串
    res = []
    for a in Case.query.filter(Case.user2 == u_id).all():
        blist = Msg.query.filter(and_(Msg.idcase == a.idcase, Msg.st == 1)).all()
        if blist:
            b=blist[-1]
            user_name = get_username(a.user1)
            c = get_username(b.id)
            if c == user_name:
                t = get_username(a.user2)
            else:
                t = user_name
            res.append({'from':c, 'to':t, 'time':b.time, 'content':b.content, 'idcase':str(a.idcase)})
    return res

def case_get_msg(idcase):
    res = []
    a=Case.query.filter(Case.idcase==idcase).one_or_none()
    for b in Msg.query.filter(and_(Msg.idcase == idcase, Msg.st == 1)).all():
            c = get_username(b.id)
            user_name=get_username(a.user1)
            if c == user_name:
                if a.user2:
                    t = get_username(a.user2)
                else:
                    t = '未分配志愿者'
            else:
                t = user_name
            res.append({'from': c, 'to': t, 'time': b.time, 'content': b.content, 'idmsg': str(b.idmsg)})
    return res

def creat_waitcheck(idcase):
    d_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    a = WaitCheck(idcase=idcase,time=d_time)
    db.session.add(a)
    db.session.commit()

#下面是值班人员功能
def get_wc_msg():#返回由字典{'from','to','content','idcase','time'}组成的列表，值都是字符串
    res = []
    for i in WaitCheck.query.all():
        a = Case.query.filter(Case.idcase == i.idcase).one_or_none()
        b = Msg.query.filter(and_(Msg.idcase == a.idcase, Msg.st == 2)).one_or_none()
        if b:
            user_name=get_username(a.user1)
            c = get_username(b.id)
            if c == user_name:
                t = get_username(a.user2)
            else:
                t = user_name
            res.append({'from':c, 'to':t, 'time':b.time, 'content':b.content, 'idcase':str(a.idcase)})
    return res

def get_hard_msg(u_id):#返回由字典{'from','to','content','idcase','time'}组成的列表，值都是字符串
    res = []
    for a in Case.query.filter(Case.st == 2).all():
        blist = Msg.query.filter(and_(Msg.idcase == a.idcase, Msg.st == 1)).all()
        if blist:
            b=blist[-1]
            user_name = get_username(a.user1)
            c = get_username(b.id)
            if c == user_name:
                t = get_username(a.user2)
            else:
                t = user_name
            res.append({'from': c, 'to': t, 'time': b.time, 'content': b.content, 'idcase': str(a.idcase)})
    return res

def get_ot_msg():#返回由字典{'from','to','content','idcase','time'}组成的列表，值都是字符串
    res = []
    for i in OtMsg.query.all():
        a = Case.query.filter(Case.idcase == i.idcase).one_or_none()
        b = Msg.query.filter(and_(Msg.idcase == a.idcase, Msg.st == 2)).one_or_none()
        if b:
            user_name=get_username(a.user1)
            c = get_username(b.id)
            if c == user_name:
                t = get_username(a.user2)
            else:
                t = user_name
            res.append({'from':c, 'to':t, 'time':b.time, 'content':b.content, 'idcase':str(a.idcase)})
    return res

#下面是管理员功能
def creat_voluntee(username, schid, password):#添加志愿者账号
    a=Useri(schid=schid, username=username)
    db.session.add(a)
    db.session.commit()
    c=a.id
    b=Userp(id=c, username=username,password=password)
    d=Volunteer(id=c)
    db.session.add(b)
    db.session.add(d)
    db.session.commit()
    return c, d.idvlt






db.create_all()


@app.template_filter('datetime')    # 这个应该可以直接删掉...吧
def jinja2_filter_datetime(ts):
    return datetime.datetime.fromtimestamp(ts,const.TZ).strftime('%Y-%m-%d %H:%M:%S')

@app.route('/',methods=['POST'])
def index():
    data=json.load(request.get_data())
    username=data['username']
    password=data['password']
    try:
        a = check_login(username, password)
        if a is None:
            return jsonify({'success': False, 'inf': '用户不存在'})
        elif a == 1:
            b, d = check_auth_and_id(username)
            # b是权限
            auth=str(b)
            return jsonify({'success': False, 'auth': auth, 'inf':''})
        else:
            return jsonify({'success': False, 'inf': '密码错误'})
    except:
        return jsonify({'success': False, 'inf': '发生错误，请重新操作'})


@app.route('/signup',methods=['POST'])
def signup():
    data=json.load(request.get_data())
    username=data['username']
    try:
        schid=int(data['schid'])
    except:
        return jsonify({'success': False, 'inf': '学号格式不正确'})
    password = data['password']
    shenfenzheng=data['shenfenzheng']
    if Useri.query.filter(Useri.username == username).one_or_none():
        return jsonify({'success':False, 'inf':'用户名已存在'})
    elif Useri.query.filter(Useri.schid == schid).one_or_none():
        return jsonify({'success': False, 'inf': '学号已注册'})
    else:
        try:
            d=creat_user(username, schid, password)
            return jsonify({'success': True, 'inf': ''})
        except:
            return jsonify({'success': False, 'inf': '发生错误，请重新操作'})



@app.route('/user',methods=['GET','POST'])
def user():
    if request.method=='GET':
        try:
            c=session['username']
            b, d = check_auth_and_id(c)
            if b == 1:            #如果用户是普通用户就显示信
                preres=user_get_msg(d)
                res=[]
                for i in preres:
                    res.append({'from':i[0], 'to':i[1],'time':i[2],'content':i[3],'idmsg':i[4]})
                return jsonify({'success': True, 'msg':res})#这里不知道jsonify能不能用于嵌套字典，要实验一下
            else:
                return jsonify({'success': False, 'inf': '权限不正确'})
        except:
            return jsonify({'success': False, 'inf': '发生错误，请重新操作'})
    else:
        try:
            data = json.load(request.get_data())
            action = data['action']
            if action == 'send':
                id = get_id(data['username'])
                content = data['content']
                if (not id is None) and content:
                    if get_user_st(id)==1:
                        idcase=creat_case(id)
                        creat_msg(idcase,id,content)
                    else:
                        a = user_get_case(id)
                        if a.st==6:
                            a.st=1
                        db.session.commit()
                        creat_msg(a.idcase, id, content)
                    return jsonify({'success': True, 'inf': ''})
                elif id is None:
                    return jsonify({'success': False, 'inf': '发送失败，用户不存在'})
                else:
                    return jsonify({'success': False, 'inf': '发送失败，内容为空'})
            elif action=='change':#这里直接更换志愿者
                id = get_id(data['username'])
                if not id is None:
                    a = user_get_case(id)
                    if a is None:
                        return jsonify({'success': False, 'inf': '操作失败，还没有创建会话'})
                    elif a.user2 is None:
                        return jsonify({'success': False, 'inf': '操作失败，还未分配志愿者'})
                    else:
                        b=a.user2
                        c=creat_case_change(id, b)
                        if c is None:
                            return jsonify({'success': False, 'inf': '操作失败，暂时没有空闲志愿者'})
                        else:
                            a.st = 4
                            db.session.commit()
                            return jsonify({'success': True, 'inf': ''})
            elif action=='burn':
                a=[]  #要烧的信的msgid的列表
                for i in data['burnmsg']:
                    a.append(int(i['idmsg']))
                for i in a:
                    burn_msg(i)
                return jsonify({'success': True, 'inf': ''})
        except:
            return jsonify({'success': False, 'inf': '发生错误，请重新操作'})

@app.route('/volunteer',methods=['GET','POST'])
def volunteer():
    if request.method=='GET':
        try:
            c=session['username']
            b, d = check_auth_and_id(c)
            if d is None:
                return jsonify({'success': False, 'inf': '用户不存在'})
            if b == 2 or b == 3:            #如果用户是志愿者或值班人员
                res=vlt_get_msg(d)
                a = Volunteer.query.filter(Volunteer.id==d).one_or_none()
                jieke=False
                if a.st==1:
                    jieke=True
                return jsonify({'success': True, 'msg':res, 'jieke':jieke})#这里不知道jsonify能不能用于嵌套字典，要实验一下
            else:
                return jsonify({'success': False, 'inf': '权限不正确'})
        except:
            return jsonify({'success': False, 'inf': '发生错误，请重新操作'})
    else:
        data = json.load(request.get_data())
        action = data['action']
        if action=='goto':
            idcase=int(data['idcace'])
            res=case_get_msg(idcase)
            return jsonify({'success':True, 'msg':res})
        if action=='send':
            idcase=int(data['idcase'])
            content=data['content']
            a=Case.query.filter(Case.idcase==idcase).one_or_none()
            if a.st!=2 and a.st!=4 and not WaitCheck.query.filter(WaitCheck.idcase == idcase).one_or_none():
                a.st=6
                db.session.commit()
                creat_msg(idcase,a.user2,content,2)
                creat_waitcheck(idcase)
                return jsonify({'succsss':True,'inf':''})
            elif a.st==2:
                return jsonify({'succsss':False,'inf':'不允许回复，该回话已设为疑难'})
            elif a.st==4:
                return jsonify({'succsss':False,'inf':'不允许回复，该回话已结束'})
            else:
                return jsonify({'succsss':False,'inf':'操作失败。已有待审核回复，请等待值班人员审核完成'})
        if action=='note':
            idcase=int(data['idcace'])
            a = Case.query.filter(Case.idcase == idcase).one_or_none()
            a.st=2
            db.session.commit()
            return jsonify({'succsss':True,'inf':''})
        if action=='change':
            data = json.load(request.get_data())
            username=data['username']
            jieke=data['jieke']
            d=get_id(username)
            a = Volunteer.query.filter(Volunteer.id == d).one_or_none()
            if jieke:
                a.st=1
                db.session.commit()
            else:
                a.st = 2
                db.session.commit()
            return jsonify({'succsss':True,'inf':''})

@app.route('/zhibanrenyuan',methods=['GET','POST'])
def zhibanrenyuan():
    if request.method=='GET':
        c = session['username']
        b, d = check_auth_and_id(c)
        if d is None:
            return jsonify({'success': False, 'inf': '用户不存在'})
        if b == 3:  # 如果用户是志愿者或值班人员
            res1 = get_wc_msg()
            res2 = get_hard_msg()
            res3 = get_ot_msg()
            return jsonify({'success': True, 'daishenhe': res1, 'yinan': res2, 'chaoshiweihui':res3})  # 这里不知道jsonify能不能用于嵌套字典，要实验一下
        else:
            return jsonify({'success': False, 'inf': '权限不正确'})
    else:
        data = json.load(request.get_data())
        action = data['action']
        if action=='goto':
            idcase=int(data['idcace'])
            res=case_get_msg(idcase)
            return jsonify({'success':True, 'msg':res})
        elif action=='pass':
            idcase=data['idcase']
            tg=data['tongguo']
            a = Case.query.filter(Case.idcase == idcase).one_or_none()
            b = Msg.query.filter(and_(Msg.idcase == a.idcase, Msg.st == 2)).one_or_none()
            if tg:
                if a.st==2:
                    return jsonify({'success': False, 'inf': '该会话已被设为疑难，请选择不通过并另行回复'})
                else:
                    b.st=1
                    a.st=6
                    to_de=WaitCheck.query.filter(WaitCheck.idcase == idcase).one_or_none()
                    if to_de:
                        db.session.delete(to_de)
                    to_de1=OtMsg.query.filter(OtMsg.idcase == idcase).one_or_none()
                    if to_de1:
                        db.session.delete(to_de1)
                    db.session.commit()
            else:
                b.st=3
                to_de = WaitCheck.query.filter(WaitCheck.idcase == idcase).one_or_none()
                if to_de:
                    db.session.delete(to_de)
        elif action=='re_hard':
            idcase = data['idcase']
            content=data['content']
            username=data['username']
            creat_msg(idcase,get_id(username),content,st=1)
            return jsonify({'succsss': True, 'inf': ''})


if __name__ == '__main__':
    app.run()