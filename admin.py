"""Password-protected, read-only overview for the local pilot."""
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from http.cookies import SimpleCookie
from pathlib import Path

ROOT = Path(__file__).parent
CREDENTIALS = ROOT / '.admin-account.json'
LOCK = threading.Lock()
SESSIONS = {}
ATTEMPTS = {}
SESSION_SECONDS = 8 * 3600


def account():
    if not CREDENTIALS.exists():
        password = secrets.token_urlsafe(15)
        salt = secrets.token_hex(16)
        record = {'username': 'admin', 'password': password, 'salt': salt,
                  'hash': hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 200000).hex()}
        # The initial password stays in a private local handover file, never in public/.
        fd = os.open(CREDENTIALS, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
    return json.loads(CREDENTIALS.read_text())


def authenticated(handler):
    try:
        cookie = SimpleCookie(handler.headers.get('Cookie', ''))
        token = cookie['campus_admin'].value
    except (KeyError, ValueError):
        return False
    with LOCK:
        return SESSIONS.get(token, 0) > time.time()


def post(handler, path, data):
    # Reject browser requests from another origin, including cross-site logout.
    origin = handler.headers.get('Origin')
    if origin and origin not in ('http://' + handler.headers.get('Host', ''),
                                  'https://' + handler.headers.get('Host', '')):
        return handler.reply({'error': '请求来源不匹配'}, 403)
    if path == '/api/admin/login':
        now = time.time()
        ip = handler.client_address[0]
        with LOCK:
            recent = [t for t in ATTEMPTS.get(ip, []) if now - t < 300]
            if len(recent) >= 8:
                return handler.reply({'error': '尝试次数过多，请 5 分钟后再试'}, 429)
            ATTEMPTS[ip] = recent + [now]
        a = account()
        password = data.get('password', '')
        if not isinstance(password, str) or len(password) > 256:
            return handler.reply({'error': '账号或密码不正确'}, 401)
        digest = hashlib.pbkdf2_hmac('sha256', password.encode(), a['salt'].encode(), 200000).hex()
        if data.get('username') != a['username'] or not hmac.compare_digest(digest, a['hash']):
            return handler.reply({'error': '账号或密码不正确'}, 401)
        token = secrets.token_urlsafe(32)
        with LOCK:
            ATTEMPTS.pop(ip, None)
            for key, expiry in list(SESSIONS.items()):
                if expiry <= now:
                    del SESSIONS[key]
            SESSIONS[token] = now + SESSION_SECONDS
        return handler.reply({'username': a['username']}, headers={
            'Set-Cookie': f'campus_admin={token}; HttpOnly; SameSite=Strict; Path=/api/admin; Max-Age={SESSION_SECONDS}'})
    if path == '/api/admin/logout':
        try:
            cookie = SimpleCookie(handler.headers.get('Cookie', ''))
            with LOCK:
                SESSIONS.pop(cookie['campus_admin'].value, None)
        except (KeyError, ValueError):
            pass
        return handler.reply({'ok': True}, headers={
            'Set-Cookie': 'campus_admin=; HttpOnly; SameSite=Strict; Path=/api/admin; Max-Age=0'})
    return handler.reply({'error': '管理后台仅提供只读总览'}, 404)


def overview(c, activities, campuses):
    tasks = [dict(r) for r in c.execute('SELECT id,title,pickup,dropoff,price,owner,runner,status,created_at,category,due,is_demo,campus FROM tasks ORDER BY created_at DESC')]
    sample_titles = {'南门午餐，帮我带回宿舍', '两件小快递，顺路帮忙取一下', '图书馆学习中，想要一杯冰拿铁'}
    for task in tasks:
        task['is_demo'] = bool(task['is_demo'] or task['title'] in sample_titles)
    carries = [dict(r) for r in c.execute('SELECT * FROM carries ORDER BY created_at DESC')]
    members = [dict(r) for r in c.execute('SELECT * FROM carry_members')]
    for carry in carries:
        carry['members'] = [r['member'] for r in members if r['carry_id'] == carry['id']]
    interests = [dict(r) for r in c.execute('SELECT * FROM activity_interests ORDER BY created_at DESC')]
    applications = [dict(r) for r in c.execute('SELECT * FROM club_applications ORDER BY created_at DESC')]
    referrals = [dict(r) for r in c.execute('SELECT * FROM referrals ORDER BY created_at DESC')]
    names = {r['actor'] for r in c.execute('SELECT actor FROM community_users')}
    for task in tasks:
        names.update(x for x in (task['owner'], task['runner']) if x)
    names.update(r['owner'] for r in carries)
    names.update(r['member'] for r in members)
    names.update(r['actor'] for r in interests + applications)
    for r in referrals:
        names.update((r['invitee'], r['inviter']))
    users = [{'name': n, 'published': sum(t['owner'] == n for t in tasks),
              'completed': sum(t['runner'] == n and t['status'] == '已完成' for t in tasks),
              'interests': sum(r['actor'] == n for r in interests)} for n in sorted(names)]
    return {'generated_at': int(time.time() * 1000), 'tasks': tasks, 'carries': carries,
            'interests': interests, 'applications': applications, 'referrals': referrals,
            'users': users, 'activities': activities, 'campuses': campuses,
            'capabilities': {'identity_verification': False, 'coin_settlement': False}}
