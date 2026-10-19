from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
from pathlib import Path
import os, json, sqlite3, uuid, time, math
import community
import admin
ROOT = Path(__file__).parent
DB = ROOT / 'campus.db'
CAMPUSES = ['紫金港校区','玉泉校区','西溪校区','华家池校区','之江校区','舟山校区','海宁国际校区']
def campus_value(d):
    v=d.get('campus',CAMPUSES[0])
    if v not in CAMPUSES: raise ValueError('请选择校区')
    return v

def db():
    c = sqlite3.connect(DB, timeout=15)
    c.row_factory = sqlite3.Row
    c.execute('''CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,title TEXT NOT NULL,pickup TEXT NOT NULL,dropoff TEXT NOT NULL,price REAL NOT NULL,note TEXT DEFAULT '',owner TEXT NOT NULL,runner TEXT,status TEXT NOT NULL DEFAULT '待接单',pickup_lat REAL,pickup_lng REAL,drop_lat REAL,drop_lng REAL,runner_lat REAL,runner_lng REAL,created_at INTEGER NOT NULL)''')
    columns = {r['name'] for r in c.execute('PRAGMA table_info(tasks)')}
    for name, definition in [('category',"TEXT DEFAULT '取送'"),('due',"TEXT DEFAULT ''"),('is_demo','INTEGER DEFAULT 0'),('campus',"TEXT NOT NULL DEFAULT '紫金港校区'")]:
        if name not in columns: c.execute(f'ALTER TABLE tasks ADD COLUMN {name} {definition}')
    c.execute('''CREATE TABLE IF NOT EXISTS carries(id TEXT PRIMARY KEY,title TEXT NOT NULL,place TEXT NOT NULL,destination TEXT NOT NULL,owner TEXT NOT NULL,capacity INTEGER NOT NULL,deadline INTEGER NOT NULL,created_at INTEGER NOT NULL)''')
    if 'campus' not in {r['name'] for r in c.execute('PRAGMA table_info(carries)')}: c.execute("ALTER TABLE carries ADD COLUMN campus TEXT NOT NULL DEFAULT '紫金港校区'")
    c.execute('''CREATE TABLE IF NOT EXISTS carry_members(carry_id TEXT NOT NULL,member TEXT NOT NULL,PRIMARY KEY(carry_id,member))''')
    community.init(c)
    c.commit()
    return c

def task_data(r):
    return {k:r[k] for k in ['id','title','pickup','dropoff','price','note','owner','runner','status','created_at','category','due','is_demo','campus']}

def text(data,key,limit=120,default=None):
    v=data.get(key,default)
    if not isinstance(v,str) or not v.strip() or len(v.strip())>limit: raise ValueError(f'请检查 {key} 的内容')
    return v.strip()

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT/'public'),**kwargs)
    def reply(self,data,status=200,headers=None):
        raw=json.dumps(data,ensure_ascii=False).encode(); self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.send_header('Cache-Control','no-store')
        for key,value in (headers or {}).items(): self.send_header(key,value)
        self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        path=urlparse(self.path).path
        if not path.startswith('/api/'): return super().do_GET()
        if path.startswith('/api/admin/') and not admin.authenticated(self):
            return self.reply({'error':'请先登录管理者账号'},401)
        with db() as c:
            if path=='/api/admin/overview':
                return self.reply(admin.overview(c,community.ACTIVITIES,CAMPUSES))
            if path=='/api/community':
                try: return self.reply(community.get(c,urlparse(self.path).query))
                except ValueError: return self.reply({'error':'身份格式错误'},400)
            if path=='/api/tasks': return self.reply([task_data(r) for r in c.execute('SELECT * FROM tasks ORDER BY created_at DESC')])
            if path=='/api/carries':
                rows=[]
                for r in c.execute('SELECT * FROM carries ORDER BY created_at DESC'):
                    obj=dict(r);obj['members']=[x[0] for x in c.execute('SELECT member FROM carry_members WHERE carry_id=?',(r['id'],))]; rows.append(obj)
                return self.reply(rows)
        self.reply({'error':'接口不存在'},404)
    def do_POST(self):
        try:
            size=int(self.headers.get('Content-Length','0'))
            if size>16384: return self.reply({'error':'内容过长'},413)
            d=json.loads(self.rfile.read(size) or b'{}')
            if not isinstance(d,dict): raise ValueError('请求格式错误')
            path=urlparse(self.path).path;parts=path.strip('/').split('/');now=int(time.time()*1000)
            if path.startswith('/api/admin/'):
                return admin.post(self,path,d)
            with db() as c:
                if path.startswith('/api/community/'):
                    try: return self.reply(community.post(c,path,d))
                    except ValueError as e: return self.reply({'error':str(e)},400)
                if path=='/api/tasks':
                    title=text(d,'title',80);pickup=text(d,'pickup');dropoff=text(d,'dropoff');owner=text(d,'owner',30)
                    price=float(d.get('price',0))
                    if not math.isfinite(price) or price<0 or price>9999: raise ValueError('喵币须为 0–9999')
                    note=str(d.get('note','')).strip(); due=str(d.get('due',''));cat=d.get('category','取送')
                    if len(note)>500 or len(due)>40 or cat not in ['取送','帮带餐','打印','借用','技能','小心愿']: raise ValueError('请检查分类或内容长度')
                    id=str(uuid.uuid4());c.execute('INSERT INTO tasks(id,title,pickup,dropoff,price,note,owner,created_at,category,due,campus) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(id,title,pickup,dropoff,round(price,2),note,owner,now,cat,due,campus_value(d)));c.commit()
                    return self.reply(task_data(c.execute('SELECT * FROM tasks WHERE id=?',(id,)).fetchone()),201)
                if len(parts)==4 and parts[:2]==['api','tasks']:
                    t=c.execute('SELECT * FROM tasks WHERE id=?',(parts[2],)).fetchone()
                    if not t: return self.reply({'error':'需求不存在'},404)
                    action=parts[3];who=text(d,'actor' if action!='accept' else 'runner',30)
                    if action=='accept':
                        if t['owner']==who: raise ValueError('不能接下自己发布的需求')
                        result=c.execute("UPDATE tasks SET runner=?,status='进行中' WHERE id=? AND status='待接单'",(who,t['id']))
                    elif action=='submit' and t['runner']==who:
                        result=c.execute("UPDATE tasks SET status='待确认' WHERE id=? AND status='进行中'",(t['id'],))
                    elif action=='confirm' and t['owner']==who:
                        result=c.execute("UPDATE tasks SET status='已完成' WHERE id=? AND status='待确认'",(t['id'],))
                    elif action=='cancel' and t['owner']==who:
                        result=c.execute("UPDATE tasks SET status='已取消' WHERE id=? AND status='待接单'",(t['id'],))
                    else: return self.reply({'error':'当前身份无法执行此操作'},403)
                    if not result.rowcount: return self.reply({'error':'状态已变化，请刷新后再试'},409)
                    c.commit();return self.reply(task_data(c.execute('SELECT * FROM tasks WHERE id=?',(t['id'],)).fetchone()))
                if path=='/api/carries':
                    title=text(d,'title',80);place=text(d,'place');dest=text(d,'destination');owner=text(d,'owner',30)
                    capacity=int(d.get('capacity',0));deadline=int(d.get('deadline',0))
                    if not 1<=capacity<=20 or not now<deadline<=now+7*86400000: raise ValueError('请设置 1–20 个名额和未来七天内的截止时间')
                    id=str(uuid.uuid4());c.execute('INSERT INTO carries(id,title,place,destination,owner,capacity,deadline,created_at,campus) VALUES(?,?,?,?,?,?,?,?,?)',(id,title,place,dest,owner,capacity,deadline,now,campus_value(d)));c.commit();return self.reply({'id':id},201)
                if len(parts)==4 and parts[:2]==['api','carries'] and parts[3] in ['join','leave']:
                    who=text(d,'member',30);c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT * FROM carries WHERE id=?',(parts[2],)).fetchone()
                    if not r:return self.reply({'error':'帮带不存在'},404)
                    if parts[3]=='leave': c.execute('DELETE FROM carry_members WHERE carry_id=? AND member=?',(r['id'],who))
                    else:
                        if r['owner']==who: raise ValueError('你已经是这次帮带的发起人')
                        if r['deadline']<=now: raise ValueError('这次帮带已截止')
                        members=[x[0] for x in c.execute('SELECT member FROM carry_members WHERE carry_id=?',(r['id'],))]
                        if who in members: raise ValueError('你已经加入了')
                        if len(members)>=r['capacity']: return self.reply({'error':'名额已满'},409)
                        c.execute('INSERT INTO carry_members VALUES(?,?)',(r['id'],who))
                    c.commit();return self.reply({'ok':True})
            self.reply({'error':'接口不存在'},404)
        except (ValueError,TypeError,KeyError,OverflowError): self.reply({'error':'提交失败，请检查字段、时间和数值是否正确'},400)
        except sqlite3.Error: self.reply({'error':'暂时无法保存，请稍后重试'},503)

if __name__=='__main__':
    admin.account()
    db().close();port=int(os.environ.get('PORT','8787'));host=os.environ.get('HOST','127.0.0.1')
    print(f'校园搭把手 http://{host}:{port}',flush=True)
    ThreadingHTTPServer((host,port),Handler).serve_forever()
