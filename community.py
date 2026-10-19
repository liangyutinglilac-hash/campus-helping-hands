"""Community pilot workflows. No real campus identity or credit issuance is enabled."""
import sqlite3, time, uuid, hashlib
from urllib.parse import parse_qs

ACTIVITIES=[
 {'id':'first-aid','title':'把急救知识，带给更多同学','short':'急救公益','description':'急救知识宣传与物资整理志愿服务。拟邀请校内红十字相关公益组织共建。','organizer':'拟合作方向 · 急救公益组织','reward':20,'kind':'急救科普'},
 {'id':'campus-cats','title':'让校园里的小生命，也被照顾','short':'校园动物关怀','description':'在有经验的组织指导下，参与物资整理、领养宣传与校园动物关怀。','organizer':'拟合作方向 · 动物关怀社团','reward':15,'kind':'动物关怀'},
 {'id':'reuse','title':'让闲置书本，再陪伴一个人','short':'旧物循环','description':'协助旧书分类、整理与公益分享，让校园资源继续流转。','organizer':'拟合作方向 · 校园公益社团','reward':10,'kind':'资源循环'}]

def init(c):
 c.execute('CREATE TABLE IF NOT EXISTS community_users(actor TEXT PRIMARY KEY,code TEXT UNIQUE NOT NULL,created_at INTEGER NOT NULL)')
 c.execute('CREATE TABLE IF NOT EXISTS activity_interests(activity_id TEXT,actor TEXT,status TEXT NOT NULL,created_at INTEGER,PRIMARY KEY(activity_id,actor))')
 c.execute('CREATE TABLE IF NOT EXISTS referrals(invitee TEXT PRIMARY KEY,inviter TEXT NOT NULL,status TEXT NOT NULL,created_at INTEGER)')
 c.execute('CREATE TABLE IF NOT EXISTS club_applications(id TEXT PRIMARY KEY,actor TEXT NOT NULL,club TEXT NOT NULL,direction TEXT NOT NULL,budget INTEGER NOT NULL,description TEXT NOT NULL,status TEXT NOT NULL,created_at INTEGER)')

def ensure(c,actor):
 code=hashlib.sha256(('campus-pilot:'+actor).encode()).hexdigest()[:10].upper()
 c.execute('INSERT OR IGNORE INTO community_users VALUES(?,?,?)',(actor,code,int(time.time()*1000)))
 return c.execute('SELECT code FROM community_users WHERE actor=?',(actor,)).fetchone()[0]

def get(c,query):
 actor=parse_qs(query).get('actor',['我'])[0].strip()
 if not actor or len(actor)>30: raise ValueError('身份格式错误')
 code=ensure(c,actor)
 activities=[]
 for a in ACTIVITIES:
  row=c.execute('SELECT status FROM activity_interests WHERE activity_id=? AND actor=?',(a['id'],actor)).fetchone()
  activities.append({**a,'status':row[0] if row else None,'is_preview':True})
 data={'activities':activities,'referral_code':code,'balance':0,'identity_verified':False,'auth_available':False,
 'invited':c.execute('SELECT count(*) FROM referrals WHERE inviter=?',(actor,)).fetchone()[0],
 'referral':dict(r) if (r:=c.execute('SELECT inviter,status FROM referrals WHERE invitee=?',(actor,)).fetchone()) else None,
 'applications':[dict(r) for r in c.execute('SELECT * FROM club_applications WHERE actor=? ORDER BY created_at DESC',(actor,))]}
 c.commit();return data

def post(c,path,d):
 actor=d.get('actor','')
 if not isinstance(actor,str) or not actor.strip() or len(actor)>30: raise ValueError('请检查身份')
 actor=actor.strip();ensure(c,actor);now=int(time.time()*1000)
 if path=='/api/community/interest':
  id=d.get('activity_id')
  if id not in [a['id'] for a in ACTIVITIES]:raise ValueError('活动不存在')
  c.execute("INSERT OR IGNORE INTO activity_interests VALUES(?,?,'意向已登记',?)",(id,actor,now));c.commit()
  return {'message':'已登记意向。正式活动开放后需重新确认报名，当前不发放积分。'}
 if path=='/api/community/referral':
  code=d.get('code','')
  if not isinstance(code,str):raise ValueError('邀请码格式错误')
  inviter=c.execute('SELECT actor FROM community_users WHERE code=?',(code.strip().upper(),)).fetchone()
  if not inviter or inviter[0]==actor:raise ValueError('邀请码无效或属于自己')
  try:c.execute("INSERT INTO referrals VALUES(?,?,'待校园认证与首次互助',?)",(actor,inviter[0],now))
  except sqlite3.IntegrityError:raise ValueError('此身份已经绑定邀请人')
  c.commit();return {'message':'邀请关系已记录；完成真实认证与首笔互助后才可审核奖励，当前不发积分。'}
 if path=='/api/community/club':
  def field(k,n):
   v=d.get(k,'')
   if not isinstance(v,str) or not v.strip() or len(v)>n:raise ValueError('请检查社团资料')
   return v.strip()
  club=field('club',80);direction=field('direction',80);description=field('description',500);budget=int(d.get('budget',0))
  if not 1<=budget<=10000:raise ValueError('试点额度须为 1–10000 点')
  c.execute("INSERT INTO club_applications VALUES(?,?,?,?,?,?,'待核验',?)",(str(uuid.uuid4()),actor,club,direction,budget,description,now));c.commit()
  return {'message':'申请已保存，等待社团资质和活动方案核验；尚未发放积分。'}
 raise ValueError('未知操作')
